"""
Budget Allocation Technique

Provides configurable budget allocation across workflow phases:
- Planning phase
- Execution phase
- Validation phase

This technique eliminates hardcoded values from orchestration/budget.py
"""

import logging
from typing import Any

from sibyl.techniques.registry import BaseTechnique

logger = logging.getLogger(__name__)


class BudgetAllocationTechnique(BaseTechnique):
    """
    Budget allocation technique with configurable phase distributions.

    Features:
    - Loads configuration from core config system
    - Supports multiple allocation strategies
    - Environment variable overrides
    - Validation of allocation percentages

    Configuration Sources (in order of precedence):
    1. Environment variables: SIBYL_BUDGET_PHASE_ALLOCATION_PLANNING
    2. Core configuration: budget.phase_allocation.planning
    3. Technique defaults: 0.15 (15%)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize budget allocation technique.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.technique_id = "budget_allocation"

        # Load configuration from core config
        self._load_configuration()

        logger.info(
            f"Budget allocation technique initialized: "
            f"planning={self.phase_allocation['planning']:.2%}, "
            f"execution={self.phase_allocation['execution']:.2%}, "
            f"validation={self.phase_allocation['validation']:.2%}"
        )

    def _load_configuration(self) -> None:
        """Load budget allocation configuration from core config."""
        from sibyl.config.loader import load_core_config

        core_config = load_core_config()
        budget_config = core_config.get("budget", {})

        # Model selection configuration
        model_selection = budget_config.get("model_selection", {})
        self.strategy = self._get_param(
            "strategy", model_selection.get("strategy", "downgrade_cascade")
        )
        self.allow_downgrade = self._get_param(
            "allow_downgrade", model_selection.get("allow_downgrade", True)
        )

        # Initial model tier
        self.model_tier_initial = self._get_param(
            "model_tier_initial", budget_config.get("model_tier_initial", 1)
        )

        # Phase allocation
        phase_alloc = budget_config.get("phase_allocation", {})
        self.phase_allocation = {
            "planning": self._get_param(
                "phase_allocation_planning", phase_alloc.get("planning", 0.15)
            ),
            "execution": self._get_param(
                "phase_allocation_execution", phase_alloc.get("execution", 0.70)
            ),
            "validation": self._get_param(
                "phase_allocation_validation", phase_alloc.get("validation", 0.15)
            ),
        }

        # Validate configuration
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate budget allocation configuration."""
        # Validate model tier
        if not (0 <= self.model_tier_initial <= 3):
            msg = f"model_tier_initial must be between 0 and 3, got {self.model_tier_initial}"
            raise ValueError(msg)

        # Validate strategy
        valid_strategies = ["downgrade_cascade", "fixed", "adaptive"]
        if self.strategy not in valid_strategies:
            msg = f"strategy must be one of {valid_strategies}, got {self.strategy}"
            raise ValueError(msg)

        # Validate phase allocations
        for phase, allocation in self.phase_allocation.items():
            if not (0.0 <= allocation <= 1.0):
                msg = f"phase_allocation.{phase} must be between 0.0 and 1.0, got {allocation}"
                raise ValueError(msg)

        # Validate total allocation
        total = sum(self.phase_allocation.values())
        if abs(total - 1.0) > 0.01:  # Allow small floating point error
            msg = (
                f"Phase allocations must sum to 1.0, got {total:.4f}. "
                f"Allocations: {self.phase_allocation}"
            )
            raise ValueError(msg)

    def execute(
        self, subtechnique: str = "phase_based", total_budget: float = 10.0, **kwargs
    ) -> dict[str, Any]:
        """
        Execute budget allocation.

        Args:
            subtechnique: Allocation algorithm to use
            total_budget: Total budget to allocate (USD)
            **kwargs: Additional parameters

        Returns:
            Result dictionary with budget allocation per phase
        """
        if subtechnique == "phase_based":
            return self._execute_phase_based(total_budget, **kwargs)
        if subtechnique == "adaptive":
            return self._execute_adaptive(total_budget, **kwargs)
        if subtechnique == "priority_weighted":
            return self._execute_priority_weighted(total_budget, **kwargs)
        msg = f"Unknown subtechnique: {subtechnique}"
        raise ValueError(msg)

    def _execute_phase_based(self, total_budget: float, **kwargs) -> dict[str, Any]:
        """Execute phase-based budget allocation."""
        from sibyl.techniques.infrastructure.budget_allocation.subtechniques.phase_based.default.implementation import (
            execute_phase_based_allocation,
        )

        return execute_phase_based_allocation(
            total_budget=total_budget,
            phase_allocation=self.phase_allocation,
            model_tier=self.model_tier_initial,
            strategy=self.strategy,
            allow_downgrade=self.allow_downgrade,
            **kwargs,
        )

    def _execute_adaptive(self, total_budget: float, **kwargs) -> dict[str, Any]:
        """Execute adaptive budget allocation."""
        msg = "Adaptive budget allocation not yet implemented"
        raise NotImplementedError(msg)

    def _execute_priority_weighted(self, total_budget: float, **kwargs) -> dict[str, Any]:
        """Execute priority-weighted budget allocation."""
        msg = "Priority-weighted budget allocation not yet implemented"
        raise NotImplementedError(msg)

    def get_phase_budget(self, phase: str, total_budget: float) -> float:
        """
        Get budget for a specific phase.

        Args:
            phase: Phase name (planning, execution, validation)
            total_budget: Total budget

        Returns:
            Budget allocation for phase
        """
        if phase not in self.phase_allocation:
            msg = f"Unknown phase: {phase}"
            raise ValueError(msg)

        return total_budget * self.phase_allocation[phase]

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "technique_id": self.technique_id,
            "strategy": self.strategy,
            "allow_downgrade": self.allow_downgrade,
            "model_tier_initial": self.model_tier_initial,
            "phase_allocation": self.phase_allocation,
        }
