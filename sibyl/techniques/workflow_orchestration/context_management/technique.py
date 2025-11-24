"""Context management technique for context optimization.

This technique orchestrates rotation strategies, summarization, compression,
and prioritization to manage context windows effectively.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique
from sibyl.techniques.workflow_orchestration.context_management.protocols import (
    ContextManagementResult,
)

logger = logging.getLogger(__name__)


class ContextManagementTechnique(BaseTechnique):
    """Context management technique for context optimization."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "context_management"
        self._description = "Context window optimization"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}
        self._technique_config = self.load_config(self._config_path)
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
        implementation: str = "default",
    ) -> None:
        """Register a subtechnique implementation.

        Args:
            subtechnique: Subtechnique instance to register
            subtechnique_name: Name of the subtechnique category
            implementation: Implementation variant name
        """
        if subtechnique_name not in self._subtechniques:
            self._subtechniques[subtechnique_name] = {}

        self._subtechniques[subtechnique_name][implementation] = subtechnique
        logger.debug("Registered %s:%s", subtechnique_name, implementation)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict | None = None,
        **kwargs,
    ) -> ContextManagementResult:
        """Execute context management technique.

        Args:
            input_data: Input data for context management
            subtechnique: Subtechnique name (rotation_strategy, summarization, etc.)
            implementation: Implementation name
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            ContextManagementResult from subtechnique execution
        """
        # Validate subtechnique exists
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique: {subtechnique}. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        if implementation not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown implementation '{implementation}' for subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        # Get subtechnique instance
        subtechnique_instance = self._subtechniques[subtechnique][implementation]

        # Build configuration cascade
        subtechnique_config = subtechnique_instance.get_config()
        cascade = ConfigCascade(
            global_config=config or {},
            technique_config=self._technique_config,
            subtechnique_config=subtechnique_config,
        )
        merged_config = cascade.merge()

        # Validate configuration
        if not subtechnique_instance.validate_config(merged_config):
            msg = f"Invalid configuration for {subtechnique}:{implementation}"
            raise ValueError(msg)

        # Execute subtechnique
        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=implementation,
            input_data=input_data,
            config=merged_config,
            executor=lambda: subtechnique_instance.execute(input_data, merged_config),
        )

    def load_config(self, config_path: Path) -> dict[str, Any]:
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

    def list_subtechniques(self) -> list[str]:
        """List available subtechniques.

        Returns:
            List of subtechnique names
        """
        return list(self._subtechniques.keys())

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register subtechniques."""
        base_path = Path(__file__).parent / "subtechniques"

        if not base_path.exists():
            logger.warning("Subtechniques directory not found: %s", base_path)
            return

        # Discover all subtechnique categories
        self._discover_subtechnique_category("rotation_strategy", base_path)
        self._discover_subtechnique_category("summarization", base_path)
        self._discover_subtechnique_category("compression", base_path)
        self._discover_subtechnique_category("prioritization", base_path)

    def _discover_subtechnique_category(self, category: str, base_path: Path) -> None:
        """Discover implementations for a specific subtechnique category.

        Args:
            category: Subtechnique category name
            base_path: Base path for subtechniques
        """
        category_path = base_path / category / "default"

        if not category_path.exists():
            logger.debug("No default implementations found for %s", category)
            return

        # Import and register default implementations
        if category == "rotation_strategy":
            self._register_rotation_strategy(category_path)
        elif category == "summarization":
            self._register_summarization(category_path)
        elif category == "compression":
            self._register_compression(category_path)
        elif category == "prioritization":
            self._register_prioritization(category_path)

    def _register_rotation_strategy(self, path: Path) -> None:
        """Register rotation strategy implementations."""
        try:
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.rotation_strategy.default.no_rotation import (  # plugin registration
                NoRotationImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.rotation_strategy.default.threshold_based import (  # plugin registration
                ThresholdBasedImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.rotation_strategy.default.token_based import (  # plugin registration
                TokenBasedImplementation,
            )

            self.register_subtechnique(
                TokenBasedImplementation(), "rotation_strategy", "token_based"
            )
            self.register_subtechnique(
                ThresholdBasedImplementation(), "rotation_strategy", "threshold_based"
            )
            self.register_subtechnique(
                NoRotationImplementation(), "rotation_strategy", "no_rotation"
            )
            logger.info("Registered rotation_strategy subtechniques")
        except Exception as e:
            logger.exception("Failed to register rotation_strategy: %s", e)

    def _register_summarization(self, path: Path) -> None:
        """Register summarization implementations."""
        try:
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.summarization.default.abstractive_simple import (  # plugin registration
                AbstractiveSimpleImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.summarization.default.extractive import (  # plugin registration
                ExtractiveImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.summarization.default.no_summarize import (  # plugin registration
                NoSummarizeImplementation,
            )

            self.register_subtechnique(ExtractiveImplementation(), "summarization", "extractive")
            self.register_subtechnique(
                AbstractiveSimpleImplementation(), "summarization", "abstractive_simple"
            )
            self.register_subtechnique(NoSummarizeImplementation(), "summarization", "no_summarize")
            logger.info("Registered summarization subtechniques")
        except Exception as e:
            logger.exception("Failed to register summarization: %s", e)

    def _register_compression(self, path: Path) -> None:
        """Register compression implementations."""
        try:
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.compression.default.entity_compression import (  # plugin registration
                EntityCompressionImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.compression.default.gist import (  # plugin registration
                GistImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.compression.default.no_compression import (  # plugin registration
                NoCompressionImplementation,
            )

            self.register_subtechnique(
                EntityCompressionImplementation(), "compression", "entity_compression"
            )
            self.register_subtechnique(GistImplementation(), "compression", "gist")
            self.register_subtechnique(
                NoCompressionImplementation(), "compression", "no_compression"
            )
            logger.info("Registered compression subtechniques")
        except Exception as e:
            logger.exception("Failed to register compression: %s", e)

    def _register_prioritization(self, path: Path) -> None:
        """Register prioritization implementations."""
        try:
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.prioritization.default.mixed import (  # plugin registration
                MixedImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.prioritization.default.recency import (  # plugin registration
                RecencyImplementation,
            )
            from sibyl.techniques.workflow_orchestration.context_management.subtechniques.prioritization.default.relevance import (  # plugin registration
                RelevanceImplementation,
            )

            self.register_subtechnique(RecencyImplementation(), "prioritization", "recency")
            self.register_subtechnique(RelevanceImplementation(), "prioritization", "relevance")
            self.register_subtechnique(MixedImplementation(), "prioritization", "mixed")
            logger.info("Registered prioritization subtechniques")
        except Exception as e:
            logger.exception("Failed to register prioritization: %s", e)
