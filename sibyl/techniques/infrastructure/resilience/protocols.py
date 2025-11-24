"""Resilience technique protocols and shared types.

This module defines the protocol interfaces and data structures for the resilience
technique that implements retry backoff and circuit breaking strategies.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class BackoffResult:
    """Result of a backoff calculation.

    Attributes:
        delay: Calculated delay in seconds
        attempt: Retry attempt number
        metadata: Additional backoff metadata
    """

    delay: float
    attempt: int
    metadata: dict[str, Any] | None = None


@dataclass
class CircuitBreakerResult:
    """Result of circuit breaker evaluation.

    Attributes:
        should_trip: Whether circuit should trip (open)
        consecutive_failures: Number of consecutive failures
        threshold: Failure threshold used
        metadata: Additional circuit breaker metadata
    """

    should_trip: bool
    consecutive_failures: int
    threshold: int
    metadata: dict[str, Any] | None = None


@dataclass
class BackoffInput:
    """Input for backoff calculation.

    Attributes:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Optional maximum delay cap
        metadata: Additional context
    """

    attempt: int
    base_delay: float = 1.0
    max_delay: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class CircuitBreakerInput:
    """Input for circuit breaker evaluation.

    Attributes:
        consecutive_failures: Number of consecutive failures
        threshold: Failure threshold for tripping
        metadata: Additional context
    """

    consecutive_failures: int
    threshold: int = 5
    metadata: dict[str, Any] | None = None


@runtime_checkable
class BackoffStrategy(Protocol):
    """Protocol for backoff strategies."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    def calculate_delay(self, input_data: BackoffInput, context: dict[str, Any]) -> BackoffResult:
        """Calculate backoff delay.

        Args:
            input_data: Backoff input data
            context: Calculation context

        Returns:
            Backoff result with delay

        Examples:
            >>> strategy = ExponentialJitterBackoff()
            >>> input_data = BackoffInput(attempt=2, base_delay=1.0)
            >>> result = strategy.calculate_delay(input_data, {})
            >>> assert result.delay > 0
        """
        ...


@runtime_checkable
class CircuitBreaker(Protocol):
    """Protocol for circuit breaker strategies."""

    @property
    def name(self) -> str:
        """Circuit breaker name for identification."""
        ...

    def should_trip(
        self, input_data: CircuitBreakerInput, context: dict[str, Any]
    ) -> CircuitBreakerResult:
        """Determine if circuit should trip.

        Args:
            input_data: Circuit breaker input data
            context: Evaluation context

        Returns:
            Circuit breaker result with decision

        Examples:
            >>> breaker = ThresholdCircuitBreaker()
            >>> input_data = CircuitBreakerInput(consecutive_failures=3, threshold=5)
            >>> result = breaker.should_trip(input_data, {})
            >>> assert not result.should_trip  # Below threshold
        """
        ...


@runtime_checkable
class ResilienceMonitor(Protocol):
    """Protocol for monitoring resilience operations."""

    @property
    def name(self) -> str:
        """Monitor name for identification."""
        ...

    def record_retry(self, attempt: int, delay: float, success: bool) -> None:
        """Record a retry attempt.

        Args:
            attempt: Retry attempt number
            delay: Delay before retry
            success: Whether retry was successful
        """
        ...

    def record_circuit_trip(self, consecutive_failures: int, threshold: int) -> None:
        """Record a circuit breaker trip.

        Args:
            consecutive_failures: Number of failures that triggered trip
            threshold: Threshold that was exceeded
        """
        ...

    def get_metrics(self) -> dict[str, Any]:
        """Get resilience metrics.

        Returns:
            Dictionary of resilience metrics
        """
        ...
