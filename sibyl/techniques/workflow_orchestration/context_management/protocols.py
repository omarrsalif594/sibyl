"""Context management technique protocols and shared types.

This module defines the protocol interfaces and data structures for context management operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ContextItem:
    """Single context item with priority and metadata."""

    id: str
    content: str
    priority: float
    timestamp: float | None = None
    relevance_score: float | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextState:
    """State of context at a point in time."""

    items: list[ContextItem]
    total_tokens: int
    capacity_tokens: int
    utilization: float  # 0.0 to 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextManagementResult:
    """Result from a context management operation."""

    context_state: ContextState
    operation: str
    items_kept: int
    items_removed: int
    tokens_saved: int
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RotationStrategy(Protocol):
    """Protocol for context rotation implementations."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    async def rotate(
        self, context_items: list[ContextItem], max_tokens: int, config: dict[str, Any]
    ) -> ContextState:
        """Rotate context items based on strategy.

        Args:
            context_items: Current context items
            max_tokens: Maximum token budget
            config: Configuration options

        Returns:
            Updated context state
        """
        ...


@runtime_checkable
class SummarizationStrategy(Protocol):
    """Protocol for context summarization implementations."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    async def summarize(
        self, context_items: list[ContextItem], target_tokens: int, config: dict[str, Any]
    ) -> str:
        """Summarize context items.

        Args:
            context_items: Context items to summarize
            target_tokens: Target token count for summary
            config: Configuration options

        Returns:
            Summarized content
        """
        ...


@runtime_checkable
class CompressionStrategy(Protocol):
    """Protocol for context compression implementations."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    async def compress(self, content: str, target_ratio: float, config: dict[str, Any]) -> str:
        """Compress content.

        Args:
            content: Content to compress
            target_ratio: Target compression ratio (0.0 to 1.0)
            config: Configuration options

        Returns:
            Compressed content
        """
        ...


@runtime_checkable
class PrioritizationStrategy(Protocol):
    """Protocol for context prioritization implementations."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    async def prioritize(
        self, context_items: list[ContextItem], query: str | None, config: dict[str, Any]
    ) -> list[ContextItem]:
        """Prioritize context items.

        Args:
            context_items: Context items to prioritize
            query: Optional query for relevance-based prioritization
            config: Configuration options

        Returns:
            Prioritized context items (highest priority first)
        """
        ...
