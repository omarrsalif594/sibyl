"""Backpressure controls: rate limiting, circuit breakers."""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from sibyl.core.infrastructure.llm.errors import CircuitOpenError, RateLimitError

logger = logging.getLogger(__name__)


class LeakyBucket:
    """Rate limiter with RPM and TPM tracking using monotonic time.

    Uses monotonic clock to avoid wall-clock jumps and implements
    a token bucket style for more predictable refill under bursty loads.
    """

    def __init__(self, requests_per_minute: int, tokens_per_minute: int | None = None) -> None:
        """Initialize leaky bucket.

        Args:
            requests_per_minute: Max requests per 60s window
            tokens_per_minute: Optional max tokens per 60s window
        """
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute

        # Use deque for efficient popleft
        self._req_timestamps: deque[float] = deque()
        self._token_usage: deque[tuple[float, int]] = deque()  # (timestamp, tokens)

        self._lock = asyncio.Lock()

        # For monotonic time tracking
        self._start_monotonic = time.monotonic()
        self._start_real = time.time()

    def _monotonic_now(self) -> float:
        """Get current time using monotonic clock.

        Returns:
            Current monotonic time
        """
        return time.monotonic()

    async def acquire(self, estimated_tokens: int = 0) -> bool:
        """Acquire permit; blocks if rate limit would be hit.

        Args:
            estimated_tokens: Estimated token count for this request

        Returns:
            True when permit acquired

        Raises:
            RateLimitError: If rate limit cannot be met (shouldn't happen with blocking)
        """
        async with self._lock:
            now = self._monotonic_now()
            cutoff = now - 60.0  # 1 minute window

            # Evict old entries
            while self._req_timestamps and self._req_timestamps[0] < cutoff:
                self._req_timestamps.popleft()
            while self._token_usage and self._token_usage[0][0] < cutoff:
                self._token_usage.popleft()

            # Check RPM
            if len(self._req_timestamps) >= self.rpm:
                # Calculate wait time
                oldest_req = self._req_timestamps[0]
                wait_until = oldest_req + 60.0
                wait_seconds = max(0, wait_until - now)

                if wait_seconds > 0:
                    logger.debug(
                        "RPM limit hit, waiting %ss (current: %s/%s)",
                        wait_seconds,
                        len(self._req_timestamps),
                        self.rpm,
                    )
                    await asyncio.sleep(wait_seconds)
                    # Recursive retry after wait
                    return await self.acquire(estimated_tokens)

            # Check TPM
            if self.tpm and estimated_tokens > 0:
                current_tokens = sum(t for _, t in self._token_usage)
                if current_tokens + estimated_tokens > self.tpm:
                    # Calculate wait time based on oldest token usage
                    if self._token_usage:
                        oldest_token_time = self._token_usage[0][0]
                        wait_until = oldest_token_time + 60.0
                        wait_seconds = max(0, wait_until - now)

                        if wait_seconds > 0:
                            logger.debug(
                                "TPM limit hit, waiting %ss (current: %s/%s)",
                                wait_seconds,
                                current_tokens,
                                self.tpm,
                            )
                            await asyncio.sleep(wait_seconds)
                            return await self.acquire(estimated_tokens)

            # Grant permit
            self._req_timestamps.append(now)
            if estimated_tokens > 0:
                self._token_usage.append((now, estimated_tokens))

            logger.debug(
                f"Rate limit permit granted (RPM: {len(self._req_timestamps)}/{self.rpm}, "
                f"TPM: {sum(t for _, t in self._token_usage)}/{self.tpm or 'N/A'})"
            )

            return True


class CircuitBreaker:
    """Circuit breaker with auto-tune from rate-limit headers.

    Opens circuit after N consecutive failures, then enters cooldown period.
    Supports auto-tuning rate limits from provider response headers.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 30,
        auto_tune: bool = True,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            cooldown_seconds: How long to keep circuit open
            auto_tune: Whether to adjust limits from rate-limit headers
        """
        self.threshold = failure_threshold
        self.cooldown = cooldown_seconds
        self.auto_tune = auto_tune

        self.failures = 0
        self.open_until = 0.0

        self._lock = asyncio.Lock()

    async def guard(self, call: Callable, route_key: str) -> Any:
        """Execute call with circuit breaker protection.

        Args:
            call: Async callable to execute
            route_key: Route identifier for logging

        Returns:
            Result from call

        Raises:
            CircuitOpenError: If circuit is open
            RateLimitError: From underlying call
            TransientProviderError: From underlying call
        """
        # Check if circuit is open (read-only, no lock needed for speed)
        now = time.monotonic()
        if now < self.open_until:
            msg = f"Circuit open for {route_key} until {self.open_until}"
            raise CircuitOpenError(msg, self.open_until)

        try:
            result = await call()

            # Success: reset failures
            async with self._lock:
                if self.failures > 0:
                    logger.info(
                        "Circuit breaker for %s: Success, resetting failures (was %s)",
                        route_key,
                        self.failures,
                    )
                    self.failures = 0

            # Auto-tune from headers if available
            if self.auto_tune and isinstance(result, dict):
                provider_metadata = result.get("provider_metadata", {})
                if "rate_limit_headers" in provider_metadata:
                    self._adjust_limits(route_key, provider_metadata["rate_limit_headers"])

            return result

        except (RateLimitError, Exception) as e:
            # Increment failure count
            async with self._lock:
                self.failures += 1

                logger.warning(
                    "Circuit breaker for %s: Failure %s/%s - %s",
                    route_key,
                    self.failures,
                    self.threshold,
                    e,
                )

                # Open circuit if threshold reached
                if self.failures >= self.threshold:
                    self.open_until = now + self.cooldown
                    logger.exception(
                        f"Circuit OPENED for {route_key} until {self.open_until} "
                        f"(cooldown: {self.cooldown}s)"
                    )

            raise

    def _adjust_limits(self, route_key: str, headers: dict[str, Any]) -> None:
        """Auto-tune rate limits from provider headers.

        Args:
            route_key: Route identifier
            headers: Rate limit headers from provider response
        """
        # Example headers from various providers:
        # - x-ratelimit-remaining-requests
        # - x-ratelimit-remaining-tokens
        # - x-ratelimit-reset-requests (timestamp)

        remaining_requests = headers.get("remaining_requests")
        remaining_tokens = headers.get("remaining_tokens")

        if remaining_requests is not None:
            logger.debug("Rate limit for %s: %s requests remaining", route_key, remaining_requests)

        if remaining_tokens is not None:
            logger.debug("Rate limit for %s: %s tokens remaining", route_key, remaining_tokens)

        # Could implement dynamic adjustment here:
        # - If remaining < 10% of limit, reduce concurrency
        # - If consistently high remaining, increase concurrency
        # For now, just log for observability

    async def reset(self) -> None:
        """Manually reset circuit breaker (for testing or admin intervention)."""
        async with self._lock:
            logger.info("Circuit breaker manually reset")
            self.failures = 0
            self.open_until = 0.0


class RouteLimiter:
    """Combined concurrency + rate limiting per route.

    Combines AsyncSemaphore (max concurrent) with LeakyBucket (RPM/TPM).
    """

    def __init__(
        self,
        max_concurrent: int,
        requests_per_minute: int,
        tokens_per_minute: int | None = None,
    ) -> None:
        """Initialize route limiter.

        Args:
            max_concurrent: Max concurrent requests
            requests_per_minute: Max requests per minute
            tokens_per_minute: Optional max tokens per minute
        """
        self.sem = asyncio.Semaphore(max_concurrent)
        self.bucket = LeakyBucket(requests_per_minute, tokens_per_minute)

        self.max_concurrent = max_concurrent
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute

    async def acquire(self, estimated_tokens: int = 0) -> Any:
        """Acquire both semaphore and rate limit permit.

        Args:
            estimated_tokens: Estimated token count

        Returns:
            Async context manager for semaphore
        """
        # First acquire rate limit permit (may block)
        await self.bucket.acquire(estimated_tokens)

        # Then acquire concurrency semaphore
        # Return context manager for use in "async with"
        return self.sem

    def get_stats(self) -> dict[str, Any]:
        """Get current limiter statistics.

        Returns:
            Dict with current usage stats
        """
        return {
            "max_concurrent": self.max_concurrent,
            "current_concurrent": self.max_concurrent - self.sem._value,  # type: ignore
            "rpm_limit": self.rpm,
            "tpm_limit": self.tpm,
        }
