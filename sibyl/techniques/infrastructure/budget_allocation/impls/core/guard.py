"""
BudgetGuard Service

Unified budget enforcement for all cost ceilings across the system.

Features:
- Per-step cost ceilings (Quorum pipeline)
- Per-workflow token limits (orchestration)
- Per-tool cost limits
- Model-aware pricing
- Centralized budget decisions

Usage:
    from infrastructure.budget import BudgetGuard

    guard = BudgetGuard()

    # Check if operation is within budget
    decision = guard.request(
        tokens=1000,
        model="claude-sonnet-4-5",
        operation="quorum_diagnosis",
    )

    if decision.allowed:
        # Proceed with operation
        result = await execute_operation()

        # Record actual usage
        guard.record_usage(
            tokens=result.actual_tokens,
            cost=result.actual_cost,
            operation="quorum_diagnosis",
        )
    else:
        # Budget exceeded
        raise BudgetExceeded(decision.reason)
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when budget ceiling is exceeded."""

    def __init__(self, message: str, ceiling: float, requested: float) -> None:
        super().__init__(message)
        self.ceiling = ceiling
        self.requested = requested


@dataclass
class BudgetDecision:
    """
    Decision result from budget check.

    Attributes:
        allowed: Whether the operation is allowed
        reason: Human-readable reason for decision
        remaining_tokens: Tokens remaining in budget
        remaining_cost: Cost remaining in budget (USD)
        ceiling_hit: Name of ceiling that was hit (if denied)
    """

    allowed: bool
    reason: str
    remaining_tokens: int | None = None
    remaining_cost: float | None = None
    ceiling_hit: str | None = None


# Model pricing (cost per 1K tokens) - loaded from configuration
def _get_model_pricing() -> Any:
    """Load model pricing from configuration."""
    try:
        from sibyl.config.loader import load_core_config

        config = load_core_config()

        # Get model pricing from providers configuration
        providers = config.get("providers", {})
        llm_providers = providers.get("llm", {})

        pricing = {}
        for _provider_name, provider_config in llm_providers.items():
            if not provider_config.get("enabled", False):
                continue
            for model_config in provider_config.get("models", []):
                model_name = model_config.get("name")
                if model_name:
                    pricing[model_name] = {
                        "input": model_config.get("cost_per_1k_input", 0.003),
                        "output": model_config.get("cost_per_1k_output", 0.015),
                    }

        # Add default fallback
        if "default" not in pricing:
            pricing["default"] = {"input": 0.003, "output": 0.015}

        return pricing
    except Exception as e:
        logger.warning("Failed to load model pricing from config: %s, using fallback", e)
        # Fallback pricing if config loading fails
        return {
            "claude-opus-4": {"input": 0.015, "output": 0.075},
            "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
            "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
            "claude-haiku-4": {"input": 0.0008, "output": 0.004},
            "gpt-4-turbo": {"input": 0.010, "output": 0.030},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "default": {"input": 0.003, "output": 0.015},
        }


# Lazy-loaded model pricing
_MODEL_PRICING = None


def _ensure_model_pricing_loaded() -> Any:
    """Ensure MODEL_PRICING is loaded."""
    global _MODEL_PRICING
    if _MODEL_PRICING is None:
        _MODEL_PRICING = _get_model_pricing()
    return _MODEL_PRICING


MODEL_PRICING = _ensure_model_pricing_loaded()


class BudgetGuard:
    """
    Centralized budget enforcement service.

    Provides unified API for all budget checks across:
    - Quorum pipeline (per-step ceilings)
    - Orchestration workflows (per-workflow limits)
    - Individual tools (per-tool limits)

    Configuration:
    - Global ceiling: Maximum cost/tokens across all operations
    - Per-operation ceilings: Override for specific operations
    - Model-aware pricing: Automatic cost calculation
    """

    def __init__(
        self,
        global_token_ceiling: int | None = None,
        global_cost_ceiling_usd: float | None = None,
        per_operation_ceilings: dict[str, float] | None = None,
    ) -> None:
        """
        Initialize BudgetGuard.

        Args:
            global_token_ceiling: Global token limit (None = unlimited)
            global_cost_ceiling_usd: Global cost limit in USD (None = unlimited)
            per_operation_ceilings: Dict of operation → cost ceiling (USD)

        Example:
            guard = BudgetGuard(
                global_cost_ceiling_usd=10.0,
                per_operation_ceilings={
                    "quorum_diagnosis": 0.5,
                    "quorum_strategy": 0.4,
                    "quorum_generation": 1.5,
                }
            )
        """
        self.global_token_ceiling = global_token_ceiling
        self.global_cost_ceiling = global_cost_ceiling_usd
        self.per_operation_ceilings = per_operation_ceilings or {}

        # Tracking
        self.tokens_used = 0
        self.cost_used = 0.0
        self.operation_costs: dict[str, float] = {}

        logger.info(
            f"BudgetGuard initialized: "
            f"global_tokens={global_token_ceiling}, "
            f"global_cost={global_cost_ceiling_usd}, "
            f"operation_ceilings={len(self.per_operation_ceilings)}"
        )

    def request(
        self,
        tokens: int,
        model: str,
        operation: str | None = None,
        estimate_output_tokens: int | None = None,
    ) -> BudgetDecision:
        """
        Check if operation is within budget.

        Args:
            tokens: Token count for operation (input tokens)
            model: LLM model name
            operation: Operation name (for per-operation ceilings)
            estimate_output_tokens: Estimated output tokens (default: same as input)

        Returns:
            BudgetDecision with allowed flag and details
        """
        # Estimate cost
        output_tokens = estimate_output_tokens or tokens
        estimated_cost = self._estimate_cost(tokens, output_tokens, model)

        # Check global token ceiling
        if self.global_token_ceiling is not None:
            if self.tokens_used + tokens > self.global_token_ceiling:
                return BudgetDecision(
                    allowed=False,
                    reason=f"Global token ceiling exceeded: {self.tokens_used + tokens} > {self.global_token_ceiling}",
                    remaining_tokens=max(0, self.global_token_ceiling - self.tokens_used),
                    ceiling_hit="global_tokens",
                )

        # Check global cost ceiling
        if self.global_cost_ceiling is not None:
            if self.cost_used + estimated_cost > self.global_cost_ceiling:
                return BudgetDecision(
                    allowed=False,
                    reason=f"Global cost ceiling exceeded: ${self.cost_used + estimated_cost:.3f} > ${self.global_cost_ceiling:.3f}",
                    remaining_cost=max(0, self.global_cost_ceiling - self.cost_used),
                    ceiling_hit="global_cost",
                )

        # Check per-operation ceiling
        if operation and operation in self.per_operation_ceilings:
            operation_ceiling = self.per_operation_ceilings[operation]
            operation_used = self.operation_costs.get(operation, 0.0)

            if operation_used + estimated_cost > operation_ceiling:
                return BudgetDecision(
                    allowed=False,
                    reason=f"Operation ceiling exceeded for {operation}: ${operation_used + estimated_cost:.3f} > ${operation_ceiling:.3f}",
                    remaining_cost=max(0, operation_ceiling - operation_used),
                    ceiling_hit=f"operation_{operation}",
                )

        # All checks passed
        return BudgetDecision(
            allowed=True,
            reason="Within budget",
            remaining_tokens=(
                self.global_token_ceiling - self.tokens_used if self.global_token_ceiling else None
            ),
            remaining_cost=(
                self.global_cost_ceiling - self.cost_used if self.global_cost_ceiling else None
            ),
        )

    def record_usage(
        self,
        tokens: int,
        cost: float,
        operation: str | None = None,
    ) -> None:
        """
        Record actual token/cost usage.

        Args:
            tokens: Actual tokens used
            cost: Actual cost in USD
            operation: Operation name (for per-operation tracking)
        """
        self.tokens_used += tokens
        self.cost_used += cost

        if operation:
            self.operation_costs[operation] = self.operation_costs.get(operation, 0.0) + cost

        logger.debug(
            f"Budget usage recorded: {tokens} tokens, ${cost:.4f} "
            f"(total: {self.tokens_used} tokens, ${self.cost_used:.4f})"
        )

    def get_stats(self) -> dict[str, any]:
        """
        Get budget usage statistics.

        Returns:
            Dict with usage stats
        """
        stats = {
            "tokens_used": self.tokens_used,
            "cost_used": self.cost_used,
            "operation_costs": self.operation_costs,
        }

        if self.global_token_ceiling:
            stats["token_utilization"] = self.tokens_used / self.global_token_ceiling

        if self.global_cost_ceiling:
            stats["cost_utilization"] = self.cost_used / self.global_cost_ceiling

        return stats

    def reset(self) -> None:
        """Reset budget tracking (useful for testing)."""
        self.tokens_used = 0
        self.cost_used = 0.0
        self.operation_costs.clear()
        logger.info("Budget tracking reset")

    def _estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> float:
        """
        Estimate cost for token usage.

        Args:
            input_tokens: Input token count
            output_tokens: Output token count
            model: Model name

        Returns:
            Estimated cost in USD
        """
        # Get pricing for model (fallback to default)
        # Ensure pricing is loaded (supports lazy loading)
        pricing_data = _ensure_model_pricing_loaded()
        pricing = pricing_data.get(model, pricing_data["default"])

        cost_input = (input_tokens / 1000.0) * pricing["input"]
        cost_output = (output_tokens / 1000.0) * pricing["output"]

        return cost_input + cost_output

    @classmethod
    def for_quorum(cls) -> "BudgetGuard":
        """
        Create BudgetGuard configured for Quorum pipeline.

        Returns:
            BudgetGuard with Quorum-specific ceilings
        """
        try:
            from sibyl.config.loader import load_core_config

            config = load_core_config()

            # Get consensus config for pipeline costs
            consensus_config = config.get("consensus", {})
            pipeline_costs = consensus_config.get("pipeline_costs", {})
            max_cost_per_pipeline = consensus_config.get("max_cost_per_pipeline_cents", 5.0)

            # Map pipeline_costs keys to quorum operation names
            per_operation_ceilings = {
                f"quorum_{key}": value for key, value in pipeline_costs.items()
            }

            # Fallback defaults if config is empty
            if not per_operation_ceilings:
                per_operation_ceilings = {
                    "quorum_diagnosis": 0.5,
                    "quorum_strategy": 0.4,
                    "quorum_location": 0.8,
                    "quorum_generation": 1.5,
                    "quorum_validation": 0.3,
                }

            return cls(
                global_cost_ceiling_usd=max_cost_per_pipeline,
                per_operation_ceilings=per_operation_ceilings,
            )
        except Exception as e:
            logger.warning("Failed to load quorum config: %s, using fallback values", e)
            # Fallback to hardcoded values
            return cls(
                global_cost_ceiling_usd=5.0,
                per_operation_ceilings={
                    "quorum_diagnosis": 0.5,
                    "quorum_strategy": 0.4,
                    "quorum_location": 0.8,
                    "quorum_generation": 1.5,
                    "quorum_validation": 0.3,
                },
            )

    @classmethod
    def for_orchestration(cls, max_cost_usd: float = 10.0) -> "BudgetGuard":
        """
        Create BudgetGuard configured for orchestration workflows.

        Args:
            max_cost_usd: Maximum cost for workflow

        Returns:
            BudgetGuard with orchestration-specific limits
        """
        return cls(
            global_cost_ceiling_usd=max_cost_usd,
        )

    @classmethod
    def unlimited(cls) -> "BudgetGuard":
        """
        Create BudgetGuard with no limits (for testing/development).

        Returns:
            BudgetGuard with unlimited budget
        """
        return cls()
