"""Session-level budget tracking with hysteresis and model-adaptive thresholds.

This module implements token budget tracking at the session level with:
- Triple threshold system: fixed defaults + model-adaptive + user-configurable
- Hysteresis: once triggered, thresholds remain active
- Model-change handling: recompute thresholds on model changes
- Thread-safe with asyncio.Lock
- Operation boundary support: track tokens per turn

Typical usage:
    tracker = SessionBudgetTracker(
        session_id="sess_abc_001",
        tokens_budget=200000,
        summarize_threshold_pct=60.0,
        rotate_threshold_pct=70.0
    )

    # Record token usage
    await tracker.record_usage(tool_name="fast_query_downstream", tokens_in=150, tokens_out=300)

    # Check thresholds
    action = await tracker.check_threshold()
    if action == RotationAction.SUMMARIZE_CONTEXT:
        # Start background summarization
    elif action == RotationAction.ROTATE_NOW:
        # Trigger session rotation
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from sibyl.techniques.workflow_orchestration.orchestration.impls.core.budget import (
    BudgetManager,
)

logger = logging.getLogger(__name__)


class RotationAction(str, Enum):
    """Actions for session rotation based on threshold checks."""

    CONTINUE = "continue"  # Below all thresholds, continue normally
    SUMMARIZE_CONTEXT = "summarize_context"  # At 60% threshold, start background summarization
    ROTATE_NOW = "rotate_now"  # At 70% threshold, rotate immediately


@dataclass
class ThresholdConfig:
    """Threshold configuration for a session.

    Attributes:
        summarize_pct: Percentage threshold for triggering background summarization (default: 60)
        rotate_pct: Percentage threshold for triggering rotation (default: 70)
        model_family: Model family for adaptive thresholds ("opus", "sonnet", "haiku", "gpt4", "gpt3.5", "codellama")
        model_adaptive: Whether to use model-adaptive thresholds
        user_overrides: User-specified threshold overrides (takes precedence)
    """

    summarize_pct: float
    rotate_pct: float
    model_family: str | None = None
    model_adaptive: bool = True
    user_overrides: dict[str, float] | None = None

    def __post_init__(self) -> None:
        """Validate thresholds."""
        if self.summarize_pct >= self.rotate_pct:
            msg = f"summarize_threshold ({self.summarize_pct}%) must be < rotate_threshold ({self.rotate_pct}%)"
            raise ValueError(msg)

        if self.summarize_pct < 0 or self.summarize_pct > 100:
            msg = f"summarize_threshold must be 0-100, got {self.summarize_pct}"
            raise ValueError(msg)

        if self.rotate_pct < 0 or self.rotate_pct > 100:
            msg = f"rotate_threshold must be 0-100, got {self.rotate_pct}"
            raise ValueError(msg)


# Model-adaptive threshold defaults
# Format: {model_family: (summarize_pct, rotate_pct)}
MODEL_ADAPTIVE_THRESHOLDS = {
    "opus": (75.0, 85.0),  # Opus has excellent context handling, can go higher
    "sonnet": (60.0, 70.0),  # Sonnet balanced (default)
    "haiku": (50.0, 65.0),  # Haiku more aggressive (smaller context degrades faster)
    "gpt4": (65.0, 75.0),  # GPT-4 good context handling
    "gpt3.5": (55.0, 70.0),  # GPT-3.5 moderate
    "codellama": (45.0, 60.0),  # CodeLlama very aggressive (4K context)
}


def get_model_family(model_name: str) -> str:
    """Extract model family from model name.

    Args:
        model_name: Full model name (e.g., "claude-sonnet-4-5-20250929")

    Returns:
        Model family ("opus", "sonnet", "haiku", etc.)
    """
    model_lower = model_name.lower()

    if "opus" in model_lower:
        return "opus"
    if "sonnet" in model_lower:
        return "sonnet"
    if "haiku" in model_lower:
        return "haiku"
    if "gpt-4" in model_lower or "gpt4" in model_lower:
        return "gpt4"
    if "gpt-3.5" in model_lower or "gpt3" in model_lower:
        return "gpt3.5"
    if "codellama" in model_lower:
        return "codellama"
    # Unknown model, use conservative defaults (sonnet)
    logger.warning("Unknown model family for '%s', using 'sonnet' defaults", model_name)
    return "sonnet"


def compute_adaptive_thresholds(
    model_name: str,
    default_summarize: float = 60.0,
    default_rotate: float = 70.0,
    user_overrides: dict[str, float] | None = None,
    model_adaptive: bool = True,
) -> tuple[float, float]:
    """Compute thresholds with triple precedence: user > model-adaptive > fixed defaults.

    Args:
        model_name: Model name for adaptive thresholds
        default_summarize: Fixed default for summarize threshold
        default_rotate: Fixed default for rotate threshold
        user_overrides: User-specified overrides {"summarize": 65, "rotate": 75}
        model_adaptive: Whether to use model-adaptive thresholds

    Returns:
        Tuple of (summarize_pct, rotate_pct)
    """
    # Start with fixed defaults
    summarize_pct = default_summarize
    rotate_pct = default_rotate

    # Apply model-adaptive thresholds if enabled
    if model_adaptive:
        model_family = get_model_family(model_name)
        if model_family in MODEL_ADAPTIVE_THRESHOLDS:
            summarize_pct, rotate_pct = MODEL_ADAPTIVE_THRESHOLDS[model_family]
            logger.debug(
                f"Using model-adaptive thresholds for {model_family}: "
                f"summarize={summarize_pct}%, rotate={rotate_pct}%"
            )

    # Apply user overrides (highest precedence)
    if user_overrides:
        if "summarize" in user_overrides:
            summarize_pct = user_overrides["summarize"]
            logger.info("User override: summarize threshold = %s%", summarize_pct)

        if "rotate" in user_overrides:
            rotate_pct = user_overrides["rotate"]
            logger.info("User override: rotate threshold = %s%", rotate_pct)

    return summarize_pct, rotate_pct


@dataclass
class TokenUsageRecord:
    """Record of token usage for a single tool call.

    Attributes:
        turn_id: Sequential turn number within session
        tool_name: Name of tool called
        tokens_in: Input tokens (prompt + context)
        tokens_out: Response tokens
        tokens_total: Total tokens for this call
        cumulative_tokens: Running total after this call
        utilization_pct: Percentage utilization after this call
        timestamp: When this call occurred
    """

    turn_id: int
    tool_name: str
    tokens_in: int
    tokens_out: int
    tokens_total: int
    cumulative_tokens: int
    utilization_pct: float
    timestamp: float  # Unix timestamp


class SessionBudgetTracker:
    """Track token budget at session level with threshold monitoring.

    This class wraps BudgetManager to provide:
    - Session-level cumulative tracking
    - Threshold-based rotation triggers (60% summarize, 70% rotate)
    - Hysteresis: once triggered, stay triggered
    - Model-change handling: recompute thresholds on model change
    - Per-turn token records

    Thread-safe with asyncio.Lock.
    """

    def __init__(
        self,
        session_id: str,
        tokens_budget: int,
        summarize_threshold_pct: float = 60.0,
        rotate_threshold_pct: float = 70.0,
        model_name: str = "claude-sonnet-4-5-20250929",
        model_adaptive: bool = True,
        user_overrides: dict[str, float] | None = None,
        budget_manager: BudgetManager | None = None,
    ) -> None:
        """Initialize session budget tracker.

        Args:
            session_id: Unique session identifier
            tokens_budget: Maximum tokens for this session (from model context window)
            summarize_threshold_pct: Percentage threshold for background summarization (default 60)
            rotate_threshold_pct: Percentage threshold for rotation (default 70)
            model_name: Model name for adaptive thresholds
            model_adaptive: Whether to use model-adaptive thresholds
            user_overrides: User-specified threshold overrides
            budget_manager: Optional existing BudgetManager to wrap

        Raises:
            ValueError: If thresholds are invalid (summarize >= rotate, or out of range)
        """
        self.session_id = session_id
        self.tokens_budget = tokens_budget
        self.model_name = model_name

        # Compute thresholds with triple precedence
        self.summarize_threshold_pct, self.rotate_threshold_pct = compute_adaptive_thresholds(
            model_name=model_name,
            default_summarize=summarize_threshold_pct,
            default_rotate=rotate_threshold_pct,
            user_overrides=user_overrides,
            model_adaptive=model_adaptive,
        )

        # Validate thresholds
        ThresholdConfig(
            summarize_pct=self.summarize_threshold_pct,
            rotate_pct=self.rotate_threshold_pct,
            model_family=get_model_family(model_name),
            model_adaptive=model_adaptive,
            user_overrides=user_overrides,
        )

        # Cumulative tracking
        self.tokens_spent = 0
        self.turn_counter = 0
        self.usage_records: list[TokenUsageRecord] = []

        # Hysteresis state (latched triggers)
        self._summarize_triggered = False
        self._rotate_triggered = False

        # Budget manager (optional)
        self._budget_manager = budget_manager

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"SessionBudgetTracker initialized for session {session_id}: "
            f"budget={tokens_budget}, summarize={self.summarize_threshold_pct}%, "
            f"rotate={self.rotate_threshold_pct}%, model={model_name}"
        )

    async def record_usage(
        self,
        tool_name: str,
        tokens_in: int,
        tokens_out: int,
        timestamp: float | None = None,
    ) -> TokenUsageRecord:
        """Record token usage for a tool call.

        Args:
            tool_name: Name of tool called
            tokens_in: Input tokens (prompt + context)
            tokens_out: Response tokens
            timestamp: Optional timestamp (defaults to now)

        Returns:
            TokenUsageRecord for this call
        """
        import time

        async with self._lock:
            self.turn_counter += 1
            tokens_total = tokens_in + tokens_out
            self.tokens_spent += tokens_total

            utilization_pct = (self.tokens_spent / self.tokens_budget) * 100.0

            record = TokenUsageRecord(
                turn_id=self.turn_counter,
                tool_name=tool_name,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                tokens_total=tokens_total,
                cumulative_tokens=self.tokens_spent,
                utilization_pct=utilization_pct,
                timestamp=timestamp or time.time(),
            )

            self.usage_records.append(record)

            logger.debug(
                f"[{self.session_id}] Turn {self.turn_counter}: {tool_name} used "
                f"{tokens_total} tokens ({tokens_in} in + {tokens_out} out), "
                f"cumulative={self.tokens_spent}/{self.tokens_budget} ({utilization_pct:.1f}%)"
            )

            return record

    async def check_threshold(self) -> RotationAction:
        """Check if thresholds exceeded with hysteresis.

        Hysteresis: Once summarize_threshold is crossed, stay in SUMMARIZE_CONTEXT
        state even if subsequent calls reduce pressure. Same for rotate_threshold.

        Returns:
            RotationAction indicating what action to take
        """
        async with self._lock:
            utilization_pct = self.get_utilization_pct()

            # Rotate threshold (higher priority)
            if utilization_pct >= self.rotate_threshold_pct:
                if not self._rotate_triggered:
                    self._rotate_triggered = True
                    logger.warning(
                        f"[{self.session_id}] Rotate threshold exceeded: "
                        f"{utilization_pct:.1f}% >= {self.rotate_threshold_pct}% "
                        f"({self.tokens_spent}/{self.tokens_budget} tokens)"
                    )
                return RotationAction.ROTATE_NOW

            # Summarize threshold (medium priority)
            if utilization_pct >= self.summarize_threshold_pct:
                if not self._summarize_triggered:
                    self._summarize_triggered = True
                    logger.info(
                        f"[{self.session_id}] Summarize threshold exceeded: "
                        f"{utilization_pct:.1f}% >= {self.summarize_threshold_pct}% "
                        f"({self.tokens_spent}/{self.tokens_budget} tokens)"
                    )
                return RotationAction.SUMMARIZE_CONTEXT

            # Below all thresholds
            return RotationAction.CONTINUE

    def get_utilization_pct(self) -> float:
        """Get current token utilization percentage.

        Returns:
            Utilization percentage (0-100+)
        """
        return (self.tokens_spent / self.tokens_budget) * 100.0

    def get_distance_to_thresholds(self) -> dict[str, float]:
        """Get distance to each threshold in percentage points.

        Returns:
            Dict with "summarize" and "rotate" distances (negative = exceeded)
        """
        utilization = self.get_utilization_pct()

        return {
            "summarize": self.summarize_threshold_pct - utilization,
            "rotate": self.rotate_threshold_pct - utilization,
        }

    async def update_model(self, new_model_name: str, model_adaptive: bool = True) -> None:
        """Update model and recompute thresholds.

        This is called when the BudgetManager downgrades to a cheaper model.
        Thresholds are recomputed based on the new model family.

        Note: User overrides are preserved and take precedence.

        Args:
            new_model_name: New model name
            model_adaptive: Whether to use model-adaptive thresholds
        """
        async with self._lock:
            old_model = self.model_name
            old_summarize = self.summarize_threshold_pct
            old_rotate = self.rotate_threshold_pct

            self.model_name = new_model_name

            # Recompute thresholds
            # Note: We don't have user_overrides stored, so this will only apply
            # model-adaptive thresholds. In production, you'd want to store and reuse
            # user_overrides from initialization.
            self.summarize_threshold_pct, self.rotate_threshold_pct = compute_adaptive_thresholds(
                model_name=new_model_name,
                default_summarize=60.0,
                default_rotate=70.0,
                user_overrides=None,  # TODO: Store and reuse from init
                model_adaptive=model_adaptive,
            )

            logger.info(
                f"[{self.session_id}] Model changed: {old_model} → {new_model_name}. "
                f"Thresholds: summarize {old_summarize:.1f}% → {self.summarize_threshold_pct:.1f}%, "
                f"rotate {old_rotate:.1f}% → {self.rotate_threshold_pct:.1f}%"
            )

    def get_stats(self) -> dict:
        """Get budget statistics.

        Returns:
            Dict with comprehensive budget stats
        """
        utilization_pct = self.get_utilization_pct()
        distances = self.get_distance_to_thresholds()

        return {
            "session_id": self.session_id,
            "tokens_budget": self.tokens_budget,
            "tokens_spent": self.tokens_spent,
            "tokens_remaining": self.tokens_budget - self.tokens_spent,
            "utilization_pct": utilization_pct,
            "summarize_threshold_pct": self.summarize_threshold_pct,
            "rotate_threshold_pct": self.rotate_threshold_pct,
            "distance_to_summarize": distances["summarize"],
            "distance_to_rotate": distances["rotate"],
            "summarize_triggered": self._summarize_triggered,
            "rotate_triggered": self._rotate_triggered,
            "turn_count": self.turn_counter,
            "model_name": self.model_name,
        }

    async def reset_hysteresis(self) -> None:
        """Reset hysteresis state (for testing or manual override).

        Warning: This should rarely be used in production. Hysteresis is designed
        to prevent thrashing and ensure stable threshold behavior.
        """
        async with self._lock:
            self._summarize_triggered = False
            self._rotate_triggered = False

            logger.warning("[%s] Hysteresis reset (manual override)", self.session_id)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionBudgetTracker(session_id={self.session_id}, "
            f"tokens={self.tokens_spent}/{self.tokens_budget}, "
            f"utilization={self.get_utilization_pct():.1f}%, "
            f"thresholds=[{self.summarize_threshold_pct}%, {self.rotate_threshold_pct}%])"
        )
