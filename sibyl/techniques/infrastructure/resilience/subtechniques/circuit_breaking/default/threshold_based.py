"""
Threshold-Based Circuit Breaking

Original logic from infrastructure/router.py:160-162:
    if consecutive_failures >= failure_threshold:
        trip_circuit()
        wait_for_cooldown(cooldown_seconds)

Trips circuit breaker when consecutive failures exceed threshold.
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class ThresholdBasedCircuitBreaker(SubtechniqueImplementation):
    """Determine if circuit breaker should trip based on failure threshold."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Determine if circuit breaker should trip.

        Args:
            context: Must contain:
                - 'consecutive_failures': int, number of consecutive failures
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with should_trip decision

        Example:
            >>> impl = ThresholdBasedCircuitBreaker(config)
            >>> result = impl.execute({'consecutive_failures': 6})
            >>> result.result['should_trip']  # True (>= 5 threshold)
        """
        consecutive_failures = context.get("consecutive_failures", 0)

        # Get parameters from config
        failure_threshold = self.config.get("failure_threshold", 5)
        cooldown_seconds = self.config.get("cooldown_seconds", 30)

        # Determine if circuit should trip
        should_trip = consecutive_failures >= failure_threshold

        return SubtechniqueResult(
            success=True,
            result={
                "should_trip": should_trip,
                "consecutive_failures": consecutive_failures,
                "failure_threshold": failure_threshold,
                "cooldown_seconds": cooldown_seconds,
                "method": "threshold_based",
            },
            metadata={"margin": consecutive_failures - failure_threshold, "tripped": should_trip},
        )
