"""Score aggregation implementations.

This module provides implementations for aggregating multiple scores
into a single composite score.
"""

import logging

from sibyl.techniques.infrastructure.scoring.protocols import (
    ScoringResult,
)

logger = logging.getLogger(__name__)


class WeightedAverageAggregator:
    """Aggregate multiple scores using weighted average.

    Examples:
        >>> aggregator = WeightedAverageAggregator()
        >>> scores = [
        ...     ScoringResult(score=0.8, confidence=1.0),
        ...     ScoringResult(score=0.6, confidence=0.9)
        ... ]
        >>> result = aggregator.aggregate(scores)
        >>> # Weighted by confidence: (0.8*1.0 + 0.6*0.9) / (1.0 + 0.9)
        >>> assert abs(result.score - 0.716) < 0.01
    """

    @property
    def name(self) -> str:
        """Aggregator name for identification."""
        return "weighted_average"

    def __init__(self, use_confidence_weighting: bool = True) -> None:
        """Initialize weighted average aggregator.

        Args:
            use_confidence_weighting: Weight by confidence scores (default: True)
        """
        self.use_confidence_weighting = use_confidence_weighting

        logger.debug(
            f"Initialized {self.name} aggregator: confidence_weighting={use_confidence_weighting}"
        )

    def aggregate(
        self, scores: list[ScoringResult], weights: dict[str, float] | None = None
    ) -> ScoringResult:
        """Aggregate multiple scoring results using weighted average.

        Args:
            scores: List of scoring results to aggregate
            weights: Optional custom weights (by index as string key)

        Returns:
            Aggregated scoring result

        Examples:
            >>> aggregator = WeightedAverageAggregator()
            >>> scores = [
            ...     ScoringResult(score=0.8, confidence=1.0),
            ...     ScoringResult(score=0.6, confidence=0.9)
            ... ]
            >>> result = aggregator.aggregate(scores)
            >>> assert 0.6 <= result.score <= 0.8
        """
        if not scores:
            logger.warning("No scores to aggregate, returning neutral score")
            return ScoringResult(
                score=0.5,
                confidence=0.0,
                metadata={"aggregator": self.name, "num_scores": 0},
            )

        # Calculate weights
        if weights is None:
            if self.use_confidence_weighting:
                # Weight by confidence scores
                weight_list = [s.confidence for s in scores]
            else:
                # Equal weights
                weight_list = [1.0] * len(scores)
        else:
            # Use custom weights
            weight_list = [weights.get(str(i), 1.0) for i in range(len(scores))]

        # Calculate weighted average
        total_weight = sum(weight_list)
        if total_weight == 0:
            logger.warning("Total weight is 0, using equal weights")
            weight_list = [1.0] * len(scores)
            total_weight = len(scores)

        weighted_sum = sum(s.score * w for s, w in zip(scores, weight_list, strict=False))
        aggregated_score = weighted_sum / total_weight

        # Calculate average confidence (weighted)
        confidence_sum = sum(s.confidence * w for s, w in zip(scores, weight_list, strict=False))
        aggregated_confidence = confidence_sum / total_weight

        # Build breakdown
        breakdown = {
            "individual_scores": [s.score for s in scores],
            "weights": weight_list,
            "total_weight": total_weight,
            "weighted_sum": weighted_sum,
        }

        logger.debug(
            f"Aggregated {len(scores)} scores: "
            f"result={aggregated_score:.2f}, confidence={aggregated_confidence:.2f}"
        )

        return ScoringResult(
            score=aggregated_score,
            confidence=aggregated_confidence,
            metadata={
                "aggregator": self.name,
                "num_scores": len(scores),
                "confidence_weighted": self.use_confidence_weighting,
            },
            breakdown=breakdown,
        )


def create_default_aggregator() -> WeightedAverageAggregator:
    """Factory function to create default score aggregator.

    Returns:
        Configured WeightedAverageAggregator instance
    """
    return WeightedAverageAggregator()
