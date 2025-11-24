"""Reranking technique protocols and shared types.

This module defines the protocol interfaces and data structures for reranking operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class RankedItem:
    """Single ranked item with score and metadata."""

    id: str
    content: str
    score: float
    rank: int
    original_rank: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RerankingResult:
    """Result from a reranking operation."""

    ranked_items: list[RankedItem]
    query: str
    reranking_method: str
    total_items: int
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CrossEncoderReranker(Protocol):
    """Protocol for cross-encoder reranking implementations."""

    @property
    def name(self) -> str:
        """Reranker name for identification."""
        ...

    async def rerank(
        self, query: str, items: list[dict[str, Any]], top_k: int, config: dict[str, Any]
    ) -> list[RankedItem]:
        """Rerank items using cross-encoder scoring.

        Args:
            query: Query string
            items: List of items to rerank
            top_k: Number of top items to return
            config: Configuration options

        Returns:
            List of reranked items
        """
        ...


@runtime_checkable
class LLMReranker(Protocol):
    """Protocol for LLM-based reranking implementations."""

    @property
    def name(self) -> str:
        """Reranker name for identification."""
        ...

    async def rerank(
        self, query: str, items: list[dict[str, Any]], top_k: int, config: dict[str, Any]
    ) -> list[RankedItem]:
        """Rerank items using LLM scoring.

        Args:
            query: Query string
            items: List of items to rerank
            top_k: Number of top items to return
            config: Configuration options

        Returns:
            List of reranked items
        """
        ...


@runtime_checkable
class DiversityReranker(Protocol):
    """Protocol for diversity-based reranking implementations."""

    @property
    def name(self) -> str:
        """Reranker name for identification."""
        ...

    async def rerank(
        self,
        query: str,
        items: list[dict[str, Any]],
        top_k: int,
        diversity_factor: float,
        config: dict[str, Any],
    ) -> list[RankedItem]:
        """Rerank items to maximize diversity.

        Args:
            query: Query string
            items: List of items to rerank
            top_k: Number of top items to return
            diversity_factor: Weight for diversity vs relevance (0-1)
            config: Configuration options

        Returns:
            List of reranked items
        """
        ...


@runtime_checkable
class BM25Reranker(Protocol):
    """Protocol for BM25-based reranking implementations."""

    @property
    def name(self) -> str:
        """Reranker name for identification."""
        ...

    async def rerank(
        self, query: str, items: list[dict[str, Any]], top_k: int, config: dict[str, Any]
    ) -> list[RankedItem]:
        """Rerank items using BM25 scoring.

        Args:
            query: Query string
            items: List of items to rerank
            top_k: Number of top items to return
            config: Configuration options

        Returns:
            List of reranked items
        """
        ...


@runtime_checkable
class FusionReranker(Protocol):
    """Protocol for result fusion/combination reranking implementations."""

    @property
    def name(self) -> str:
        """Reranker name for identification."""
        ...

    async def fuse(
        self,
        query: str,
        result_lists: list[list[dict[str, Any]]],
        top_k: int,
        config: dict[str, Any],
    ) -> list[RankedItem]:
        """Fuse multiple result lists into a single ranked list.

        Args:
            query: Query string
            result_lists: Multiple lists of search results to fuse
            top_k: Number of top items to return
            config: Configuration options

        Returns:
            List of fused and reranked items
        """
        ...
