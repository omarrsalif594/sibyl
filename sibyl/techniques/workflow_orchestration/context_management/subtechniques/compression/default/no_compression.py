"""
No Compression implementation for compression.

Pass-through implementation that performs no compression.
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


class NoCompressionImplementation:
    """No Compression implementation.

    Pass-through implementation that returns content unchanged.
    """

    def __init__(self) -> None:
        self._name = "no_compression"
        self._description = "Pass-through implementation with no compression"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute no compression (pass-through).

        Args:
            input_data: Dict with "content" (str) and "target_ratio" (float)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with unchanged content
        """
        content: str = input_data.get("content", "")
        target_ratio: float = input_data.get("target_ratio", 1.0)

        # Calculate tokens
        content_tokens = estimate_tokens(content)

        # Create context item with unchanged content
        item = ContextItem(
            id="uncompressed",
            content=content,
            priority=1.0,
            token_count=content_tokens,
            metadata={
                "compression_type": "none",
            },
        )

        # Create context state
        context_state = ContextState(
            items=[item],
            total_tokens=content_tokens,
            capacity_tokens=content_tokens,
            utilization=1.0,
            metadata={
                "compression_strategy": "no_compression",
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="no_compression",
            items_kept=1,
            items_removed=0,
            tokens_saved=0,
            metadata={
                "target_ratio": target_ratio,
                "actual_ratio": 1.0,
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
