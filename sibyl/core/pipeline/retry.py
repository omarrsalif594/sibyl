"""Retry logic for pipeline steps with exponential backoff.

This module provides retry functionality for pipeline steps, supporting:
- Exponential, linear, and constant backoff strategies
- Error filtering (retry specific errors, skip others)
- Configurable max attempts and delays
- Retry context tracking

Example:
    config = RetryConfig(
        max_attempts=3,
        backoff=BackoffStrategy.EXPONENTIAL,
        initial_delay=1.0,
        on_errors=["NetworkError", "TimeoutError"]
    )

    retry_helper = RetryHelper(config)
    result = await retry_helper.execute_with_retry(async_func, "step_name")
"""

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BackoffStrategy(str, Enum):
    """Backoff strategy for retry policies."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class RetryConfig:
    """Configuration for retry policies.

    Attributes:
        max_attempts: Maximum number of retry attempts (1-10)
        backoff: Backoff strategy (exponential, linear, constant)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        on_errors: List of error patterns to retry on (None = retry all)
        skip_errors: List of error patterns to skip retry (takes precedence)
    """

    max_attempts: int = 3
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    on_errors: list[str] | None = None
    skip_errors: list[str] | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (1 <= self.max_attempts <= 10):
            msg = "max_attempts must be between 1 and 10"
            raise ValueError(msg)
        if self.initial_delay <= 0:
            msg = "initial_delay must be positive"
            raise ValueError(msg)
        if self.max_delay <= 0:
            msg = "max_delay must be positive"
            raise ValueError(msg)
        if self.backoff_factor <= 1 and self.backoff == BackoffStrategy.EXPONENTIAL:
            msg = "backoff_factor must be > 1 for exponential backoff"
            raise ValueError(msg)


@dataclass
class RetryContext:
    """Context for retry execution.

    Attributes:
        attempt: Current attempt number (1-indexed)
        max_attempts: Maximum attempts allowed
        last_error: Last error encountered
        total_delay: Total delay accumulated across retries
    """

    attempt: int = 0
    max_attempts: int = 3
    last_error: Exception | None = None
    total_delay: float = 0.0


class RetryHelper:
    """Helper for executing steps with retry logic."""

    def __init__(self, config: RetryConfig) -> None:
        """Initialize retry helper.

        Args:
            config: Retry configuration
        """
        self.config = config

    async def execute_with_retry(
        self,
        func: Callable[[], Any],
        step_name: str,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            step_name: Name of step (for logging)

        Returns:
            Result from successful execution

        Raises:
            Exception: If all retries exhausted
        """
        ctx = RetryContext(max_attempts=self.config.max_attempts)

        while ctx.attempt < ctx.max_attempts:
            ctx.attempt += 1

            try:
                if ctx.attempt > 1:
                    logger.info(
                        "Executing %s (attempt %s/%s)", step_name, ctx.attempt, ctx.max_attempts
                    )
                else:
                    logger.debug("Executing %s (attempt 1/%s)", step_name, ctx.max_attempts)

                result = await func()

                if ctx.attempt > 1:
                    logger.info(
                        f"{step_name} succeeded on attempt {ctx.attempt} "
                        f"(total delay: {ctx.total_delay:.1f}s)"
                    )

                return result

            except Exception as e:
                ctx.last_error = e

                # Check if we should retry this error
                if not self._should_retry(e):
                    logger.info("%s error not retryable: %s", step_name, e)
                    raise

                # Check if more attempts available
                if ctx.attempt >= ctx.max_attempts:
                    logger.exception("%s failed after %s attempts: %s", step_name, ctx.attempt, e)
                    raise

                # Calculate delay
                delay = self._calculate_delay(ctx.attempt)
                ctx.total_delay += delay

                logger.warning(
                    f"{step_name} attempt {ctx.attempt} failed: {e}. Retrying in {delay:.1f}s..."
                )

                # Wait before retry
                await asyncio.sleep(delay)

        # Should never reach here
        msg = "Retry logic error"
        raise RuntimeError(msg)

    def _should_retry(self, error: Exception) -> bool:
        """Check if error should trigger retry.

        Args:
            error: Exception that occurred

        Returns:
            True if should retry
        """
        error_str = str(error)
        error_type = type(error).__name__
        error_full = f"{error_type}: {error_str}"

        # Check skip_errors (takes precedence)
        if self.config.skip_errors:
            for pattern in self.config.skip_errors:
                if re.search(pattern, error_full, re.IGNORECASE):
                    logger.debug("Error matches skip pattern: %s", pattern)
                    return False

        # Check on_errors (if specified)
        if self.config.on_errors:
            for pattern in self.config.on_errors:
                if re.search(pattern, error_full, re.IGNORECASE):
                    logger.debug("Error matches retry pattern: %s", pattern)
                    return True
            # No match = don't retry
            return False

        # No filters = retry all
        return True

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        if self.config.backoff == BackoffStrategy.EXPONENTIAL:
            # Exponential: delay = initial * (factor ^ (attempt - 1))
            delay = self.config.initial_delay * (self.config.backoff_factor ** (attempt - 1))

        elif self.config.backoff == BackoffStrategy.LINEAR:
            # Linear: delay = initial * attempt
            delay = self.config.initial_delay * attempt

        elif self.config.backoff == BackoffStrategy.CONSTANT:
            # Constant: delay = initial
            delay = self.config.initial_delay

        else:
            msg = f"Unknown backoff strategy: {self.config.backoff}"
            raise ValueError(msg)

        # Cap at max_delay
        return min(delay, self.config.max_delay)
