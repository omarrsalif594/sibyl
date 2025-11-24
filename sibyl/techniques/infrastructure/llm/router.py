"""LLM Router with backpressure, circuit breakers, and exponential backoff."""

import asyncio
import logging
import random
from typing import Any

from sibyl.config import get_llm_config
from sibyl.core.contracts.providers import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
)
from sibyl.core.infrastructure.llm.errors import (
    CircuitOpenError,
    RateLimitError,
    TransientProviderError,
)
from sibyl.techniques.infrastructure.providers.registry import ProviderRegistry
from sibyl.techniques.infrastructure.rate_limiting.subtechniques.leaky_bucket.default.backpressure import (
    CircuitBreaker,
    RouteLimiter,
)
from sibyl.techniques.infrastructure.token_management.subtechniques.counting.default.token_counter import (
    TokenCounter,
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """Route LLM requests with backpressure and fault tolerance.

    Features:
    - Per-route concurrency limits (semaphore)
    - Per-route rate limits (RPM + TPM)
    - Circuit breakers per route
    - Exponential backoff with jitter
    - Auto-tuning from rate-limit headers
    - Dynamic provider instantiation via ProviderRegistry
    """

    def __init__(
        self, config: dict[str, Any], provider_registry: ProviderRegistry | None = None
    ) -> None:
        """Initialize router.

        Args:
            config: Configuration dict with provider settings
            provider_registry: Optional ProviderRegistry for dynamic provider instantiation
        """
        self.config = config
        self._provider_registry = provider_registry
        self._clients: dict[str, LLMProvider] = {}

        # Per-route controls
        self._limiters: dict[str, RouteLimiter] = {}
        self._breakers: dict[str, CircuitBreaker] = {}

        # Load retry configuration from core config
        llm_config = get_llm_config()
        retry_config = llm_config.get("retry", {})
        self._max_retries = retry_config.get("max_retries", 3)
        self._base_delay = retry_config.get("base_delay", 1.0)
        self._max_delay = retry_config.get("max_delay", 60.0)

        # Store jitter_percent for use in backoff calculation
        self._jitter_percent = retry_config.get("jitter_percent", 20)

    def register_client(self, provider: str, client: LLMProvider) -> None:
        """Register a provider client.

        Args:
            provider: Provider name ("anthropic", "openai", etc.)
            client: LLM provider implementation
        """
        self._clients[provider] = client
        logger.info("Registered LLM provider: %s", provider)

    def _get_or_create_client(self, provider: str) -> LLMProvider:
        """Get or create a provider client.

        Uses cached client if available, otherwise creates a new one using
        the ProviderRegistry.

        Args:
            provider: Provider name

        Returns:
            LLM provider instance

        Raises:
            KeyError: If provider not registered and registry not available
            ValueError: If provider cannot be instantiated
        """
        # Return cached client if available
        if provider in self._clients:
            return self._clients[provider]

        # Try to create using registry
        if self._provider_registry is None:
            msg = (
                f"Provider not registered: {provider}. "
                "Either register the client manually or provide a ProviderRegistry."
            )
            raise KeyError(msg)

        try:
            logger.info("Creating provider instance for: %s", provider)
            client = self._provider_registry.create_llm_provider_instance(provider)
            # Cache the created client
            self._clients[provider] = client
            logger.info("Successfully created and cached LLM provider: %s", provider)
            return client
        except Exception as e:
            msg = f"Failed to create provider {provider}: {e}"
            raise ValueError(msg)

    def _get_route_key(self, provider: str, model: str) -> str:
        """Get unique route key.

        Args:
            provider: Provider name
            model: Model name

        Returns:
            Route key for tracking limits
        """
        return f"{provider}:{model}"

    def _get_limiter(self, route_key: str, provider: str) -> RouteLimiter:
        """Get or create rate limiter for route.

        Args:
            route_key: Route identifier
            provider: Provider name

        Returns:
            RouteLimiter instance
        """
        if route_key not in self._limiters:
            # Get rate limits from config
            provider_config = self.config.get("providers", {}).get(provider, {})
            rate_limit_config = provider_config.get("rate_limit", {})

            max_concurrent = rate_limit_config.get("max_concurrent", 10)
            rpm = rate_limit_config.get("requests_per_minute", 50)
            tpm = rate_limit_config.get("tokens_per_minute")

            self._limiters[route_key] = RouteLimiter(max_concurrent, rpm, tpm)

            logger.info(
                f"Created rate limiter for {route_key}: "
                f"concurrent={max_concurrent}, RPM={rpm}, TPM={tpm}"
            )

        return self._limiters[route_key]

    def _get_breaker(self, route_key: str, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for route.

        Args:
            route_key: Route identifier
            provider: Provider name

        Returns:
            CircuitBreaker instance
        """
        if route_key not in self._breakers:
            # Get circuit breaker config from provider config first, then fallback to core config
            provider_config = self.config.get("providers", {}).get(provider, {})
            breaker_config = provider_config.get("circuit_breaker", {})

            # Fallback to core config defaults
            llm_config = get_llm_config()
            core_breaker_config = llm_config.get("circuit_breaker", {})

            threshold = breaker_config.get("failure_threshold") or core_breaker_config.get(
                "failure_threshold", 5
            )
            cooldown = breaker_config.get("cooldown_seconds") or core_breaker_config.get(
                "cooldown_seconds", 30
            )
            auto_tune = breaker_config.get("auto_tune", True)

            self._breakers[route_key] = CircuitBreaker(threshold, cooldown, auto_tune)

            logger.info(
                f"Created circuit breaker for {route_key}: "
                f"threshold={threshold}, cooldown={cooldown}s (from {'provider config' if 'failure_threshold' in breaker_config else 'core config'})"
            )

        return self._breakers[route_key]

    async def route(
        self,
        provider: str,
        model: str,
        prompt: str,
        options: CompletionOptions,
        priority: int = 5,
    ) -> CompletionResult:
        """Route request to provider with backpressure and fault tolerance.

        Args:
            provider: Provider name
            model: Model name
            prompt: Input prompt
            options: Completion options
            priority: Priority level (lower = higher priority, not yet implemented)

        Returns:
            CompletionResult

        Raises:
            KeyError: If provider not registered and registry not available
            ValueError: If provider cannot be instantiated
            CircuitOpenError: If circuit is open
            RateLimitError: After all retries exhausted
            TransientProviderError: After all retries exhausted
        """
        # Get or create client using registry
        client = self._get_or_create_client(provider)
        route_key = self._get_route_key(provider, model)

        # Get backpressure controls
        limiter = self._get_limiter(route_key, provider)
        breaker = self._get_breaker(route_key, provider)

        # Preflight token estimation
        estimated_tokens = TokenCounter.count(prompt, model, provider)

        logger.debug(
            f"Routing request to {route_key} "
            f"(est. {estimated_tokens} tokens, correlation_id={options.correlation_id})"
        )

        # Retry loop with exponential backoff
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                # Acquire rate limit permit (may block)
                async with await limiter.acquire(estimated_tokens):
                    # Execute with circuit breaker protection
                    result = await breaker.guard(
                        lambda: client.complete_async(prompt, options), route_key
                    )

                    logger.info(
                        f"Request succeeded: {route_key} "
                        f"(tokens: {result['tokens_in']} in, {result['tokens_out']} out, "
                        f"latency: {result['latency_ms']}ms)"
                    )

                    return result

            except CircuitOpenError:
                # Don't retry if circuit is open
                logger.exception("Circuit open for %s, aborting", route_key)
                raise

            except (RateLimitError, TransientProviderError) as e:
                last_error = e
                logger.warning(
                    "Request failed (attempt %s/%s): %s", attempt + 1, self._max_retries, e
                )

                # Exponential backoff with jitter
                if attempt < self._max_retries - 1:
                    delay = self._calculate_backoff(attempt, e)
                    logger.info("Backing off %ss before retry", delay)
                    await asyncio.sleep(delay)
                else:
                    logger.exception("All retries exhausted for %s, giving up", route_key)

        # All retries exhausted
        if last_error:
            raise last_error
        msg = f"Request failed with no error (route={route_key})"
        raise RuntimeError(msg)

    def _calculate_backoff(self, attempt: int, error: Exception) -> float:
        """Calculate backoff delay with exponential increase and jitter.

        Args:
            attempt: Attempt number (0-indexed)
            error: The error that triggered backoff

        Returns:
            Delay in seconds
        """
        # Exponential: 1s, 2s, 4s, 8s, ... (using configured base_delay and max_delay)
        base_delay = self._base_delay * (2**attempt)

        # Cap at max_delay
        base_delay = min(base_delay, self._max_delay)

        # If RateLimitError with retry_after, use that
        if isinstance(error, RateLimitError) and error.retry_after:
            base_delay = max(base_delay, error.retry_after)

        # Add jitter using configured jitter_percent (default 20%)
        # Convert to range: jitter_percent=20 means +/- 20%
        # S311: Using random for backoff jitter (not security-sensitive)
        jitter_factor = (self._jitter_percent / 100.0) * (random.random() * 2 - 1)
        jitter = base_delay * jitter_factor
        delay = base_delay + jitter

        return max(0, delay)  # Ensure non-negative

    def get_stats(self, provider: str | None = None) -> dict[str, Any]:
        """Get router statistics.

        Args:
            provider: Optional provider filter

        Returns:
            Dict with stats for all routes (or filtered routes)
        """
        stats = {}

        for route_key, limiter in self._limiters.items():
            # Filter by provider if specified
            if provider and not route_key.startswith(f"{provider}:"):
                continue

            breaker = self._breakers.get(route_key)

            stats[route_key] = {
                "limiter": limiter.get_stats(),
                "breaker": {
                    "failures": breaker.failures if breaker else 0,
                    "open": breaker.open_until > 0 if breaker else False,
                },
            }

        return stats
