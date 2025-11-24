"""
No Summarize implementation for summarization.

Pass-through implementation that performs no summarization.
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


class NoSummarizeImplementation:
    """No Summarize implementation.

    Pass-through implementation that returns all context items unchanged.
    """

    def __init__(self) -> None:
        self._name = "no_summarize"
        self._description = "Pass-through implementation with no summarization"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute no summarization (pass-through).

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and "target_tokens" (int)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with unchanged context
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        target_tokens: int = input_data.get("target_tokens", 1000)

        # Calculate token counts if not present
        for item in context_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Calculate total tokens
        total_tokens = sum(item.token_count for item in context_items)
        utilization = total_tokens / target_tokens if target_tokens > 0 else 0.0

        # Create context state with all items unchanged
        context_state = ContextState(
            items=context_items,
            total_tokens=total_tokens,
            capacity_tokens=target_tokens,
            utilization=utilization,
            metadata={
                "summarization_strategy": "no_summarize",
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="no_summarization",
            items_kept=len(context_items),
            items_removed=0,
            tokens_saved=0,
            metadata={
                "target_tokens": target_tokens,
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
