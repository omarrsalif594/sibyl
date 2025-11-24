"""Budget management with model ladder for downgrade strategy."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from sibyl.core.infrastructure.llm.errors import BudgetExceededError

logger = logging.getLogger(__name__)


@dataclass
class ModelTier:
    """Model tier for budget downgrade ladder."""

    provider: str  # "anthropic", "openai", "ollama"
    model: str  # Model name
    cost_per_1k_input: float  # Cost per 1K input tokens (USD)
    cost_per_1k_output: float  # Cost per 1K output tokens (USD)
    max_tokens: int  # Maximum context window
    quality_score: int  # Quality score (1-10, higher is better)

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost for token usage.

        Args:
            tokens_in: Input tokens
            tokens_out: Output tokens

        Returns:
            Estimated cost in USD
        """
        cost_in = (tokens_in / 1000.0) * self.cost_per_1k_input
        cost_out = (tokens_out / 1000.0) * self.cost_per_1k_output
        return cost_in + cost_out


def _build_model_ladder_from_config() -> list[ModelTier]:
    """Build model ladder from configuration.

    Returns:
        List of ModelTier sorted by quality_score descending

    Note:
        This function dynamically loads the model ladder from the configuration
        file, making it easy to add or modify providers without code changes.
    """
    from sibyl.core.server.config import get_config

    try:
        config = get_config()

        if not config.providers:
            logger.warning("No provider configuration found, using empty model ladder")
            return []

        model_tiers = []

        # Build model tiers from all LLM providers
        for provider_name, provider_config in config.providers.llm.items():
            if not provider_config.enabled:
                continue

            for model_config in provider_config.models:
                tier = ModelTier(
                    provider=provider_name,
                    model=model_config.name,
                    cost_per_1k_input=model_config.cost_per_1k_input,
                    cost_per_1k_output=model_config.cost_per_1k_output,
                    max_tokens=model_config.max_tokens,
                    quality_score=model_config.quality_score,
                )
                model_tiers.append(tier)

        # Sort by quality_score descending (highest quality first)
        model_tiers.sort(key=lambda t: t.quality_score, reverse=True)

        logger.info("Built model ladder with %s models from configuration", len(model_tiers))
        return model_tiers

    except Exception as e:
        logger.exception("Failed to build model ladder from config: %s", e)
        return []


# Global model ladder (lazy-loaded from config)
_MODEL_LADDER: list[ModelTier] | None = None


def get_model_ladder() -> list[ModelTier]:
    """Get model ladder (lazy-loaded from configuration).

    Returns:
        List of ModelTier sorted by quality_score descending
    """
    global _MODEL_LADDER

    if _MODEL_LADDER is None:
        _MODEL_LADDER = _build_model_ladder_from_config()

    return _MODEL_LADDER


# Note: Lazy-loaded to avoid circular imports during module initialization
_MODEL_LADDER_INITIALIZED = False


def _ensure_model_ladder_loaded() -> None:
    """Ensure MODEL_LADDER is loaded (call this before accessing it)."""
    global _MODEL_LADDER_INITIALIZED, MODEL_LADDER
    if not _MODEL_LADDER_INITIALIZED:
        MODEL_LADDER = get_model_ladder()
        _MODEL_LADDER_INITIALIZED = True


# Initialize as empty list, will be populated on first access
MODEL_LADDER = []


class BudgetManager:
    """Token and cost budget enforcement with degradation strategies.

    Strategies:
    - "fail": Fail immediately when budget exceeded
    - "downgrade": Move to cheaper model on next tier
    - "summarize": Trigger context summarization
    """

    def __init__(
        self,
        max_tokens: int,
        max_cost_usd: float | None = None,
        degradation_strategy: str | None = None,
        initial_tier: int | None = None,
    ) -> None:
        """Initialize budget manager.

        Args:
            max_tokens: Maximum token budget
            max_cost_usd: Optional maximum cost budget (USD)
            degradation_strategy: Strategy when budget exceeded ("fail", "downgrade", "summarize")
                                 If None, loads from core config
            initial_tier: Starting tier index in MODEL_LADDER
                         If None, loads from core config
        """
        # Load from config if not provided
        if degradation_strategy is None or initial_tier is None:
            try:
                from sibyl.config.loader import load_core_config

                core_config = load_core_config()
                budget_config = core_config.get("budget", {})
                model_selection = budget_config.get("model_selection", {})

                if degradation_strategy is None:
                    # Map strategy name to degradation mode
                    strategy = model_selection.get("strategy", "downgrade_cascade")
                    if strategy == "downgrade_cascade" or model_selection.get(
                        "allow_downgrade", True
                    ):
                        degradation_strategy = "downgrade"
                    else:
                        degradation_strategy = "fail"

                if initial_tier is None:
                    initial_tier = budget_config.get("model_tier_initial", 1)
            except Exception as e:
                logger.warning("Failed to load budget config: %s, using defaults", e)
                if degradation_strategy is None:
                    degradation_strategy = "downgrade"
                if initial_tier is None:
                    initial_tier = 1

        self.max_tokens = max_tokens
        self.max_cost_usd = max_cost_usd
        self.degradation = degradation_strategy
        self.current_tier = initial_tier

        self.tokens_spent = 0
        self.cost_spent = 0.0

        self._lock = asyncio.Lock()

        # Get model ladder from config
        ladder = get_model_ladder()
        initial_model = (
            ladder[initial_tier].model if ladder and initial_tier < len(ladder) else "unknown"
        )

        logger.info(
            f"Budget manager initialized: max_tokens={max_tokens}, "
            f"max_cost={max_cost_usd}, strategy={degradation_strategy}, "
            f"initial_model={initial_model}"
        )

    async def check_and_reserve(
        self, estimated_tokens: int, estimated_cost: float
    ) -> dict[str, Any]:
        """Preflight check; returns action: "proceed" | "downgrade" | "summarize" | "fail".

        Args:
            estimated_tokens: Estimated token count for request
            estimated_cost: Estimated cost for request

        Returns:
            Action dict with:
            - action: "proceed" | "downgrade" | "summarize" | "fail"
            - model: ModelTier to use (if proceed or downgrade)

        Raises:
            BudgetExceededError: If strategy is "fail" or no options left
        """
        async with self._lock:
            ladder = get_model_ladder()
            if not ladder:
                msg = "No models available in model ladder"
                raise BudgetExceededError(msg)

            current_model = ladder[self.current_tier]

            # Token check
            if self.tokens_spent + estimated_tokens > self.max_tokens:
                logger.warning(
                    "Token budget limit approaching: %s/%s",
                    self.tokens_spent + estimated_tokens,
                    self.max_tokens,
                )

                if self.degradation == "fail":
                    msg = f"Token budget exhausted: {self.tokens_spent}/{self.max_tokens}"
                    raise BudgetExceededError(msg)

                if self.degradation == "downgrade":
                    # Try next cheaper model
                    if self.current_tier < len(ladder) - 1:
                        self.current_tier += 1
                        next_model = ladder[self.current_tier]
                        logger.warning("Downgrading to %s due to token budget", next_model.model)
                        return {"action": "downgrade", "model": next_model}
                    # Already at cheapest model, try summarize
                    logger.warning("At cheapest model, attempting context summarization")
                    return {"action": "summarize", "model": current_model}

                if self.degradation == "summarize":
                    return {"action": "summarize", "model": current_model}

            # Cost check
            if self.max_cost_usd and self.cost_spent + estimated_cost > self.max_cost_usd:
                logger.warning(
                    "Cost budget limit approaching: $%s/$%s",
                    self.cost_spent + estimated_cost,
                    self.max_cost_usd,
                )
                if self.degradation == "downgrade" and self.current_tier < len(ladder) - 1:
                    self.current_tier += 1
                    next_model = ladder[self.current_tier]
                    logger.warning("Downgrading to %s due to cost budget", next_model.model)
                    return {"action": "downgrade", "model": next_model}
                msg = f"Cost budget exhausted: ${self.cost_spent:.2f}/${self.max_cost_usd:.2f}"
                raise BudgetExceededError(msg)

            # Reserve tokens
            self.tokens_spent += estimated_tokens
            self.cost_spent += estimated_cost

            return {"action": "proceed", "model": current_model}

    async def commit(self, actual_tokens: int, actual_cost: float, estimated_tokens: int) -> None:
        """Commit actual usage (adjust reservation).

        Args:
            actual_tokens: Actual tokens used
            actual_cost: Actual cost incurred
            estimated_tokens: Original estimated tokens
        """
        async with self._lock:
            # Adjust for estimation error
            delta_tokens = actual_tokens - estimated_tokens

            # Update spent (already reserved estimated, now adjust)
            self.tokens_spent += delta_tokens

            # Cost was estimated, replace with actual
            # (Note: estimated_cost was added in check_and_reserve, so no adjustment needed if actual == estimated)

            logger.debug(
                "Budget committed: %s tokens (delta: %s), $%s",
                actual_tokens,
                delta_tokens,
                actual_cost,
            )

    async def release_reservation(self, estimated_tokens: int, estimated_cost: float) -> None:
        """Release reservation (e.g., if request failed).

        Args:
            estimated_tokens: Tokens to release
            estimated_cost: Cost to release
        """
        async with self._lock:
            self.tokens_spent -= estimated_tokens
            self.cost_spent -= estimated_cost

            logger.debug("Budget released: %s tokens, $%s", estimated_tokens, estimated_cost)

    def get_current_model(self) -> ModelTier:
        """Get current model tier.

        Returns:
            Current ModelTier
        """
        ladder = get_model_ladder()
        if not ladder:
            msg = "No models available in model ladder"
            raise ValueError(msg)
        return ladder[self.current_tier]

    def get_stats(self) -> dict[str, Any]:
        """Get budget statistics.

        Returns:
            Dict with budget stats
        """
        ladder = get_model_ladder()
        current_model = ladder[self.current_tier] if ladder else None
        current_model_str = (
            f"{current_model.provider}:{current_model.model}" if current_model else "unknown"
        )

        return {
            "max_tokens": self.max_tokens,
            "tokens_spent": self.tokens_spent,
            "tokens_remaining": self.max_tokens - self.tokens_spent,
            "tokens_utilization": self.tokens_spent / self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "cost_spent": self.cost_spent,
            "cost_remaining": (self.max_cost_usd - self.cost_spent if self.max_cost_usd else None),
            "cost_utilization": (
                self.cost_spent / self.max_cost_usd if self.max_cost_usd else None
            ),
            "current_tier": self.current_tier,
            "current_model": current_model_str,
            "degradation_strategy": self.degradation,
        }


class BudgetPolicy:
    """Per-phase budget allocation policy."""

    def __init__(self, total_budget: int, phases: list[str]) -> None:
        """Initialize budget policy.

        Args:
            total_budget: Total token budget
            phases: List of phase names
        """
        self.total_budget = total_budget
        self.phases = phases

        # Load default allocation percentages from configuration or technique
        self.default_allocations = self._load_default_allocations()

        # Compute allocations
        self.allocations = {}
        for phase in phases:
            percentage = self.default_allocations.get(phase, 1.0 / len(phases))
            self.allocations[phase] = int(total_budget * percentage)

        logger.info("Budget policy created: %s", self.allocations)

    def _load_default_allocations(self) -> dict[str, float]:
        """Load default phase allocations from budget_allocation technique or config.

        Returns:
            Dictionary mapping phase names to allocation percentages
        """
        try:
            # Try to load from budget_allocation technique
            from sibyl.techniques.infrastructure.budget_allocation import BudgetAllocationTechnique

            technique = BudgetAllocationTechnique()
            config = technique.get_configuration()
            phase_allocation = config.get("phase_allocation", {})

            # Map generic phase names to specific workflow phases
            # The technique uses: planning, execution, validation
            # This policy uses: compile, test, fix, review, create_pr
            # Map them appropriately
            return {
                "compile": 0.05,  # 5% - just compilation, no LLM
                "test": 0.05,  # 5% - testing, minimal LLM
                "fix": phase_allocation.get("execution", 0.60),  # Use execution phase allocation
                "review": phase_allocation.get(
                    "validation", 0.20
                ),  # Use validation phase allocation
                "create_pr": phase_allocation.get(
                    "planning", 0.10
                ),  # Use planning phase allocation
                # Generic fallbacks for any other phases
                "planning": phase_allocation.get("planning", 0.15),
                "execution": phase_allocation.get("execution", 0.70),
                "validation": phase_allocation.get("validation", 0.15),
            }
        except Exception as e:
            logger.warning(
                "Failed to load budget allocations from technique: %s, using fallback", e
            )
            # Fallback to hardcoded values
            return {
                "compile": 0.05,
                "test": 0.05,
                "fix": 0.60,
                "review": 0.20,
                "create_pr": 0.10,
                "planning": 0.15,
                "execution": 0.70,
                "validation": 0.15,
            }

    def get_phase_budget(self, phase: str) -> int:
        """Get token budget for a phase.

        Args:
            phase: Phase name

        Returns:
            Token budget for phase
        """
        return self.allocations.get(phase, 0)

    def create_phase_manager(
        self,
        phase: str,
        max_cost_usd: float | None = None,
        degradation_strategy: str = "downgrade",
    ) -> BudgetManager:
        """Create budget manager for a phase.

        Args:
            phase: Phase name
            max_cost_usd: Optional cost budget
            degradation_strategy: Degradation strategy

        Returns:
            BudgetManager instance for this phase
        """
        phase_budget = self.get_phase_budget(phase)

        return BudgetManager(
            max_tokens=phase_budget,
            max_cost_usd=max_cost_usd,
            degradation_strategy=degradation_strategy,
        )


def get_model_by_name(provider: str, model: str) -> ModelTier | None:
    """Get model tier by provider and name.

    Args:
        provider: Provider name
        model: Model name

    Returns:
        ModelTier or None if not found
    """
    ladder = get_model_ladder()
    for tier in ladder:
        if tier.provider == provider and tier.model == model:
            return tier
    return None


def get_cheapest_model() -> ModelTier | None:
    """Get cheapest model from ladder.

    Returns:
        Cheapest ModelTier or None if ladder is empty
    """
    ladder = get_model_ladder()
    return ladder[-1] if ladder else None


def get_best_model() -> ModelTier | None:
    """Get best quality model from ladder.

    Returns:
        Best ModelTier or None if ladder is empty
    """
    ladder = get_model_ladder()
    return ladder[0] if ladder else None
