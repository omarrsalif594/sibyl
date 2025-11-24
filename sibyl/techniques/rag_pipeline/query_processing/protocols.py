"""Query processing technique protocols and shared types.

This module defines the protocol interfaces and data structures for query processing operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ProcessedQuery:
    """Single processed query variant."""

    query: str
    method: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    original_query: str | None = None


@dataclass
class QueryProcessingResult:
    """Result from a query processing operation."""

    processed_queries: list[ProcessedQuery]
    original_query: str
    processing_method: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class QueryExpander(Protocol):
    """Protocol for query expansion implementations."""

    @property
    def name(self) -> str:
        """Expander name for identification."""
        ...

    async def expand(self, query: str, config: dict[str, Any]) -> list[str]:
        """Expand query into multiple variations.

        Args:
            query: Original query string
            config: Configuration options

        Returns:
            List of expanded query strings
        """
        ...


@runtime_checkable
class QueryRewriter(Protocol):
    """Protocol for query rewriting implementations."""

    @property
    def name(self) -> str:
        """Rewriter name for identification."""
        ...

    async def rewrite(
        self, query: str, context: dict[str, Any] | None, config: dict[str, Any]
    ) -> str:
        """Rewrite query based on context.

        Args:
            query: Original query string
            context: Optional context information
            config: Configuration options

        Returns:
            Rewritten query string
        """
        ...


@runtime_checkable
class MultiQueryGenerator(Protocol):
    """Protocol for multi-query generation implementations."""

    @property
    def name(self) -> str:
        """Generator name for identification."""
        ...

    async def generate(self, query: str, num_queries: int, config: dict[str, Any]) -> list[str]:
        """Generate multiple query variations.

        Args:
            query: Original query string
            num_queries: Number of variations to generate
            config: Configuration options

        Returns:
            List of query variations
        """
        ...


@runtime_checkable
class HyDEGenerator(Protocol):
    """Protocol for Hypothetical Document Embeddings (HyDE) implementations."""

    @property
    def name(self) -> str:
        """Generator name for identification."""
        ...

    async def generate_hypothetical_doc(self, query: str, config: dict[str, Any]) -> str:
        """Generate hypothetical document from query.

        Args:
            query: Original query string
            config: Configuration options

        Returns:
            Generated hypothetical document
        """
        ...


@runtime_checkable
class QueryDecomposer(Protocol):
    """Protocol for query decomposition implementations."""

    @property
    def name(self) -> str:
        """Decomposer name for identification."""
        ...

    async def decompose(self, query: str, config: dict[str, Any]) -> list[str]:
        """Decompose complex query into sub-queries.

        Args:
            query: Original complex query
            config: Configuration options

        Returns:
            List of sub-queries
        """
        ...
