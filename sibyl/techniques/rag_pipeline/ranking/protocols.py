"""Ranking technique protocols and shared types.

This module defines the protocol interfaces and data structures for ranking operations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Ranker(Protocol):
    """Protocol for ranking implementations."""

    @property
    def name(self) -> str:
        """Implementation name for identification."""
        ...

    def rank(self, items: list[Any], query: str, config: dict[str, Any]) -> list[Any]:
        """Rank items based on relevance to query.

        Args:
            items: Items to rank
            query: Query string
            config: Configuration options

        Returns:
            Ranked list of items
        """
        ...
