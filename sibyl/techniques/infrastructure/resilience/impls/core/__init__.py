"""Core resilience implementations."""

from sibyl.techniques.infrastructure.resilience.impls.core.backoff_engine import (
    ExponentialJitterBackoff,
)
from sibyl.techniques.infrastructure.resilience.impls.core.circuit_breaker import (
    ThresholdCircuitBreaker,
)

__all__ = [
    "ExponentialJitterBackoff",
    "ThresholdCircuitBreaker",
]


def get_builtin_implementations() -> Any:
    """Get dictionary of built-in resilience implementations.

    Returns:
        Dict mapping implementation names to classes
    """
    return {
        "backoff": {
            "exponential_jitter": ExponentialJitterBackoff,
        },
        "circuit_breaker": {
            "threshold_based": ThresholdCircuitBreaker,
        },
    }
