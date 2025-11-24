"""Metrics collection for scoring operations.

This module provides metrics tracking for scoring calculations,
including success rates, score distributions, and performance metrics.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sibyl.techniques.infrastructure.scoring.protocols import ScoringResult

logger = logging.getLogger(__name__)


@dataclass
class ScoringMetrics:
    """Metrics for scoring operations.

    Attributes:
        total_calculations: Total number of scoring calculations
        calculations_by_type: Count by scoring type (confidence, quality, relevance)
        score_distribution: Distribution of scores by range
        average_score: Average score across all calculations
        average_confidence: Average confidence across all calculations
        total_time_seconds: Total time spent on calculations
        errors: Number of calculation errors
    """

    total_calculations: int = 0
    calculations_by_type: dict[str, int] = field(default_factory=dict)
    score_distribution: dict[str, int] = field(default_factory=dict)
    average_score: float = 0.0
    average_confidence: float = 0.0
    total_time_seconds: float = 0.0
    errors: int = 0
    _score_sum: float = field(default=0.0, repr=False)
    _confidence_sum: float = field(default=0.0, repr=False)

    def record_calculation(
        self, result: ScoringResult, calculation_type: str, duration_seconds: float
    ) -> None:
        """Record a scoring calculation.

        Args:
            result: Scoring result
            calculation_type: Type of calculation (confidence, quality, relevance)
            duration_seconds: Time taken for calculation
        """
        self.total_calculations += 1
        self.calculations_by_type[calculation_type] = (
            self.calculations_by_type.get(calculation_type, 0) + 1
        )

        # Update score statistics
        self._score_sum += result.score
        self._confidence_sum += result.confidence
        self.average_score = self._score_sum / self.total_calculations
        self.average_confidence = self._confidence_sum / self.total_calculations

        # Update score distribution
        score_range = self._get_score_range(result.score)
        self.score_distribution[score_range] = self.score_distribution.get(score_range, 0) + 1

        # Update timing
        self.total_time_seconds += duration_seconds

        logger.debug(
            f"Recorded {calculation_type} calculation: "
            f"score={result.score:.2f}, time={duration_seconds:.3f}s"
        )

    def record_error(self, calculation_type: str, error: Exception) -> None:
        """Record a calculation error.

        Args:
            calculation_type: Type of calculation that failed
            error: Exception that occurred
        """
        self.errors += 1
        logger.exception("Scoring error in %s: %s", calculation_type, error)

    def _get_score_range(self, score: float) -> str:
        """Get score range bucket for distribution.

        Args:
            score: Score value

        Returns:
            Range string (e.g., "0.0-0.2")
        """
        if score < 0:
            return "negative"
        if score < 0.2:
            return "0.0-0.2"
        if score < 0.4:
            return "0.2-0.4"
        if score < 0.6:
            return "0.4-0.6"
        if score < 0.8:
            return "0.6-0.8"
        return "0.8-1.0"

    def to_dict(self) -> dict:
        """Convert metrics to dictionary.

        Returns:
            Dictionary representation of metrics
        """
        return {
            "total_calculations": self.total_calculations,
            "calculations_by_type": self.calculations_by_type,
            "score_distribution": self.score_distribution,
            "average_score": self.average_score,
            "average_confidence": self.average_confidence,
            "total_time_seconds": self.total_time_seconds,
            "errors": self.errors,
        }


# Global metrics instance
_global_metrics = ScoringMetrics()


def get_metrics() -> ScoringMetrics:
    """Get global scoring metrics.

    Returns:
        Global ScoringMetrics instance
    """
    return _global_metrics


def reset_metrics() -> None:
    """Reset global scoring metrics."""
    global _global_metrics
    _global_metrics = ScoringMetrics()
    logger.info("Scoring metrics reset")


@contextmanager
def track_calculation(calculation_type: str) -> Any:
    """Context manager to track scoring calculation time.

    Args:
        calculation_type: Type of calculation (confidence, quality, relevance)

    Yields:
        None

    Examples:
        >>> with track_calculation('confidence'):
        ...     result = calculator.calculate(input_data, context)
        ...     # Automatically tracked in metrics
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.debug("%s calculation took %ss", calculation_type, duration)


def record_calculation(
    result: ScoringResult, calculation_type: str, duration_seconds: float
) -> None:
    """Record a scoring calculation in global metrics.

    Args:
        result: Scoring result
        calculation_type: Type of calculation
        duration_seconds: Time taken for calculation
    """
    _global_metrics.record_calculation(result, calculation_type, duration_seconds)


def record_error(calculation_type: str, error: Exception) -> None:
    """Record a calculation error in global metrics.

    Args:
        calculation_type: Type of calculation that failed
        error: Exception that occurred
    """
    _global_metrics.record_error(calculation_type, error)
