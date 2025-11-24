"""
Protocol definitions for compression subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CompressionProtocol(Protocol):
    """Base protocol for compression implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the compression operation.

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
class PickleCompressionProtocol(CompressionProtocol):
    """Pickle Compression protocol."""
