"""
No summarization implementation (pass-through).

Returns messages unchanged without any summarization.
Useful when summarization is disabled or not needed.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class NoSummarizationResult:
    """Result of no-summarization pass-through."""

    summary: list[dict[str, Any]]
    original_count: int
    summary_count: int
    compression_ratio: float
    method: str


class NoSummarizeImplementation:
    """No summarization implementation.

    Pass-through implementation that returns messages unchanged.
    Useful when:
    - Summarization is explicitly disabled
    - Message count is already low
    - Full context preservation is required
    """

    def __init__(self) -> None:
        self._name = "no_summarize"
        self._description = "Pass-through, no summarization"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> NoSummarizationResult:
        """Execute no-summarization (pass-through).

        Args:
            input_data: Dict with:
                - messages: List of message dicts with 'content' field
                - context_items: Alternative - list of text items
            config: Merged configuration with:
                - add_metadata: Add pass-through metadata to messages (default: False)

        Returns:
            NoSummarizationResult with unchanged messages
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
        add_metadata = config.get("add_metadata", False)

        logger.debug("No summarization: passing through %s messages unchanged", original_count)

        # Optionally add metadata to indicate pass-through
        if add_metadata:
            summary = []
            for msg in messages:
                if isinstance(msg, dict):
                    msg_copy = msg.copy()
                    if "metadata" not in msg_copy:
                        msg_copy["metadata"] = {}
                    msg_copy["metadata"]["summarization"] = "pass_through"
                    summary.append(msg_copy)
                else:
                    summary.append(msg)
        else:
            # Return messages unchanged
            summary = messages

        return NoSummarizationResult(
            summary=summary,
            original_count=original_count,
            summary_count=len(summary),
            compression_ratio=1.0,
            method="no_summarization",
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {"add_metadata": False}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        add_metadata = config.get("add_metadata", False)

        if not isinstance(add_metadata, bool):
            msg = f"add_metadata must be a boolean, got {type(add_metadata)}"
            raise TypeError(msg)

        return True
