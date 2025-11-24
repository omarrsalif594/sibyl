"""
Threshold Based implementation for rotation_strategy.

Rotates context when utilization exceeds threshold by removing lowest priority items.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.workflow_orchestration.context_management.protocols import (
    ContextItem,
    ContextManagementResult,
    ContextState,
)


def estimate_tokens(text: str) -> int:
    """Estimate token count using simple whitespace splitting with 1.3x multiplier."""
    return int(len(text.split()) * 1.3)


class ThresholdBasedImplementation:
    """Threshold Based rotation implementation.

    Rotates context when utilization exceeds a configurable threshold (e.g., 80%)
    by removing lowest priority items.
    """

    def __init__(self) -> None:
        self._name = "threshold_based"
        self._description = (
            "Rotate when utilization exceeds threshold, removing lowest priority items"
        )
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute threshold-based rotation.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and "max_tokens" (int)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with rotated context
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        max_tokens: int = input_data.get("max_tokens", 4000)
        threshold: float = config.get("threshold", 0.8)  # Default 80% utilization

        # Calculate token counts if not present
        for item in context_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Calculate current total
        total_tokens = sum(item.token_count for item in context_items)
        current_utilization = total_tokens / max_tokens if max_tokens > 0 else 0.0

        kept_items = list(context_items)
        removed_count = 0
        tokens_saved = 0

        # Only rotate if we exceed the threshold
        if current_utilization > threshold:
            # Sort by priority (lowest priority first for removal)
            sorted_items = sorted(context_items, key=lambda x: x.priority)

            # Target tokens is the threshold amount
            target_tokens = int(max_tokens * threshold)

            # Remove lowest priority items until under target
            current_tokens = total_tokens
            kept_items = list(sorted_items)

            for item in sorted_items:
                if current_tokens <= target_tokens:
                    break
                kept_items.remove(item)
                current_tokens -= item.token_count
                removed_count += 1
                tokens_saved += item.token_count

        # Calculate final stats
        final_tokens = sum(item.token_count for item in kept_items)
        utilization = final_tokens / max_tokens if max_tokens > 0 else 0.0

        # Create context state
        context_state = ContextState(
            items=kept_items,
            total_tokens=final_tokens,
            capacity_tokens=max_tokens,
            utilization=utilization,
            metadata={
                "rotation_strategy": "threshold_based",
                "original_count": len(context_items),
                "original_tokens": total_tokens,
                "threshold": threshold,
                "exceeded_threshold": current_utilization > threshold,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="threshold_based_rotation",
            items_kept=len(kept_items),
            items_removed=removed_count,
            tokens_saved=tokens_saved,
            metadata={
                "max_tokens": max_tokens,
                "threshold": threshold,
                "initial_utilization": current_utilization,
                "strategy": "lowest_priority_first",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {
            "threshold": 0.8,  # 80% utilization
            "default_max_tokens": 4000,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "threshold" in config:
            threshold = config["threshold"]
            if not isinstance(threshold, (int, float)) or threshold <= 0 or threshold > 1:
                return False
        if "max_tokens" in config:
            if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
                return False
        return True
