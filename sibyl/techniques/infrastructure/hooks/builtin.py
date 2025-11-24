"""Built-in hook implementations.

This module provides standard hooks for common use cases:
- MetricsHook: Record operation metrics (duration, success/failure)
- CacheHook: Cache operation results to avoid expensive recomputation

Example:
    from sibyl.mcp_server.infrastructure.hooks import (
        get_hook_registry,
        MetricsHook,
        CacheHook,
    )

    registry = get_hook_registry()
    registry.register(MetricsHook())
    registry.register(CacheHook(ttl_seconds=300))
"""

import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sibyl.core.protocols.infrastructure.hooks import HookContext

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation.

    Attributes:
        operation_name: Name of the operation
        total_calls: Total number of calls
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        total_duration_ms: Total duration in milliseconds
        min_duration_ms: Minimum duration
        max_duration_ms: Maximum duration
        last_call_time: When operation was last called
    """

    operation_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0
    last_call_time: datetime | None = None

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation_name": self.operation_name,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms
            if self.min_duration_ms != float("inf")
            else None,
            "max_duration_ms": self.max_duration_ms,
            "success_rate": self.success_rate,
            "last_call_time": self.last_call_time.isoformat() if self.last_call_time else None,
        }


class MetricsHook:
    """Hook for recording operation metrics.

    Tracks:
    - Call counts (total, successful, failed)
    - Duration statistics (min, max, avg)
    - Success rates
    - Last call times

    All metrics are in-memory and reset on server restart.
    """

    name: str = "metrics"
    priority: int = 100  # High priority to measure accurately
    enabled: bool = True

    def __init__(self) -> None:
        """Initialize metrics hook."""
        self._metrics: dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics(operation_name="")
        )
        self._operation_start_times: dict[str, float] = {}

    async def before(self, context: HookContext) -> HookContext:
        """Record operation start time.

        Args:
            context: Operation context

        Returns:
            Unmodified context
        """
        # Record start time for this operation invocation
        self._operation_start_times[context.operation_id] = time.time()

        # Initialize metrics for this operation if needed
        if context.operation_name not in self._metrics:
            self._metrics[context.operation_name] = OperationMetrics(
                operation_name=context.operation_name
            )

        # Increment total calls
        metrics = self._metrics[context.operation_name]
        metrics.total_calls += 1
        metrics.last_call_time = datetime.utcnow()

        return context

    async def after(self, context: HookContext, result: Any) -> Any:
        """Record successful operation completion.

        Args:
            context: Operation context
            result: Operation result

        Returns:
            Unmodified result
        """
        # Calculate duration
        if context.operation_id in self._operation_start_times:
            start_time = self._operation_start_times[context.operation_id]
            duration_ms = (time.time() - start_time) * 1000
            del self._operation_start_times[context.operation_id]

            # Update metrics
            metrics = self._metrics[context.operation_name]
            metrics.successful_calls += 1
            metrics.total_duration_ms += duration_ms
            metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
            metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)

            logger.debug("Operation %s completed in %sms", context.operation_name, duration_ms)
        return result

    async def on_error(self, context: HookContext, error: Exception) -> Exception:
        """Record failed operation.

        Args:
            context: Operation context
            error: Exception that was raised

        Returns:
            Unmodified exception
        """
        # Calculate duration
        if context.operation_id in self._operation_start_times:
            start_time = self._operation_start_times[context.operation_id]
            duration_ms = (time.time() - start_time) * 1000
            del self._operation_start_times[context.operation_id]

            # Update metrics
            metrics = self._metrics[context.operation_name]
            metrics.failed_calls += 1
            metrics.total_duration_ms += duration_ms
            metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
            metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)

            logger.debug(
                "Operation %s failed after %sms: %s", context.operation_name, duration_ms, error
            )
        return error

    def get_metrics(self, operation_name: str | None = None) -> dict[str, Any]:
        """Get metrics for one or all operations.

        Args:
            operation_name: Specific operation name, or None for all

        Returns:
            Dictionary of metrics
        """
        if operation_name:
            if operation_name in self._metrics:
                return self._metrics[operation_name].to_dict()
            return {}

        # Return all metrics
        return {name: metrics.to_dict() for name, metrics in self._metrics.items()}

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._operation_start_times.clear()
        logger.info("Metrics reset")


@dataclass
class CacheEntry:
    """Cache entry with result and metadata.

    Attributes:
        result: Cached result
        created_at: When entry was created
        access_count: Number of times entry was accessed
        last_access: When entry was last accessed
    """

    result: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired
        """
        age = datetime.utcnow() - self.created_at
        return age.total_seconds() > ttl_seconds


class CacheHook:
    """Hook for caching operation results.

    Caches results based on operation name and arguments.
    Useful for expensive operations that are called multiple times
    with the same inputs.

    Features:
    - TTL-based expiration
    - LRU eviction when cache is full
    - Cache hit/miss metrics
    - Configurable cache size

    Note:
        Only caches operations that return successfully.
        Cache keys are based on operation name + stringified arguments.
    """

    name: str = "cache"
    priority: int = 90  # High priority but after metrics
    enabled: bool = True

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_entries: int = 1000,
        cache_errors: bool = False,
    ) -> None:
        """Initialize cache hook.

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 300s = 5min)
            max_entries: Maximum number of cache entries (default: 1000)
            cache_errors: Whether to cache error results (default: False)
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.cache_errors = cache_errors

        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    async def before(self, context: HookContext) -> HookContext:
        """Check cache for existing result.

        If cache hit, stores result in context metadata to skip execution.

        Args:
            context: Operation context

        Returns:
            Context with cache_hit flag if found
        """
        cache_key = self._compute_cache_key(context)

        # Check if entry exists and is not expired
        if cache_key in self._cache:
            entry = self._cache[cache_key]

            if not entry.is_expired(self.ttl_seconds):
                # Cache hit!
                self._hits += 1
                entry.access_count += 1
                entry.last_access = datetime.utcnow()

                logger.debug(
                    "Cache HIT for %s (age=%s)",
                    context.operation_name,
                    datetime.utcnow() - entry.created_at,
                )

                # Store cached result in context for retrieval
                return context.with_metadata(
                    cache_hit=True,
                    cached_result=entry.result,
                )
            # Expired - remove it
            del self._cache[cache_key]
            logger.debug("Cache EXPIRED for %s", context.operation_name)

        # Cache miss
        self._misses += 1
        logger.debug("Cache MISS for %s", context.operation_name)

        return context.with_metadata(cache_hit=False)

    async def after(self, context: HookContext, result: Any) -> Any:
        """Store result in cache.

        Args:
            context: Operation context
            result: Operation result

        Returns:
            Unmodified result
        """
        # If cache hit, return cached result instead
        if context.metadata.get("cache_hit"):
            return context.metadata.get("cached_result")

        # Store result in cache
        cache_key = self._compute_cache_key(context)

        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_entries:
            self._evict_lru()

        # Store entry
        self._cache[cache_key] = CacheEntry(result=result)

        logger.debug(
            "Cached result for %s (cache size: %s)", context.operation_name, len(self._cache)
        )

        return result

    async def on_error(self, context: HookContext, error: Exception) -> Exception:
        """Optionally cache error results.

        Args:
            context: Operation context
            error: Exception that was raised

        Returns:
            Unmodified exception
        """
        if self.cache_errors:
            cache_key = self._compute_cache_key(context)

            # Evict oldest entry if cache is full
            if len(self._cache) >= self.max_entries:
                self._evict_lru()

            # Store error as cached result
            self._cache[cache_key] = CacheEntry(result=error)

            logger.debug("Cached error for %s", context.operation_name)

        return error

    def _compute_cache_key(self, context: HookContext) -> str:
        """Compute cache key from context.

        Args:
            context: Operation context

        Returns:
            Cache key string
        """
        # Create deterministic key from operation name + args + kwargs
        key_parts = [context.operation_name]

        # Add args
        for arg in context.args:
            key_parts.append(self._serialize_arg(arg))

        # Add sorted kwargs
        for k, v in sorted(context.kwargs.items()):
            key_parts.append(f"{k}={self._serialize_arg(v)}")

        key_string = "|".join(key_parts)

        # Hash for consistent length
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _serialize_arg(self, arg: Any) -> str:
        """Serialize argument to string.

        Args:
            arg: Argument value

        Returns:
            String representation
        """
        try:
            # Try JSON serialization first
            return json.dumps(arg, sort_keys=True, default=str)
        except Exception:
            # Fall back to str()
            return str(arg)

    def _evict_lru(self) -> None:
        """Evict least recently used cache entry."""
        if not self._cache:
            return

        # Find entry with oldest last_access
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_access,
        )

        del self._cache[lru_key]
        logger.debug("Evicted LRU cache entry: %s...", lru_key[:16])

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
        }

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def invalidate(self, operation_name: str) -> None:
        """Invalidate all cache entries for an operation.

        Args:
            operation_name: Operation name to invalidate
        """
        keys_to_remove = [
            key for key, entry in self._cache.items() if key.startswith(operation_name)
        ]

        for key in keys_to_remove:
            del self._cache[key]

        logger.info("Invalidated %s cache entries for %s", len(keys_to_remove), operation_name)
