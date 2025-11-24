"""
Resilience Technique

Infrastructure resilience algorithms for retry backoff and circuit breaking.

Extracted from hardcoded logic in:
- infrastructure/router.py:270,280 (exponential backoff with jitter)
- infrastructure/router.py:160-162 (circuit breaker threshold)
"""

from typing import Any

from sibyl.techniques.protocols import BaseTechnique, SubtechniqueResult


class ResilienceTechnique(BaseTechnique):
    """Infrastructure resilience algorithms."""

    def execute(
        self, subtechnique: str, implementation: str, context: dict[str, Any], **kwargs
    ) -> SubtechniqueResult:
        """
        Execute a resilience subtechnique.

        Args:
            subtechnique: One of ['backoff_strategy', 'circuit_breaking']
            implementation: Implementation name
            context: Input data for algorithm
            **kwargs: Additional arguments

        Returns:
            SubtechniqueResult with calculated values
        """
        impl = self.get_subtechnique(subtechnique, implementation)
        return impl.execute(context, **kwargs)

    def calculate_backoff(
        self, attempt: int, base_delay: float = 1.0, implementation: str | None = None, **kwargs
    ) -> float:
        """
        Calculate backoff delay for retry.

        Args:
            attempt: Retry attempt number (0-indexed)
            base_delay: Base delay in seconds
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            Delay in seconds
        """
        impl = implementation or "exponential_jitter"
        result = self.execute(
            "backoff_strategy", impl, {"attempt": attempt, "base_delay": base_delay}, **kwargs
        )
        return result.result.get("delay", base_delay)

    def should_trip_circuit(
        self, consecutive_failures: int, implementation: str | None = None, **kwargs
    ) -> bool:
        """
        Determine if circuit breaker should trip.

        Args:
            consecutive_failures: Number of consecutive failures
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            True if circuit should trip
        """
        impl = implementation or "threshold_based"
        result = self.execute(
            "circuit_breaking", impl, {"consecutive_failures": consecutive_failures}, **kwargs
        )
        return result.result.get("should_trip", False)
