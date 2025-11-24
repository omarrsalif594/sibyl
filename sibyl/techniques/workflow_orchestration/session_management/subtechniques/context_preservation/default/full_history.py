"""
Full history context preservation implementation.

Preserves all messages without filtering. Useful when:
- Token budget is large enough for complete history
- Maximum accuracy is required
- Session is still small/manageable
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FullHistoryResult:
    """Result of full history context preservation."""

    preserved_messages: list[dict[str, Any]]
    original_count: int
    preserved_count: int
    dropped_count: int
    max_messages_warning: bool


class FullHistoryImplementation:
    """Full history context preservation.

    Pass-through implementation that keeps all messages without filtering.

    Use this when:
    - Token budget is sufficient for full context
    - All historical context is critical
    - Session hasn't reached concerning size yet
    - Maximum fidelity is required

    Includes optional warnings when message count becomes very large.
    """

    def __init__(self) -> None:
        self._name = "full_history"
        self._description = "Keep all messages (no filtering)"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> FullHistoryResult:
        """Execute full history preservation (pass-through).

        Args:
            input_data: Dict with:
                - messages: List of message dicts to preserve
                - context_items: Alternative - list of items to preserve
            config: Merged configuration with:
                - warn_threshold: Message count to trigger warning (default: 100)
                - max_messages: Hard limit on messages (default: None = unlimited)
                - add_metadata: Add preservation metadata (default: False)

        Returns:
            FullHistoryResult with all messages preserved
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
        warn_threshold = config.get("warn_threshold", 100)
        max_messages = config.get("max_messages")
        add_metadata = config.get("add_metadata", False)

        logger.debug(
            f"Full history preservation: {original_count} messages "
            f"(warn_threshold={warn_threshold})"
        )

        # Check warning threshold
        max_messages_warning = False
        if original_count >= warn_threshold:
            logger.warning(
                f"Full history contains {original_count} messages, which exceeds "
                f"warning threshold ({warn_threshold}). Consider using a filtering strategy."
            )
            max_messages_warning = True

        # Apply hard limit if configured
        dropped_count = 0
        if max_messages is not None and original_count > max_messages:
            logger.warning(
                "Applying max_messages limit: keeping last %s of %s messages",
                max_messages,
                original_count,
            )
            preserved_messages = messages[-max_messages:]
            dropped_count = original_count - max_messages
        else:
            preserved_messages = messages

        # Optionally add metadata
        if add_metadata and not dropped_count:
            result_messages = []
            for msg in preserved_messages:
                if isinstance(msg, dict):
                    msg_copy = msg.copy()
                    if "metadata" not in msg_copy:
                        msg_copy["metadata"] = {}
                    msg_copy["metadata"]["preservation"] = "full_history"
                    result_messages.append(msg_copy)
                else:
                    result_messages.append(msg)
            preserved_messages = result_messages

        preserved_count = len(preserved_messages)

        logger.debug(
            f"Full history result: {preserved_count} messages preserved, "
            f"{dropped_count} dropped (if any)"
        )

        return FullHistoryResult(
            preserved_messages=preserved_messages,
            original_count=original_count,
            preserved_count=preserved_count,
            dropped_count=dropped_count,
            max_messages_warning=max_messages_warning,
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {"warn_threshold": 100, "max_messages": None, "add_metadata": False}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        warn_threshold = config.get("warn_threshold", 100)
        max_messages = config.get("max_messages")
        add_metadata = config.get("add_metadata", False)

        if not isinstance(warn_threshold, int) or warn_threshold < 1:
            msg = f"warn_threshold must be a positive integer, got {warn_threshold}"
            raise ValueError(msg)

        if max_messages is not None:
            if not isinstance(max_messages, int) or max_messages < 1:
                msg = f"max_messages must be a positive integer or None, got {max_messages}"
                raise ValueError(msg)

        if not isinstance(add_metadata, bool):
            msg = f"add_metadata must be a boolean, got {type(add_metadata)}"
            raise TypeError(msg)

        return True
