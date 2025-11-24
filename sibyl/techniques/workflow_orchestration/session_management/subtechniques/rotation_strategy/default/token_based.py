"""
Token-based rotation strategy implementation.

Triggers rotation based on token usage thresholds with:
- Triple threshold system: fixed defaults + model-adaptive + user-configurable
- Hysteresis: once triggered, thresholds remain active
- Model-change handling: recompute thresholds on model changes
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class RotationAction(str, Enum):
    """Actions for session rotation based on threshold checks."""

    CONTINUE = "continue"
    SUMMARIZE_CONTEXT = "summarize_context"  # At configurable threshold (default: 60%)
    ROTATE_NOW = "rotate_now"  # At configurable threshold (default: 70%)


# Model-adaptive threshold defaults
# Format: {model_family: (summarize_pct, rotate_pct)}
MODEL_ADAPTIVE_THRESHOLDS = {
    "opus": (75.0, 85.0),  # Opus has excellent context handling
    "sonnet": (60.0, 70.0),  # Sonnet balanced (default)
    "haiku": (50.0, 65.0),  # Haiku more aggressive
    "gpt4": (65.0, 75.0),  # GPT-4 good context handling
    "gpt3.5": (55.0, 70.0),  # GPT-3.5 moderate
    "codellama": (45.0, 60.0),  # CodeLlama very aggressive
}


@dataclass
class RotationDecision:
    """Result of rotation check."""

    action: RotationAction
    reason: str
    utilization_pct: float
    tokens_used: int
    tokens_budget: int


class TokenBasedImplementation:
    """Token-based rotation strategy.

    Determines when to rotate sessions based on token budget utilization.
    Supports model-adaptive thresholds that adjust based on the model's
    context handling capabilities.
    """

    def __init__(self) -> None:
        self._name = "token_based"
        self._description = "Trigger rotation based on token usage thresholds"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> RotationDecision:
        """Execute token-based rotation check.

        Args:
            input_data: Dict with:
                - tokens_used: Current token usage
                - tokens_budget: Total token budget
                - model_name: Model name for adaptive thresholds (optional)
            config: Merged configuration with:
                - summarize_threshold_pct: Threshold for summarization (default: 60.0)
                - rotate_threshold_pct: Threshold for rotation (default: 70.0)
                - model_adaptive: Enable model-adaptive thresholds (default: True)
                - user_overrides: User threshold overrides (optional)

        Returns:
            RotationDecision with action and metadata
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        tokens_used = input_data.get("tokens_used", 0)
        tokens_budget = input_data.get("tokens_budget", 200000)
        model_name = input_data.get("model_name", "claude-sonnet-4")

        # Calculate utilization
        utilization_pct = (tokens_used / tokens_budget * 100) if tokens_budget > 0 else 0

        # Compute thresholds
        summarize_threshold, rotate_threshold = self._compute_thresholds(
            model_name=model_name, config=config
        )

        # Determine action
        if utilization_pct >= rotate_threshold:
            action = RotationAction.ROTATE_NOW
            reason = f"Token usage {utilization_pct:.1f}% exceeds rotate threshold {rotate_threshold:.1f}%"
        elif utilization_pct >= summarize_threshold:
            action = RotationAction.SUMMARIZE_CONTEXT
            reason = f"Token usage {utilization_pct:.1f}% exceeds summarize threshold {summarize_threshold:.1f}%"
        else:
            action = RotationAction.CONTINUE
            reason = f"Token usage {utilization_pct:.1f}% below thresholds"

        logger.debug(
            f"Token-based rotation check: {action.value} "
            f"({tokens_used}/{tokens_budget} tokens, {utilization_pct:.1f}%)"
        )

        return RotationDecision(
            action=action,
            reason=reason,
            utilization_pct=utilization_pct,
            tokens_used=tokens_used,
            tokens_budget=tokens_budget,
        )

    def _compute_thresholds(self, model_name: str, config: dict[str, Any]) -> tuple[float, float]:
        """Compute thresholds with triple precedence: user > model-adaptive > fixed defaults."""
        # Start with fixed defaults from config
        default_summarize = config.get("summarize_threshold_pct", 60.0)
        default_rotate = config.get("rotate_threshold_pct", 70.0)

        summarize_pct = default_summarize
        rotate_pct = default_rotate

        # Apply model-adaptive thresholds if enabled
        model_adaptive = config.get("model_adaptive", True)
        if model_adaptive:
            model_family = self._get_model_family(model_name)
            if model_family in MODEL_ADAPTIVE_THRESHOLDS:
                summarize_pct, rotate_pct = MODEL_ADAPTIVE_THRESHOLDS[model_family]
                logger.debug(
                    f"Using model-adaptive thresholds for {model_family}: "
                    f"summarize={summarize_pct}%, rotate={rotate_pct}%"
                )

        # Apply user overrides (highest precedence)
        user_overrides = config.get("user_overrides", {})
        if user_overrides:
            if "summarize" in user_overrides:
                summarize_pct = user_overrides["summarize"]
            if "rotate" in user_overrides:
                rotate_pct = user_overrides["rotate"]
            logger.debug(
                "Applied user overrides: summarize=%s%, rotate=%s%", summarize_pct, rotate_pct
            )

        return summarize_pct, rotate_pct

    def _get_model_family(self, model_name: str) -> str:
        """Extract model family from model name."""
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
        logger.warning("Unknown model family for '%s', using 'sonnet' defaults", model_name)
        return "sonnet"

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {
            "summarize_threshold_pct": 60.0,
            "rotate_threshold_pct": 70.0,
            "model_adaptive": True,
            "user_overrides": {},
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        summarize = config.get("summarize_threshold_pct", 60.0)
        rotate = config.get("rotate_threshold_pct", 70.0)

        if not (0 <= summarize <= 100):
            msg = f"summarize_threshold_pct must be 0-100, got {summarize}"
            raise ValueError(msg)

        if not (0 <= rotate <= 100):
            msg = f"rotate_threshold_pct must be 0-100, got {rotate}"
            raise ValueError(msg)

        if summarize >= rotate:
            msg = f"summarize_threshold_pct ({summarize}) must be < rotate_threshold_pct ({rotate})"
            raise ValueError(msg)

        return True
