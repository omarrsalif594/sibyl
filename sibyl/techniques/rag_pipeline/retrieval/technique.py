"""
Retrieval Technique Orchestrator

This module orchestrates different retrieval subtechniques and manages
their configuration and execution.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class RetrievalTechnique:
    """
    Retrieval technique orchestrator.

    This class manages multiple retrieval subtechniques and provides
    a unified interface for retrieval operations.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize retrieval technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "retrieval"
        self._description = "Semantic and vector-based retrieval with multiple strategies"
        self._subtechniques: dict[str, BaseSubtechnique] = {}

        # Load technique configuration
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._technique_config = self.load_config(self._config_path)

    @property
    def name(self) -> str:
        """Get technique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get technique description."""
        return self._description

    @property
    def subtechniques(self) -> dict[str, BaseSubtechnique]:
        """Get all registered subtechniques."""
        return self._subtechniques

    def register_subtechnique(self, subtechnique: BaseSubtechnique) -> None:
        """
        Register a new subtechnique.

        Args:
            subtechnique: Subtechnique implementation

        Raises:
            ValueError: If subtechnique with same name already exists
        """
        if subtechnique.name in self._subtechniques:
            msg = f"Subtechnique '{subtechnique.name}' is already registered"
            raise ValueError(msg)

        logger.info("Registering subtechnique: %s", subtechnique.name)
        self._subtechniques[subtechnique.name] = subtechnique

    def list_subtechniques(self) -> list[str]:
        """
        List all available subtechnique names.

        Returns:
            List of subtechnique names
        """
        return list(self._subtechniques.keys())

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a specific subtechnique.

        Args:
            input_data: Query or input data for retrieval
            subtechnique: Name of subtechnique to use
            config: Configuration overrides
            **kwargs: Additional arguments passed to subtechnique

        Returns:
            Retrieval results

        Raises:
            ValueError: If subtechnique not found
            RuntimeError: If execution fails
        """
        # Validate subtechnique exists
        if subtechnique not in self._subtechniques:
            msg = f"Subtechnique '{subtechnique}' not found. Available: {self.list_subtechniques()}"
            raise ValueError(msg)

        # Get subtechnique implementation
        impl = self._subtechniques[subtechnique]

        # Build configuration cascade
        global_config = kwargs.get("global_config", {})
        subtechnique_config = impl.get_config()

        # Apply user overrides
        if config:
            subtechnique_config.update(config)

        cascade = ConfigCascade(
            global_config=global_config,
            technique_config=self._technique_config,
            subtechnique_config=subtechnique_config,
        )

        # Get merged configuration
        merged_config = cascade.merge()

        # Validate configuration
        try:
            impl.validate_config(merged_config)
        except ValueError as e:
            msg = f"Invalid configuration for {subtechnique}: {e}"
            raise ValueError(msg) from e

        try:
            result = execute_with_observability(
                technique_name=self.name,
                subtechnique=subtechnique,
                implementation=subtechnique,
                input_data=input_data,
                config=merged_config,
                executor=lambda: impl.execute(input_data, merged_config),
            )
            result_count = len(result) if isinstance(result, list) else "N/A"
            logger.info("Retrieval complete: %s (returned %s results)", subtechnique, result_count)
            return result
        except Exception as e:
            msg = f"Execution failed for {subtechnique}: {e}"
            raise RuntimeError(msg) from e

    def get_config(self) -> dict[str, Any]:
        """
        Get technique configuration.

        Returns:
            Technique configuration dictionary
        """
        return self._technique_config.copy()

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        import yaml  # plugin registration

        if not config_path.exists():
            logger.warning("Config file not found: %s, using empty config", config_path)
            return {}

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config if config is not None else {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in {config_path}: {e}"
            raise ValueError(msg) from None

    def __repr__(self) -> str:
        """String representation."""
        return f"RetrievalTechnique(subtechniques={len(self._subtechniques)})"
