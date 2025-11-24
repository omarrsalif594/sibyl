"""Circuit breaker implementations."""

import logging
from typing import Any

from sibyl.techniques.infrastructure.resilience.protocols import (
    CircuitBreakerInput,
    CircuitBreakerResult,
)

logger = logging.getLogger(__name__)


class ThresholdCircuitBreaker:
    """Threshold-based circuit breaker.

    Based on infrastructure/router.py:160-162 logic:
    - Trip when consecutive_failures >= threshold
    """

    @property
    def name(self) -> str:
        return "threshold_based"

    def __init__(self, default_threshold: int = 5) -> None:
        """Initialize threshold circuit breaker.

        Args:
            default_threshold: Default failure threshold (default: 5)
        """
        self.default_threshold = default_threshold

    def should_trip(
        self, input_data: CircuitBreakerInput, context: dict[str, Any]
    ) -> CircuitBreakerResult:
        """Determine if circuit should trip.

        Args:
            input_data: Circuit breaker input
            context: Context

        Returns:
            Circuit breaker result
        """
        threshold = input_data.threshold or self.default_threshold
        should_trip = input_data.consecutive_failures >= threshold

        if should_trip:
            logger.warning(
                "Circuit breaker tripped: %s >= %s", input_data.consecutive_failures, threshold
            )
        else:
            logger.debug("Circuit breaker OK: %s < %s", input_data.consecutive_failures, threshold)

        return CircuitBreakerResult(
            should_trip=should_trip,
            consecutive_failures=input_data.consecutive_failures,
            threshold=threshold,
            metadata={
                "strategy": self.name,
                "default_threshold": self.default_threshold,
            },
        )
