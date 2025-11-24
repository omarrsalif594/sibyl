"""Validation technique protocols and shared types.

This module defines the protocol interfaces and data structures for validation operations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Validator(Protocol):
    """Protocol for validation implementations."""

    @property
    def name(self) -> str:
        """Implementation name for identification."""
        ...

    def validate(self, data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Validate data.

        Args:
            data: Data to validate
            config: Configuration options

        Returns:
            Validation result with is_valid, errors, warnings
        """
        ...
