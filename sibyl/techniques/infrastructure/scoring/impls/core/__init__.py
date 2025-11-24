"""Core scoring implementations."""

from sibyl.techniques.infrastructure.scoring.impls.core.aggregator import (
    WeightedAverageAggregator,
)
from sibyl.techniques.infrastructure.scoring.impls.core.confidence_engine import (
    WeightedSumCalculator,
)
from sibyl.techniques.infrastructure.scoring.impls.core.quality_engine import (
    PenaltyBasedScorer,
)
from sibyl.techniques.infrastructure.scoring.impls.core.relevance_engine import (
    ThresholdBasedScorer,
)

__all__ = [
    "PenaltyBasedScorer",
    "ThresholdBasedScorer",
    "WeightedAverageAggregator",
    "WeightedSumCalculator",
]


def get_builtin_implementations() -> Any:
    """Get dictionary of built-in scoring implementations.

    Returns:
        Dict mapping implementation names to classes

    Examples:
        >>> impls = get_builtin_implementations()
        >>> calculator = impls['confidence']['weighted_sum']()
        >>> assert calculator.name == 'weighted_sum'
    """
    return {
        "confidence": {
            "weighted_sum": WeightedSumCalculator,
        },
        "quality": {
            "penalty_based": PenaltyBasedScorer,
        },
        "relevance": {
            "threshold_based": ThresholdBasedScorer,
        },
        "aggregation": {
            "weighted_average": WeightedAverageAggregator,
        },
    }
