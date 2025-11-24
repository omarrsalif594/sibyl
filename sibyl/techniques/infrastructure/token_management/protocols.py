"""
Protocol definitions for token_management subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TokenManagementProtocol(Protocol):
    """Base protocol for token_management implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the token_management operation.

        Args:
            input_data: Input data to process
            config: Configuration parameters

        Returns:
            Processed result
        """
        ...

    @property
    def name(self) -> str:
        """Get implementation name."""
        ...

    @property
    def description(self) -> str:
        """Get implementation description."""
        ...


@runtime_checkable
class CountingProtocol(TokenManagementProtocol):
    """Counting protocol."""
