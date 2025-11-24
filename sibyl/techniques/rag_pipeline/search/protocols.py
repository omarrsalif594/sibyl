"""Search technique protocols and shared types.

This module defines the protocol interfaces and data structures for search operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SearchResult:
    """Single search result."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    rank: int | None = None


@dataclass
class SearchResponse:
    """Response from a search operation."""

    results: list[SearchResult]
    query: str
    total_results: int
    search_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorSearcher(Protocol):
    """Protocol for vector search implementations."""

    @property
    def name(self) -> str:
        """Searcher name for identification."""
        ...

    async def search(
        self, query_vector: list[float], top_k: int, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Perform vector similarity search.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        ...


@runtime_checkable
class KeywordSearcher(Protocol):
    """Protocol for keyword search implementations."""

    @property
    def name(self) -> str:
        """Searcher name for identification."""
        ...

    async def search(
        self, query: str, top_k: int, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Perform keyword search.

        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        ...


@runtime_checkable
class HybridSearcher(Protocol):
    """Protocol for hybrid search implementations."""

    @property
    def name(self) -> str:
        """Searcher name for identification."""
        ...

    async def search(
        self,
        query: str,
        query_vector: list[float] | None,
        top_k: int,
        vector_results: list[SearchResult] | None = None,
        keyword_results: list[SearchResult] | None = None,
        alpha: float = 0.5,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector and keyword results.

        Args:
            query: Search query string
            query_vector: Optional query embedding vector
            top_k: Number of results to return
            vector_results: Optional pre-computed vector search results
            keyword_results: Optional pre-computed keyword search results
            alpha: Weight for vector vs keyword (0.0 = all keyword, 1.0 = all vector)

        Returns:
            List of search results
        """
        ...
