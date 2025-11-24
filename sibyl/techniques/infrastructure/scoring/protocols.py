"""Scoring technique protocols and shared types.

This module defines the protocol interfaces and data structures for the scoring
technique that calculates confidence, quality, and relevance scores for agents.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ScoringResult:
    """Result of a scoring operation.

    Attributes:
        score: The calculated score value
        confidence: Confidence in the score (0.0 to 1.0)
        metadata: Additional scoring metadata
        breakdown: Optional detailed breakdown of score components
    """

    score: float
    confidence: float = 1.0
    metadata: dict[str, Any] | None = None
    breakdown: dict[str, float] | None = None


@dataclass
class ConfidenceInput:
    """Input for confidence calculation.

    Attributes:
        tools: List of tools in the plan
        metadata: Additional context for confidence calculation
    """

    tools: list[str]
    metadata: dict[str, Any] | None = None


@dataclass
class QualityInput:
    """Input for quality scoring.

    Attributes:
        failures: Number of failures
        issues: List of issues with severity levels
        metadata: Additional context for quality scoring
    """

    failures: int = 0
    issues: list[dict[str, Any]] = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []


@dataclass
class RelevanceInput:
    """Input for relevance scoring.

    Attributes:
        similarity: Similarity score (0.0 to 1.0)
        metadata: Additional context for relevance scoring
    """

    similarity: float
    metadata: dict[str, Any] | None = None


@runtime_checkable
class ConfidenceCalculator(Protocol):
    """Protocol for confidence calculation strategies."""

    @property
    def name(self) -> str:
        """Calculator name for identification."""
        ...

    def calculate(self, input_data: ConfidenceInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate confidence score.

        Args:
            input_data: Confidence input data
            context: Calculation context

        Returns:
            Scoring result with confidence score

        Examples:
            >>> calculator = WeightedSumCalculator()
            >>> input_data = ConfidenceInput(tools=['tool1', 'tool2'])
            >>> result = calculator.calculate(input_data, {})
            >>> assert 0.0 <= result.score <= 1.0
        """
        ...


@runtime_checkable
class QualityScorer(Protocol):
    """Protocol for quality scoring strategies."""

    @property
    def name(self) -> str:
        """Scorer name for identification."""
        ...

    def score(self, input_data: QualityInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate quality score.

        Args:
            input_data: Quality input data
            context: Scoring context

        Returns:
            Scoring result with quality score (negative indicates problems)

        Examples:
            >>> scorer = PenaltyBasedScorer()
            >>> input_data = QualityInput(failures=1, issues=[{'severity': 'high'}])
            >>> result = scorer.score(input_data, {})
            >>> assert result.score < 0  # Penalty for failures
        """
        ...


@runtime_checkable
class RelevanceScorer(Protocol):
    """Protocol for relevance scoring strategies."""

    @property
    def name(self) -> str:
        """Scorer name for identification."""
        ...

    def score(self, input_data: RelevanceInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate relevance score.

        Args:
            input_data: Relevance input data
            context: Scoring context

        Returns:
            Scoring result with relevance score

        Examples:
            >>> scorer = ThresholdBasedScorer()
            >>> input_data = RelevanceInput(similarity=0.85)
            >>> result = scorer.score(input_data, {})
            >>> assert 0.0 <= result.score <= 1.0
        """
        ...


@runtime_checkable
class ScoringAggregator(Protocol):
    """Protocol for aggregating multiple scores."""

    @property
    def name(self) -> str:
        """Aggregator name for identification."""
        ...

    def aggregate(
        self, scores: list[ScoringResult], weights: dict[str, float] | None = None
    ) -> ScoringResult:
        """Aggregate multiple scoring results.

        Args:
            scores: List of scoring results to aggregate
            weights: Optional weights for each score

        Returns:
            Aggregated scoring result

        Examples:
            >>> aggregator = WeightedAverageAggregator()
            >>> scores = [
            ...     ScoringResult(score=0.8, confidence=1.0),
            ...     ScoringResult(score=0.6, confidence=0.9)
            ... ]
            >>> result = aggregator.aggregate(scores)
            >>> assert 0.0 <= result.score <= 1.0
        """
        ...
