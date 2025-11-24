"""
Sliding window context preservation implementation.

Keeps the most recent N messages and drops older ones.
Simple, predictable, and efficient approach to context management.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SlidingWindowResult:
    """Result of sliding window context preservation."""

    preserved_messages: list[dict[str, Any]]
    original_count: int
    preserved_count: int
    dropped_count: int
    window_size: int


class SlidingWindowImplementation:
    """Sliding window context preservation.

    Maintains a fixed-size window of the most recent messages.
    As new messages arrive, older messages are dropped from the window.

    This is the simplest and most predictable context preservation strategy:
    - Always keeps the N most recent messages
    - Oldest messages are dropped first
    - No scoring or importance calculation needed
    """

    def __init__(self) -> None:
        self._name = "sliding_window"
        self._description = "Keep last N messages, drop older ones"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> SlidingWindowResult:
        """Execute sliding window context preservation.

        Args:
            input_data: Dict with:
                - messages: List of message dicts to filter
                - context_items: Alternative - list of items to filter
            config: Merged configuration with:
                - window_size: Number of recent messages to keep (default: 10)
                - min_window_size: Minimum window size (default: 3)

        Returns:
            SlidingWindowResult with preserved messages
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        # Extract messages
        messages = input_data.get("messages", [])
        if not messages:
            context_items = input_data.get("context_items", [])
            if isinstance(context_items, list):
                messages = [{"content": str(item)} for item in context_items]

        if not isinstance(messages, list):
            msg = "messages must be a list"
            raise TypeError(msg)

        original_count = len(messages)

        # Get configuration
        window_size = config.get("window_size", 10)
        min_window_size = config.get("min_window_size", 3)

        # Ensure window size is at least the minimum
        effective_window_size = max(window_size, min_window_size)

        logger.debug(
            "Sliding window: %s messages, window_size=%s", original_count, effective_window_size
        )

        # Keep only the last N messages
        if original_count <= effective_window_size:
            # All messages fit in window
            preserved_messages = messages
            dropped_count = 0
        else:
            # Keep only the most recent messages
            preserved_messages = messages[-effective_window_size:]
            dropped_count = original_count - effective_window_size

        preserved_count = len(preserved_messages)

        logger.debug(
            "Sliding window result: kept %s, dropped %s messages", preserved_count, dropped_count
        )

        return SlidingWindowResult(
            preserved_messages=preserved_messages,
            original_count=original_count,
            preserved_count=preserved_count,
            dropped_count=dropped_count,
            window_size=effective_window_size,
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {"window_size": 10, "min_window_size": 3}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        window_size = config.get("window_size", 10)
        min_window_size = config.get("min_window_size", 3)

        if not isinstance(window_size, int) or window_size < 1:
            msg = f"window_size must be a positive integer, got {window_size}"
            raise ValueError(msg)

        if not isinstance(min_window_size, int) or min_window_size < 1:
            msg = f"min_window_size must be a positive integer, got {min_window_size}"
            raise ValueError(msg)

        if min_window_size > window_size:
            logger.warning(
                f"min_window_size ({min_window_size}) > window_size ({window_size}). "
                f"Using min_window_size as effective window size."
            )

        if window_size > 1000:
            logger.warning(
                f"window_size {window_size} is very large. "
                "Consider using token-based limits instead."
            )

        return True
