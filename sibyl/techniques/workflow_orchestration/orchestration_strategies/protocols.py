"""Orchestration strategies protocols and shared types."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class MergeResult:
    """Result of a context merge operation."""

    merged_context: dict[str, Any]
    sources: list[str]
    metadata: dict[str, Any] | None = None


@dataclass
class AggregationResult:
    """Result of consensus aggregation."""

    aggregated_value: Any
    sources: list[Any]
    confidence: float
    metadata: dict[str, Any] | None = None


@runtime_checkable
class ContextMerger(Protocol):
    """Protocol for context merging strategies."""

    @property
    def name(self) -> str:
        """Merger name."""
        ...

    def merge(self, contexts: list[dict[str, Any]], context: dict[str, Any]) -> MergeResult:
        """Merge multiple contexts.

        Args:
            contexts: Contexts to merge
            context: Merge context

        Returns:
            Merge result
        """
        ...


@runtime_checkable
class ConsensusAggregator(Protocol):
    """Protocol for consensus aggregation strategies."""

    @property
    def name(self) -> str:
        """Aggregator name."""
        ...

    def aggregate(self, values: list[Any], context: dict[str, Any]) -> AggregationResult:
        """Aggregate values to consensus.

        Args:
            values: Values to aggregate
            context: Aggregation context

        Returns:
            Aggregation result
        """
        ...
