"""Retrieval technique protocols and shared types.

This module defines the protocol interfaces and data structures for retrieval operations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Retriever(Protocol):
    """Protocol for retrieval implementations."""

    @property
    def name(self) -> str:
        """Implementation name for identification."""
        ...

    def retrieve(self, query: str, config: dict[str, Any]) -> list[Any]:
        """Retrieve relevant items for query.

        Args:
            query: Query string
            config: Configuration options

        Returns:
            List of retrieved items
        """
        ...
