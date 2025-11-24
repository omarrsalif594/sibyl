"""Validation technique for quality control and output validation.

This technique orchestrates validation, retry strategies, and quality scoring
to ensure high-quality outputs from the system.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class ValidationTechnique(BaseTechnique):
    """Validation technique for quality control."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "validation"
        self._description = "Quality validation and control"
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
    ) -> Any:
        """Execute validation technique.

        Args:
            input_data: Input data for validation
            subtechnique: Subtechnique name (validator_composition, retry_strategy, quality_scoring)
            implementation: Implementation name
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            Result from subtechnique execution
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

        # Discover validator_composition subtechniques
        self._discover_subtechnique_category("validator_composition", base_path)

        # Discover retry_strategy subtechniques
        self._discover_subtechnique_category("retry_strategy", base_path)

        # Discover quality_scoring subtechniques
        self._discover_subtechnique_category("quality_scoring", base_path)

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
        if category == "validator_composition":
            self._register_validator_composition(category_path)
        elif category == "retry_strategy":
            self._register_retry_strategy(category_path)
        elif category == "quality_scoring":
            self._register_quality_scoring(category_path)

    def _register_validator_composition(self, path: Path) -> None:
        """Register validator composition implementations."""
        try:
            from sibyl.techniques.ai_generation.validation.subtechniques.validator_composition.default.composite import (  # plugin registration
                CompositeValidation,
            )
            from sibyl.techniques.ai_generation.validation.subtechniques.validator_composition.default.first_pass import (  # plugin registration
                FirstPassValidation,
            )
            from sibyl.techniques.ai_generation.validation.subtechniques.validator_composition.default.single import (  # plugin registration
                SingleValidation,
            )

            self.register_subtechnique(CompositeValidation(), "validator_composition", "composite")
            self.register_subtechnique(FirstPassValidation(), "validator_composition", "first_pass")
            self.register_subtechnique(SingleValidation(), "validator_composition", "single")

            logger.info("Registered validator_composition subtechniques")
        except Exception as e:
            logger.exception("Failed to register validator_composition: %s", e)

    def _register_retry_strategy(self, path: Path) -> None:
        """Register retry strategy implementations."""
        try:
            from sibyl.techniques.ai_generation.validation.subtechniques.retry_strategy.default.exponential_backoff import (  # plugin registration
                ExponentialBackoffRetry,
            )
            from sibyl.techniques.ai_generation.validation.subtechniques.retry_strategy.default.fixed_retry import (  # plugin registration
                FixedRetry,
            )
            from sibyl.techniques.ai_generation.validation.subtechniques.retry_strategy.default.no_retry import (  # plugin registration
                NoRetry,
            )

            self.register_subtechnique(
                ExponentialBackoffRetry(), "retry_strategy", "exponential_backoff"
            )
            self.register_subtechnique(FixedRetry(), "retry_strategy", "fixed_retry")
            self.register_subtechnique(NoRetry(), "retry_strategy", "no_retry")

            logger.info("Registered retry_strategy subtechniques")
        except Exception as e:
            logger.exception("Failed to register retry_strategy: %s", e)

    def _register_quality_scoring(self, path: Path) -> None:
        """Register quality scoring implementations."""
        try:
            from sibyl.techniques.ai_generation.validation.subtechniques.quality_scoring.default.rule_based import (  # plugin registration
                RuleBasedScoring,
            )
            from sibyl.techniques.ai_generation.validation.subtechniques.quality_scoring.default.threshold_based import (  # plugin registration
                ThresholdBasedScoring,
            )

            self.register_subtechnique(RuleBasedScoring(), "quality_scoring", "rule_based")
            self.register_subtechnique(
                ThresholdBasedScoring(), "quality_scoring", "threshold_based"
            )

            logger.info("Registered quality_scoring subtechniques")
        except Exception as e:
            logger.exception("Failed to register quality_scoring: %s", e)
