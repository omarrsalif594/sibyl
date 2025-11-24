"""Context augmentation and enrichment."""

import logging
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.loader import SubtechniqueSpec, load_subtechnique
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class AugmentationTechnique(BaseTechnique):
    """Context augmentation and enrichment orchestrator."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "augmentation"
        self._description = "Context augmentation and enrichment"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._technique_config = self.load_config(self._config_path)
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}
        self._subtech_configs: dict[str, dict[str, Any]] = {}
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def subtechniques(self) -> dict[str, dict[str, BaseSubtechnique]]:
        return self._subtechniques

    def register_subtechnique(
        self,
        subtechnique: BaseSubtechnique,
        subtechnique_name: str,
        implementation: str | None = None,
    ) -> None:
        """Register a subtechnique implementation."""
        impl_name = implementation or subtechnique.name
        self._subtechniques.setdefault(subtechnique_name, {})[impl_name] = subtechnique
        logger.debug("Registered augmentation subtechnique %s:%s", subtechnique_name, impl_name)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute an augmentation subtechnique."""
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        impl_name = implementation
        if implementation == "default":
            impl_name = self._subtech_configs.get(subtechnique, {}).get("default_implementation")
        if not impl_name:
            impl_name = next(iter(self._subtechniques[subtechnique].keys()))

        if impl_name not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown implementation '{impl_name}' for '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        impl = self._subtechniques[subtechnique][impl_name]
        subtech_config = impl.get_config() or {}
        if config:
            subtech_config = {**subtech_config, **config}

        cascade = ConfigCascade(
            global_config=kwargs.get("global_config", {}),
            technique_config=self._technique_config,
            subtechnique_config=subtech_config,
        )
        merged_config = cascade.merge()

        if not impl.validate_config(merged_config):
            msg = f"Invalid configuration for {subtechnique}:{impl_name}"
            raise ValueError(msg)

        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=impl_name,
            input_data=input_data,
            config=merged_config,
            executor=lambda: impl.execute(input_data, merged_config),
        )

    def get_config(self) -> dict[str, Any]:
        return self._technique_config.copy()

    def load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            logger.warning("Config file not found for augmentation: %s", config_path)
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML in {config_path}: {exc}"
            raise ValueError(msg) from None

    def list_subtechniques(self) -> dict[str, list[str]]:
        """Return mapping of subtechnique categories to implementations."""
        return {name: list(impls.keys()) for name, impls in self._subtechniques.items()}

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register default implementations."""
        # Define subtechniques and their implementations
        # Using the new loader for metadata_injection, keeping old approach for others
        subtechniques_config = {
            "metadata_injection": {
                "variant": "default",
                "implementations": ["schema_metadata", "source_metadata"],
                "use_loader": True,
            },
            "citation_injection": {
                "implementations": [
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.citation_injection.default.inline_citations",
                        "InlineCitationsImplementation",
                    ),
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.citation_injection.default.footnotes",
                        "FootnotesImplementation",
                    ),
                ],
                "use_loader": False,
            },
            "cross_reference": {
                "implementations": [
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.cross_reference.default.entity_links",
                        "EntityLinksImplementation",
                    ),
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.cross_reference.default.doc_links",
                        "DocLinksImplementation",
                    ),
                ],
                "use_loader": False,
            },
            "temporal_context": {
                "implementations": [
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.temporal_context.default.timestamp",
                        "TimestampImplementation",
                    ),
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.temporal_context.default.recency",
                        "RecencyImplementation",
                    ),
                ],
                "use_loader": False,
            },
            "entity_linking": {
                "implementations": [
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.entity_linking.default.spacy",
                        "SpacyImplementation",
                    ),
                    (
                        "sibyl.techniques.rag_pipeline.augmentation.subtechniques.entity_linking.default.llm",
                        "LlmImplementation",
                    ),
                ],
                "use_loader": False,
            },
        }

        for subtechnique, config in subtechniques_config.items():
            self._subtech_configs[subtechnique] = self._load_subtech_config(subtechnique)

            if config.get("use_loader"):
                # Use the new loader approach
                self._load_with_loader(subtechnique, config)
            else:
                # Use the old direct import approach
                for module_path, class_name in config["implementations"]:
                    self._load_and_register(subtechnique, module_path, class_name)

    def _load_with_loader(self, subtechnique: str, config: dict[str, Any]) -> None:
        """Load subtechnique implementations using the new loader."""
        try:
            # Create the spec for this subtechnique
            spec = SubtechniqueSpec(
                shop="rag_pipeline",
                technique="augmentation",
                subtechnique=subtechnique,
                variant=config.get("variant", "default"),
            )

            # Load the factory function
            factory = load_subtechnique(spec)

            # Build each implementation
            for impl_name in config.get("implementations", []):
                try:
                    instance = factory(implementation_name=impl_name)
                    self.register_subtechnique(instance, subtechnique, instance.name)
                    logger.info(
                        "Registered augmentation implementation %s:%s using loader",
                        subtechnique,
                        impl_name,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to build implementation %s:%s: %s",
                        subtechnique,
                        impl_name,
                        exc,
                    )
        except Exception as exc:
            logger.warning(
                "Failed to load subtechnique %s with loader: %s",
                subtechnique,
                exc,
            )

    def _load_and_register(self, subtechnique: str, module_path: str, class_name: str) -> None:
        try:
            module = import_module(module_path)
            impl_cls = getattr(module, class_name)
            instance = impl_cls()
            self.register_subtechnique(instance, subtechnique, instance.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to register augmentation implementation %s.%s: %s",
                module_path,
                class_name,
                exc,
            )

    def _load_subtech_config(self, subtechnique: str) -> dict[str, Any]:
        config_path = Path(__file__).parent / "subtechniques" / subtechnique / "config.yaml"
        if not config_path.exists():
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            logger.warning("Invalid YAML for subtechnique %s: %s", subtechnique, exc)
            return {}
