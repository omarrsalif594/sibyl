"""
Session Management Technique Orchestrator

This module orchestrates session lifecycle, rotation strategies, context preservation,
and summarization subtechniques. It provides a unified interface for managing
session state across different rotation strategies.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class SessionManagementTechnique:
    """
    Session management technique orchestrator.

    This class manages multiple session management subtechniques across three categories:
    1. Rotation strategies (token-based, time-based, message-count)
    2. Context preservation (sliding-window, importance-based, full-history)
    3. Summarization (extractive, abstractive, no-summarize)
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize session management technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "session_management"
        self._description = "Session lifecycle and context management"
        self._subtechniques: dict[str, BaseSubtechnique] = {}

        # Load technique configuration
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._technique_config = self.load_config(self._config_path)

        # Auto-discover and register subtechniques
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
    def subtechniques(self) -> dict[str, BaseSubtechnique]:
        """Get all registered subtechniques."""
        return self._subtechniques

    def register_subtechnique(
        self, subtechnique: BaseSubtechnique, category: str | None = None
    ) -> None:
        """
        Register a new subtechnique.

        Args:
            subtechnique: Subtechnique implementation
            category: Optional category (rotation_strategy, context_preservation, summarization)

        Raises:
            ValueError: If subtechnique with same name already exists
        """
        # Create full key with category if provided
        key = f"{category}:{subtechnique.name}" if category else subtechnique.name

        if key in self._subtechniques:
            msg = f"Subtechnique '{key}' is already registered"
            raise ValueError(msg)

        logger.info("Registering session management subtechnique: %s", key)
        self._subtechniques[key] = subtechnique

    def list_subtechniques(self, category: str | None = None) -> list[str]:
        """
        List all available subtechnique names, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of subtechnique names
        """
        if category:
            return [name for name in self._subtechniques if name.startswith(f"{category}:")]
        return list(self._subtechniques.keys())

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        category: str | None = None,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a specific subtechnique.

        Args:
            input_data: Input data for the subtechnique
            subtechnique: Name of subtechnique to use
            category: Optional category (rotation_strategy, context_preservation, summarization)
            config: Configuration overrides
            **kwargs: Additional arguments passed to subtechnique

        Returns:
            Subtechnique output

        Raises:
            ValueError: If subtechnique not found
            RuntimeError: If execution fails
        """
        # Build full key
        key = f"{category}:{subtechnique}" if category else subtechnique

        # Validate subtechnique exists
        if key not in self._subtechniques:
            msg = f"Subtechnique '{key}' not found. Available: {self.list_subtechniques(category)}"
            raise ValueError(msg)

        # Get subtechnique implementation
        impl = self._subtechniques[key]

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
            msg = f"Invalid configuration for {key}: {e}"
            raise ValueError(msg) from e

        # Execute subtechnique
        try:
            result = execute_with_observability(
                technique_name=self.name,
                subtechnique=subtechnique,
                implementation=category or "default",
                input_data=input_data,
                config=merged_config,
                executor=lambda: impl.execute(input_data, merged_config),
                extra_log_fields={"category": category},
            )
            logger.info("Session management complete: %s", key)
            return result
        except Exception as e:
            logger.exception("Session management failed for %s: %s", key, e)
            msg = f"Execution failed for {key}: {e}"
            raise RuntimeError(msg) from e

    def check_rotation(
        self,
        strategy: str = "token_based",
        session_data: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Any:
        """
        Check if session should rotate using specified strategy.

        Args:
            strategy: Rotation strategy (token_based, time_based, message_count)
            session_data: Session state data
            config: Configuration overrides

        Returns:
            Rotation decision from strategy
        """
        return self.execute(
            input_data=session_data or {},
            subtechnique=strategy,
            category="rotation_strategy",
            config=config,
        )

    def preserve_context(
        self,
        strategy: str = "sliding_window",
        messages: list[Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Preserve context using specified strategy.

        Args:
            strategy: Context preservation strategy (sliding_window, importance_based, full_history)
            messages: List of messages to filter
            config: Configuration overrides

        Returns:
            Filtered list of messages
        """
        return self.execute(
            input_data=messages or [],
            subtechnique=strategy,
            category="context_preservation",
            config=config,
        )

    def summarize_context(
        self,
        strategy: str = "extractive",
        messages: list[Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Summarize context using specified strategy.

        Args:
            strategy: Summarization strategy (extractive, abstractive, no_summarize)
            messages: List of messages to summarize
            config: Configuration overrides

        Returns:
            Summarized list of messages
        """
        return self.execute(
            input_data=messages or [],
            subtechnique=strategy,
            category="summarization",
            config=config,
        )

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """
        Load technique configuration from YAML file.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        if config_path.exists():
            import yaml  # plugin registration

            with open(config_path) as f:
                config = yaml.safe_load(f)
                logger.debug("Loaded config from %s", config_path)
                return config or {}
        else:
            logger.warning("Config file not found: %s, using defaults", config_path)
            return {}

    def _discover_subtechniques(self) -> None:
        """
        Auto-discover and register subtechniques from subdirectories.

        Scans the subtechniques/ directory for:
        - rotation_strategy/default/{token_based, time_based, message_count}.py
        - context_preservation/default/{sliding_window, importance_based, full_history}.py
        - summarization/default/{extractive, abstractive, no_summarize}.py
        """
        Path(__file__).parent / "subtechniques"

        # Define subtechnique mapping
        subtechnique_map = {
            "rotation_strategy": ["token_based", "time_based", "message_count"],
            "rotation_based": ["rotation_manager"],
            "context_preservation": ["sliding_window", "importance_based", "full_history"],
            "summarization": ["extractive", "abstractive", "no_summarize"],
        }

        for category, implementations in subtechnique_map.items():
            for impl_name in implementations:
                try:
                    # Build module path
                    module_name = f"sibyl.techniques.workflow_orchestration.session_management.subtechniques.{category}.default.{impl_name}"

                    # Import module dynamically
                    import importlib  # plugin registration

                    module = importlib.import_module(module_name)

                    # Find implementation class (convert snake_case to PascalCase)
                    class_name = (
                        "".join(word.capitalize() for word in impl_name.split("_"))
                        + "Implementation"
                    )

                    if hasattr(module, class_name):
                        impl_class = getattr(module, class_name)
                        instance = impl_class()
                        self.register_subtechnique(instance, category)
                        logger.debug("Auto-discovered: %s:%s", category, impl_name)
                    else:
                        logger.warning("Class %s not found in %s", class_name, module_name)
                except Exception as e:
                    logger.warning(f"Failed to load {category}:{impl_name}: {e}", exc_info=True)

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about registered subtechniques.

        Returns:
            Dictionary with counts per category
        """
        return {
            "total": len(self._subtechniques),
            "rotation_strategy": len(self.list_subtechniques("rotation_strategy")),
            "rotation_based": len(self.list_subtechniques("rotation_based")),
            "context_preservation": len(self.list_subtechniques("context_preservation")),
            "summarization": len(self.list_subtechniques("summarization")),
            "subtechniques": list(self._subtechniques.keys()),
        }
