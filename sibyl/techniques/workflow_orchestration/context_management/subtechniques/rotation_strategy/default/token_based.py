"""
Token Based implementation for rotation_strategy.

Rotates context when token count exceeds threshold by removing oldest items first.
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


class TokenBasedImplementation:
    """Token Based rotation implementation.

    Rotates context when token count exceeds threshold by removing oldest items first
    until the context is under the max token budget.
    """

    def __init__(self) -> None:
        self._name = "token_based"
        self._description = (
            "Rotate context when token count exceeds threshold, removing oldest items first"
        )
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute token-based rotation.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and "max_tokens" (int)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with rotated context
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        max_tokens: int = input_data.get("max_tokens", 4000)

        # Calculate token counts if not present
        for item in context_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Sort by timestamp (oldest first)
        sorted_items = sorted(context_items, key=lambda x: x.timestamp or 0)

        # Calculate current total
        total_tokens = sum(item.token_count for item in sorted_items)

        # Remove oldest items until under budget
        kept_items = []
        removed_count = 0
        tokens_saved = 0

        if total_tokens <= max_tokens:
            # No rotation needed
            kept_items = sorted_items
        else:
            # Remove from oldest until we're under budget
            current_tokens = 0
            for item in reversed(sorted_items):  # Start from newest
                if current_tokens + item.token_count <= max_tokens:
                    kept_items.insert(0, item)
                    current_tokens += item.token_count
                else:
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
                "rotation_strategy": "token_based",
                "original_count": len(context_items),
                "original_tokens": total_tokens,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="token_based_rotation",
            items_kept=len(kept_items),
            items_removed=removed_count,
            tokens_saved=tokens_saved,
            metadata={
                "max_tokens": max_tokens,
                "strategy": "oldest_first",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {
            "default_max_tokens": 4000,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "max_tokens" in config:
            if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
                return False
        return True
