"""
No Rotation implementation for rotation_strategy.

Pass-through implementation that performs no rotation.
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


class NoRotationImplementation:
    """No Rotation implementation.

    Pass-through implementation that returns all context items unchanged.
    """

    def __init__(self) -> None:
        self._name = "no_rotation"
        self._description = "Pass-through implementation with no rotation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute no rotation (pass-through).

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and "max_tokens" (int)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with unchanged context
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        max_tokens: int = input_data.get("max_tokens", 4000)

        # Calculate token counts if not present
        for item in context_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Calculate total tokens
        total_tokens = sum(item.token_count for item in context_items)
        utilization = total_tokens / max_tokens if max_tokens > 0 else 0.0

        # Create context state with all items
        context_state = ContextState(
            items=context_items,
            total_tokens=total_tokens,
            capacity_tokens=max_tokens,
            utilization=utilization,
            metadata={
                "rotation_strategy": "no_rotation",
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="no_rotation",
            items_kept=len(context_items),
            items_removed=0,
            tokens_saved=0,
            metadata={
                "max_tokens": max_tokens,
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
