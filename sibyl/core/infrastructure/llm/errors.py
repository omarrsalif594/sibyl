from __future__ import annotations

"""LLM provider error types."""


class ProviderError(Exception):
    """Base exception for all provider errors."""


class RateLimitError(ProviderError):
    """Rate limit hit (429 Too Many Requests)."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after  # Seconds to wait before retry


class TransientProviderError(ProviderError):
    """Transient provider error (5xx, network issues)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CapabilityError(ProviderError):
    """Provider doesn't support requested capability."""


class CircuitOpenError(ProviderError):
    """Circuit breaker is open, request rejected."""

    def __init__(self, message: str, open_until: float) -> None:
        super().__init__(message)
        self.open_until = open_until  # Timestamp when circuit closes


class BudgetExceededError(ProviderError):
    """Token or cost budget exceeded."""
