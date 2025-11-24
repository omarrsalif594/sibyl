"""Relevance scoring implementations.

This module provides implementations for calculating relevance scores
based on similarity metrics (e.g., from search results).
"""

import logging
from typing import Any

from sibyl.techniques.infrastructure.scoring.protocols import (
    RelevanceInput,
    ScoringResult,
)

logger = logging.getLogger(__name__)


class ThresholdBasedScorer:
    """Calculate relevance score using threshold-based approach.

    This implementation is based on the original logic from agents/search.py:249-252:
    - High relevance (>= 0.8): score = 0.8
    - Medium relevance (>= 0.6): score = 0.6
    - Low relevance (< 0.6): score = 0.4

    Examples:
        >>> scorer = ThresholdBasedScorer()
        >>> input_data = RelevanceInput(similarity=0.85)
        >>> result = scorer.score(input_data, {})
        >>> assert result.score == 0.8  # High relevance
    """

    @property
    def name(self) -> str:
        """Scorer name for identification."""
        return "threshold_based"

    def __init__(
        self,
        high_threshold: float = 0.8,
        medium_threshold: float = 0.6,
        high_score: float = 0.8,
        medium_score: float = 0.6,
        low_score: float = 0.4,
    ) -> None:
        """Initialize threshold-based scorer.

        Args:
            high_threshold: Threshold for high relevance (default: 0.8)
            medium_threshold: Threshold for medium relevance (default: 0.6)
            high_score: Score for high relevance (default: 0.8)
            medium_score: Score for medium relevance (default: 0.6)
            low_score: Score for low relevance (default: 0.4)
        """
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.high_score = high_score
        self.medium_score = medium_score
        self.low_score = low_score

        logger.debug(
            f"Initialized {self.name} scorer: "
            f"thresholds=[{medium_threshold}, {high_threshold}], "
            f"scores=[{low_score}, {medium_score}, {high_score}]"
        )

    def score(self, input_data: RelevanceInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate relevance score using threshold-based approach.

        Args:
            input_data: Relevance input data with similarity score
            context: Scoring context (unused in this implementation)

        Returns:
            ScoringResult with relevance score (0.0 to 1.0)

        Examples:
            >>> scorer = ThresholdBasedScorer()
            >>> # High relevance
            >>> result = scorer.score(RelevanceInput(similarity=0.85), {})
            >>> assert result.score == 0.8
            >>> # Medium relevance
            >>> result = scorer.score(RelevanceInput(similarity=0.7), {})
            >>> assert result.score == 0.6
            >>> # Low relevance
            >>> result = scorer.score(RelevanceInput(similarity=0.5), {})
            >>> assert result.score == 0.4
        """
        similarity = input_data.similarity

        # Determine relevance level and score
        if similarity >= self.high_threshold:
            score = self.high_score
            level = "high"
        elif similarity >= self.medium_threshold:
            score = self.medium_score
            level = "medium"
        else:
            score = self.low_score
            level = "low"

        # Calculate score breakdown
        breakdown = {
            "similarity": similarity,
            "relevance_level": level,
            "threshold_used": self.high_threshold
            if level == "high"
            else (self.medium_threshold if level == "medium" else 0.0),
        }

        logger.debug(
            f"Relevance calculated: score={score:.2f}, similarity={similarity:.2f}, level={level}"
        )

        return ScoringResult(
            score=score,
            confidence=1.0,  # We're confident in our calculation
            metadata={
                "scorer": self.name,
                "similarity": similarity,
                "relevance_level": level,
            },
            breakdown=breakdown,
        )


def create_default_relevance_scorer() -> ThresholdBasedScorer:
    """Factory function to create default relevance scorer.

    Returns:
        Configured ThresholdBasedScorer instance
    """
    return ThresholdBasedScorer()
