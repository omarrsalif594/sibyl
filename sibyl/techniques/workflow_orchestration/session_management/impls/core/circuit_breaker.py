"""Circuit breaker for graceful degradation and fault tolerance.

This module provides circuit breaker pattern implementation for:
- **LLM summarization**: Fallback to delta compression on failures
- **Database operations**: Graceful degradation on write failures
- **Session rotation**: Continue with current session on rotation failures

Circuit breaker states:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests blocked (fallback used)
- **HALF_OPEN**: Testing recovery, single request allowed

Key features:
- **Failure threshold**: Opens after N consecutive failures
- **Timeout**: Transitions to HALF_OPEN after recovery timeout
- **Automatic recovery**: Closes on successful HALF_OPEN request
- **Metrics integration**: Tracks open/close events

Typical usage:
    breaker = CircuitBreaker(
        name="llm_summarization",
        failure_threshold=3,
        recovery_timeout=30.0,
    )

    try:
        result = await breaker.call(expensive_llm_operation, arg1, arg2)
    except CircuitBreakerOpen:
        # Use fallback
        result = await cheap_fallback_operation(arg1, arg2)
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Import SessionManagementTechnique for configuration
from sibyl.techniques.workflow_orchestration.session_management import SessionManagementTechnique

logger = logging.getLogger(__name__)

# Load default configuration from technique (module-level singleton)
_technique = SessionManagementTechnique()
_technique_config = _technique.load_config(_technique._config_path)
_circuit_breaker_config = (
    _technique_config.get("rotation_based", {})
    .get("rotation_manager", {})
    .get("circuit_breaker", {})
)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is OPEN."""

    def __init__(self, breaker_name: str, message: str) -> None:
        self.breaker_name = breaker_name
        super().__init__(message)


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics.

    Attributes:
        name: Breaker name
        state: Current state
        failure_count: Consecutive failures in CLOSED state
        success_count: Successful calls in current state
        total_calls: Total calls (lifetime)
        total_failures: Total failures (lifetime)
        total_opens: Total times breaker opened
        last_failure_time: Timestamp of last failure
        last_open_time: Timestamp when breaker last opened
        last_close_time: Timestamp when breaker last closed
    """

    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    total_calls: int
    total_failures: int
    total_opens: int
    last_failure_time: float | None
    last_open_time: float | None
    last_close_time: float | None


class CircuitBreaker:
    """Circuit breaker for graceful degradation.

    This implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation
    - OPEN: Failures detected, requests blocked
    - HALF_OPEN: Testing recovery

    The breaker:
    - Opens after failure_threshold consecutive failures
    - Transitions to HALF_OPEN after recovery_timeout
    - Closes after successful HALF_OPEN request
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
        success_threshold: int = 1,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Breaker name (for logging/metrics)
            failure_threshold: Number of consecutive failures before opening (default from technique: 3)
            recovery_timeout: Seconds to wait before attempting recovery (default from technique: 30.0)
            success_threshold: Number of successes needed in HALF_OPEN to close (default: 1)
        """
        self.name = name

        # Use technique configuration as defaults, allow explicit overrides
        # Configuration source: sibyl/techniques/session_management/config.yaml
        self.failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else _circuit_breaker_config.get("failure_threshold", 3)
        )
        self.recovery_timeout = (
            recovery_timeout
            if recovery_timeout is not None
            else _circuit_breaker_config.get("recovery_timeout_seconds", 30.0)
        )
        self.success_threshold = (
            success_threshold
            if success_threshold is not None
            else _circuit_breaker_config.get("half_open_max_calls", 1)
        )

        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_open_time: float | None = None
        self._last_close_time: float | None = None

        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_opens = 0

        # Concurrency control
        self._lock = asyncio.Lock()

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker.

        Args:
            func: Function to call (can be async or sync)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If breaker is OPEN
            Exception: Any exception raised by func
        """
        async with self._lock:
            self._total_calls += 1

            # Check if breaker is OPEN
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout elapsed
                if self._should_attempt_recovery():
                    logger.info("CircuitBreaker '%s': Attempting recovery (HALF_OPEN)", self.name)
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    # Still OPEN, reject request
                    time_since_open = (
                        time.time() - self._last_open_time if self._last_open_time else 0
                    )
                    raise CircuitBreakerOpen(
                        self.name,
                        f"Circuit breaker '{self.name}' is OPEN "
                        f"({time_since_open:.1f}s / {self.recovery_timeout}s timeout)",
                    )

            # Execute function
            try:
                # Handle async and sync functions
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success - update state
                await self._on_success()

                return result

            except Exception as e:
                # Failure - update state
                await self._on_failure(e)
                raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1

            # Check if we should close the breaker
            if self._success_count >= self.success_threshold:
                logger.info(
                    f"CircuitBreaker '{self.name}': Recovery successful, closing "
                    f"({self._success_count}/{self.success_threshold} successes)"
                )
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._last_close_time = time.time()

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                logger.debug("CircuitBreaker '%s': Reset failure count after success", self.name)
                self._failure_count = 0

    async def _on_failure(self, exception: Exception) -> None:
        """Handle failed call.

        Args:
            exception: Exception that was raised
        """
        self._total_failures += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure during recovery attempt - reopen
            logger.warning(
                f"CircuitBreaker '{self.name}': Recovery failed, reopening "
                f"(error: {type(exception).__name__})"
            )
            self._state = CircuitState.OPEN
            self._last_open_time = time.time()
            self._total_opens += 1

        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1

            # Check if we should open the breaker
            if self._failure_count >= self.failure_threshold:
                logger.error(
                    f"CircuitBreaker '{self.name}': Opening due to {self._failure_count} "
                    f"consecutive failures (threshold={self.failure_threshold})"
                )
                self._state = CircuitState.OPEN
                self._last_open_time = time.time()
                self._total_opens += 1

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery should be attempted.

        Returns:
            True if recovery timeout has elapsed, False otherwise
        """
        if self._last_open_time is None:
            return False

        elapsed = time.time() - self._last_open_time
        return elapsed >= self.recovery_timeout

    async def force_open(self) -> None:
        """Force breaker to OPEN state (for testing/manual intervention)."""
        async with self._lock:
            logger.warning("CircuitBreaker '%s': Forced OPEN", self.name)
            self._state = CircuitState.OPEN
            self._last_open_time = time.time()
            self._total_opens += 1

    async def force_close(self) -> None:
        """Force breaker to CLOSED state (for testing/manual intervention)."""
        async with self._lock:
            logger.info("CircuitBreaker '%s': Forced CLOSED", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_close_time = time.time()

    def get_state(self) -> CircuitState:
        """Get current breaker state.

        Returns:
            Current CircuitState
        """
        return self._state

    def get_stats(self) -> CircuitBreakerStats:
        """Get breaker statistics.

        Returns:
            CircuitBreakerStats instance
        """
        return CircuitBreakerStats(
            name=self.name,
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            total_calls=self._total_calls,
            total_failures=self._total_failures,
            total_opens=self._total_opens,
            last_failure_time=self._last_failure_time,
            last_open_time=self._last_open_time,
            last_close_time=self._last_close_time,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"CircuitBreaker(name='{self.name}', state={self._state.value}, failures={self._failure_count}/{self.failure_threshold})"


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    This provides centralized management of circuit breakers across
    the application, with named breakers for different operations.
    """

    def __init__(self) -> None:
        """Initialize circuit breaker registry."""
        self._breakers: dict[str, CircuitBreaker] = {}
        logger.info("CircuitBreakerRegistry initialized")

    def get_or_create(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
        success_threshold: int | None = None,
    ) -> CircuitBreaker:
        """Get existing breaker or create new one.

        Args:
            name: Breaker name
            failure_threshold: Failure threshold (only used if creating, defaults from technique)
            recovery_timeout: Recovery timeout (only used if creating, defaults from technique)
            success_threshold: Success threshold (only used if creating, defaults from technique)

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )

        return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get existing breaker.

        Args:
            name: Breaker name

        Returns:
            CircuitBreaker or None if not found
        """
        return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get statistics for all breakers.

        Returns:
            Dict mapping breaker name to stats
        """
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def __repr__(self) -> str:
        """String representation."""
        return f"CircuitBreakerRegistry(breakers={len(self._breakers)})"


# Global registry (singleton)
_global_registry: CircuitBreakerRegistry | None = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry (singleton).

    Returns:
        CircuitBreakerRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()

    return _global_registry


def get_circuit_breaker(
    name: str,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
) -> CircuitBreaker:
    """Get or create circuit breaker from global registry.

    Args:
        name: Breaker name
        failure_threshold: Failure threshold (defaults from technique config)
        recovery_timeout: Recovery timeout (defaults from technique config)

    Returns:
        CircuitBreaker instance
    """
    registry = get_circuit_breaker_registry()
    return registry.get_or_create(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )
