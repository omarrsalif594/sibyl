"""
Message count-based rotation strategy implementation.

Triggers rotation based on the number of messages/turns in the session.
Useful for tracking conversation depth regardless of token usage or time.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MessageCountDecision:
    """Result of message count-based rotation check."""

    should_rotate: bool
    reason: str
    message_count: int
    max_message_count: int
    remaining_messages: int


class MessageCountImplementation:
    """Message count-based rotation strategy.

    Rotates sessions based on the number of messages/turns in the conversation.
    This provides a predictable rotation point based on interaction depth rather
    than token usage or elapsed time.
    """

    def __init__(self) -> None:
        self._name = "message_count"
        self._description = "Trigger rotation based on number of messages/turns in session"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> MessageCountDecision:
        """Execute message count-based rotation check.

        Args:
            input_data: Dict with:
                - message_count: Current number of messages in session
                - messages: Alternative - list of messages (will count length)
            config: Merged configuration with:
                - max_message_count: Maximum messages before rotation (default: 50)

        Returns:
            MessageCountDecision with rotation recommendation and metadata
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        # Extract message count
        message_count = input_data.get("message_count")
        if message_count is None:
            # Try to count from messages list
            messages = input_data.get("messages", [])
            message_count = len(messages) if isinstance(messages, list) else 0

        if not isinstance(message_count, int) or message_count < 0:
            msg = f"message_count must be a non-negative integer, got {message_count}"
            raise ValueError(msg)

        # Get threshold from config
        max_message_count = config.get("max_message_count", 50)

        # Calculate remaining messages
        remaining_messages = max(0, max_message_count - message_count)

        # Determine rotation decision
        should_rotate = message_count >= max_message_count

        if should_rotate:
            reason = f"Message count {message_count} meets or exceeds threshold {max_message_count}"
        else:
            reason = (
                f"Message count {message_count} below threshold "
                f"({remaining_messages} messages remaining)"
            )

        logger.debug(
            f"Message count rotation check: rotate={should_rotate} "
            f"(count={message_count}, threshold={max_message_count})"
        )

        return MessageCountDecision(
            should_rotate=should_rotate,
            reason=reason,
            message_count=message_count,
            max_message_count=max_message_count,
            remaining_messages=remaining_messages,
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {"max_message_count": 50}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        max_count = config.get("max_message_count", 50)

        if not isinstance(max_count, int) or max_count <= 0:
            msg = f"max_message_count must be a positive integer, got {max_count}"
            raise ValueError(msg)

        if max_count > 1000:
            logger.warning(
                f"max_message_count {max_count} is very large. "
                "Consider using token-based rotation for long conversations."
            )

        return True
