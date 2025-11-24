"""Formatting technique protocols and shared types."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class FormatResult:
    """Result of a formatting operation."""

    formatted_value: str
    original_value: str
    metadata: dict[str, Any] | None = None


@runtime_checkable
class Formatter(Protocol):
    """Protocol for formatting strategies."""

    @property
    def name(self) -> str:
        """Formatter name."""
        ...

    def format(self, value: str, context: dict[str, Any]) -> FormatResult:
        """Format a value.

        Args:
            value: Value to format
            context: Formatting context

        Returns:
            Format result
        """
        ...
