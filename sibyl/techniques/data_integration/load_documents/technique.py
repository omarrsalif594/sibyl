"""Load documents technique orchestrator.

This technique manages document loading from data providers.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.data_integration.load_documents.protocols import LoadDocumentsResult
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class LoadDocumentsTechnique(BaseTechnique):
    """Technique for loading documents from data providers."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize load documents technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "load_documents"
        self._description = "Load documents from data providers"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}
        self._technique_config = self._load_config(self._config_path)
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        """Get technique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get technique description."""
        return self._description

    @property
    def subtechniques(self) -> dict[str, dict[str, BaseSubtechnique]]:
        """Get registered subtechniques."""
        return self._subtechniques

    def register_subtechnique(
        self,
        subtechnique: BaseSubtechnique,
        subtechnique_name: str,
        variant: str = "default",
    ) -> None:
        """Register a subtechnique variant.

        Args:
            subtechnique: Subtechnique instance to register
            subtechnique_name: Name of the subtechnique category
            variant: Variant name (default, provider, custom)
        """
        if subtechnique_name not in self._subtechniques:
            self._subtechniques[subtechnique_name] = {}

        self._subtechniques[subtechnique_name][variant] = subtechnique
        logger.debug("Registered %s:%s", subtechnique_name, variant)

    def execute(
        self,
        input_data: Any,
        subtechnique: str = "loader",
        variant: str = "default",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LoadDocumentsResult:
        """Execute document loading.

        Args:
            input_data: Input data
            subtechnique: Subtechnique name
            variant: Variant name (default, provider, custom)
            config: Optional configuration override
            **kwargs: Additional arguments merged into config

        Returns:
            LoadDocumentsResult from subtechnique execution

        Raises:
            ValueError: If subtechnique or variant not found
            RuntimeError: If execution fails
        """
        # Validate subtechnique exists
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique: {subtechnique}. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        if variant not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown variant '{variant}' for subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        # Get subtechnique instance
        subtechnique_instance = self._subtechniques[subtechnique][variant]

        # Build configuration cascade
        subtechnique_config = subtechnique_instance.get_config()
        cascade = ConfigCascade(
            global_config=config or {},
            technique_config=self._technique_config,
            subtechnique_config=subtechnique_config,
        )
        merged_config = cascade.merge()
        merged_config.update(kwargs)

        # Validate configuration
        if not subtechnique_instance.validate_config(merged_config):
            msg = f"Invalid configuration for {subtechnique}:{variant}"
            raise ValueError(msg)

        # Execute subtechnique
        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=variant,
            input_data=input_data,
            config=merged_config,
            executor=lambda: subtechnique_instance.execute(input_data, merged_config),
        )

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """Load technique configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_config(self) -> dict[str, Any]:
        """Get technique configuration.

        Returns:
            Technique configuration dictionary
        """
        return self._technique_config.copy()

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register subtechniques."""
        base_path = Path(__file__).parent / "subtechniques"

        if not base_path.exists():
            logger.warning("Subtechniques directory not found: %s", base_path)
            return

        # Discover loader subtechnique
        self._discover_subtechnique_variants("loader", base_path)

    def _discover_subtechnique_variants(self, subtechnique_name: str, base_path: Path) -> None:
        """Discover variants for a specific subtechnique.

        Args:
            subtechnique_name: Subtechnique name
            base_path: Base path for subtechniques
        """
        subtechnique_path = base_path / subtechnique_name

        if not subtechnique_path.exists():
            logger.debug("Subtechnique not found: %s", subtechnique_name)
            return

        # Try to load each variant
        for variant in ["default", "provider", "custom"]:
            variant_path = subtechnique_path / variant
            if variant_path.exists():
                try:
                    # Import the build_subtechnique function
                    module_path = f"sibyl.techniques.data_integration.load_documents.subtechniques.{subtechnique_name}.{variant}"
                    module = __import__(module_path, fromlist=["build_subtechnique"])
                    build_fn = module.build_subtechnique

                    # Only register if it doesn't raise NotImplementedError
                    try:
                        instance = build_fn()
                        self.register_subtechnique(instance, subtechnique_name, variant)
                        logger.info("Registered %s:%s", subtechnique_name, variant)
                    except NotImplementedError:
                        logger.debug(
                            "Variant %s:%s not implemented (stub only)", subtechnique_name, variant
                        )
                except Exception as e:
                    logger.exception("Failed to load %s:%s: %s", subtechnique_name, variant, e)


def build_technique(config_path: Path | None = None) -> LoadDocumentsTechnique:
    """Build and return the load documents technique instance.

    Args:
        config_path: Optional path to technique config file

    Returns:
        LoadDocumentsTechnique instance
    """
    return LoadDocumentsTechnique(config_path)
