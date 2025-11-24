"""
Recency implementation for prioritization.

Prioritizes context items based on timestamps (most recent first).
"""

import time
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


class RecencyImplementation:
    """Recency prioritization implementation.

    Prioritizes context items based on timestamps, with most recent items first.
    """

    def __init__(self) -> None:
        self._name = "recency"
        self._description = "Prioritize based on timestamps (most recent first)"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute recency-based prioritization.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and optional "query" (str)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with prioritized context items
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        input_data.get("query")

        # Assign timestamps if not present (use current time)
        current_time = time.time()
        for item in context_items:
            if item.timestamp is None:
                item.timestamp = current_time

        # Sort by timestamp (most recent first)
        sorted_items = sorted(context_items, key=lambda x: x.timestamp or 0, reverse=True)

        # Update priority scores based on recency
        # Most recent gets highest priority
        for idx, item in enumerate(sorted_items):
            # Priority from 1.0 (most recent) to 0.1 (oldest)
            # Use exponential decay for more natural distribution
            priority = max(0.1, 1.0 - (idx / len(sorted_items)) * 0.9)
            item.priority = priority

        # Calculate token counts if not present
        for item in sorted_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Calculate stats
        total_tokens = sum(item.token_count for item in sorted_items)

        # Create context state
        context_state = ContextState(
            items=sorted_items,
            total_tokens=total_tokens,
            capacity_tokens=total_tokens,
            utilization=1.0,
            metadata={
                "prioritization_strategy": "recency",
                "sort_order": "most_recent_first",
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="recency_prioritization",
            items_kept=len(sorted_items),
            items_removed=0,
            tokens_saved=0,
            metadata={
                "strategy": "recency",
                "items_processed": len(context_items),
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
