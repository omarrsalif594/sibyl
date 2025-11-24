"""Validation technique protocols and shared types.

This module defines the protocol interfaces and data structures for the validation
technique that validates outputs before returning them to clients.
"""

from typing import Any, Protocol, runtime_checkable

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    Validator,
)


@runtime_checkable
class ValidatorComposer(Protocol):
    """Protocol for validator composition strategies."""

    @property
    def name(self) -> str:
        """Composer name for identification."""
        ...

    async def compose(
        self, validators: list[Validator], output: Any, context: dict[str, Any]
    ) -> ValidationVerdict:
        """Compose multiple validators into a single verdict.

        Args:
            validators: List of validators to compose
            output: Output to validate
            context: Validation context

        Returns:
            Composed validation verdict
        """
        ...


@runtime_checkable
class RetryStrategy(Protocol):
    """Protocol for retry strategies."""

    @property
    def name(self) -> str:
        """Strategy name for identification."""
        ...

    async def should_retry(
        self, verdict: ValidationVerdict, attempt: int, max_attempts: int
    ) -> bool:
        """Determine if operation should be retried.

        Args:
            verdict: Current validation verdict
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum allowed attempts

        Returns:
            True if should retry, False otherwise
        """
        ...

    async def get_backoff_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        ...


@runtime_checkable
class QualityScorer(Protocol):
    """Protocol for quality scoring strategies."""

    @property
    def name(self) -> str:
        """Scorer name for identification."""
        ...

    async def score(
        self, output: Any, context: dict[str, Any], verdict: ValidationVerdict | None = None
    ) -> float:
        """Calculate quality score for output.

        Args:
            output: Output to score
            context: Scoring context
            verdict: Optional validation verdict to incorporate

        Returns:
            Quality score (0.0 to 1.0, where 1.0 is perfect)
        """
        ...
