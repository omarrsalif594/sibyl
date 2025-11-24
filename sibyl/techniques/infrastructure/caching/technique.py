"""Multi-level caching strategies."""

import logging
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class CachingTechnique(BaseTechnique):
    """Multi-level caching strategies."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "caching"
        self._description = "Multi-level caching strategies"
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
        impl_name = implementation or subtechnique.name
        self._subtechniques.setdefault(subtechnique_name, {})[impl_name] = subtechnique
        logger.debug("Registered caching subtechnique %s:%s", subtechnique_name, impl_name)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
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
            logger.warning("Config file not found for caching: %s", config_path)
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML in {config_path}: {exc}"
            raise ValueError(msg) from None

    def list_subtechniques(self) -> dict[str, list[str]]:
        return {name: list(impls.keys()) for name, impls in self._subtechniques.items()}

    def _discover_subtechniques(self) -> None:
        base = "sibyl.techniques.infrastructure.caching.subtechniques"
        mapping = {
            "embedding_cache": [
                (f"{base}.embedding_cache.default.lru", "LruImplementation"),
                (f"{base}.embedding_cache.default.ttl", "TtlImplementation"),
            ],
            "query_cache": [
                (f"{base}.query_cache.default.exact_match", "ExactMatchImplementation"),
            ],
            "retrieval_cache": [
                (f"{base}.retrieval_cache.default.semantic", "SemanticImplementation"),
                (f"{base}.retrieval_cache.default.query_hash", "QueryHashImplementation"),
            ],
            "semantic_cache": [
                (
                    f"{base}.semantic_cache.default.similarity_threshold",
                    "SimilarityThresholdImplementation",
                ),
            ],
        }

        for subtechnique, implementations in mapping.items():
            self._subtech_configs[subtechnique] = self._load_subtech_config(subtechnique)
            for module_path, class_name in implementations:
                self._load_and_register(subtechnique, module_path, class_name)

    def _load_and_register(self, subtechnique: str, module_path: str, class_name: str) -> None:
        try:
            module = import_module(module_path)
            impl_cls = getattr(module, class_name)
            instance = impl_cls()
            self.register_subtechnique(instance, subtechnique, instance.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to register caching implementation %s.%s: %s",
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
