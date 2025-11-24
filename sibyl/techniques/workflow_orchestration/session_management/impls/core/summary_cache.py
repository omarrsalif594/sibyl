"""Content-addressed LRU cache for context summaries.

This module provides deterministic caching for context summaries with:
- Content-addressed keys: SHA256 hash of (context + turn_id + thresholds)
- LRU eviction: Fixed memory budget, evict least recently used
- Thread-safe: asyncio.Lock for concurrent access
- Idempotent: Same context always produces same cache key
- Race-safe: Late arrivals with stale keys are ignored

Key benefits:
- **Avoid re-summarization**: Same context summarized once
- **Memory bounded**: Fixed budget (default 10 summaries)
- **Deterministic**: Content hash ensures idempotence
- **Race-safe**: Stale cache keys ignored if context changed

Typical usage:
    cache = SummaryCache(max_entries=10, max_memory_bytes=50_000_000)

    # Generate cache key
    cache_key = cache.compute_key(context, session_id, turn_id)

    # Try cache first
    summary = await cache.get(cache_key)
    if summary:
        return summary  # Cache hit

    # Cache miss: generate summary
    summary = await expensive_llm_call(context)

    # Store in cache
    await cache.set(cache_key, summary)
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata.

    Attributes:
        key: Cache key (SHA256 hash)
        summary: Cached summary content
        size_bytes: Approximate size in bytes
        created_at: Timestamp when cached
        accessed_at: Timestamp of last access
        access_count: Number of times accessed
        session_id: Session that created this entry
        turn_id: Turn ID at creation time
    """

    key: str
    summary: dict[str, Any]
    size_bytes: int
    created_at: float
    accessed_at: float
    access_count: int
    session_id: str
    turn_id: int


class SummaryCache:
    """LRU cache for context summaries with content-addressed keys.

    This cache provides:
    - Content-addressed keys (SHA256 of context + metadata)
    - LRU eviction (fixed memory budget)
    - Thread-safe operations (asyncio.Lock)
    - Cache statistics (hit rate, evictions)

    Cache key derivation:
        key = SHA256(json({
            "context_stable_hash": SHA256(stable_inputs),
            "context_dynamic_hash": SHA256(dynamic_observations),
            "session_id": session_id,
            "turn_id": turn_id,
            "summarize_threshold": threshold,
            "rotate_threshold": threshold
        }))

    This ensures:
    - Same context + metadata → same key (deterministic)
    - Different turn → different key (captures progression)
    - Different thresholds → different key (threshold-specific summaries)
    """

    def __init__(self, max_entries: int = 10, max_memory_bytes: int = 50_000_000) -> None:
        """Initialize summary cache.

        Args:
            max_entries: Maximum number of entries (default 10)
            max_memory_bytes: Maximum memory budget in bytes (default 50MB)
        """
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_bytes

        # LRU cache (OrderedDict maintains insertion order)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Memory tracking
        self._current_memory_bytes = 0

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._sets = 0

        # Eviction pressure tracking (rolling 10-minute window)
        self._eviction_window_seconds = 600  # 10 minutes
        self._eviction_history: deque[tuple[float, int]] = deque()  # (timestamp, eviction_count)
        self._set_history: deque[tuple[float, int]] = deque()  # (timestamp, set_count)

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"SummaryCache initialized: max_entries={max_entries}, "
            f"max_memory_mb={max_memory_bytes / 1_000_000:.1f}"
        )

    def compute_key(
        self,
        context: dict[str, Any],
        session_id: str,
        turn_id: int,
        summarize_threshold: float,
        rotate_threshold: float,
    ) -> str:
        """Compute content-addressed cache key.

        The key is derived from:
        - Context content (stable and dynamic hashes)
        - Session identifier
        - Turn ID (captures conversation progression)
        - Thresholds (threshold-specific summaries)

        Args:
            context: Context dict with stable_inputs, dynamic_observations, etc.
            session_id: Session identifier
            turn_id: Turn number
            summarize_threshold: Summarize threshold percentage
            rotate_threshold: Rotate threshold percentage

        Returns:
            SHA256 hex digest (cache key)
        """
        # Extract or compute context hashes
        stable_hash = context.get("stable_hash") or self._compute_hash(
            json.dumps(context.get("stable_inputs", {}), sort_keys=True)
        )

        dynamic_hash = context.get("dynamic_hash") or self._compute_hash(
            json.dumps(context.get("dynamic_observations", {}), sort_keys=True)
        )

        # Compose cache key input
        key_input = {
            "context_stable_hash": stable_hash,
            "context_dynamic_hash": dynamic_hash,
            "session_id": session_id,
            "turn_id": turn_id,
            "summarize_threshold": summarize_threshold,
            "rotate_threshold": rotate_threshold,
        }

        # Compute cache key
        key_text = json.dumps(key_input, sort_keys=True)
        return self._compute_hash(key_text)

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get summary from cache.

        Args:
            key: Cache key

        Returns:
            Summary dict or None if not found
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                logger.debug("Cache miss: %s...", key[:8])
                return None

            # Cache hit: update access metadata
            entry.accessed_at = time.time()
            entry.access_count += 1

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            self._hits += 1
            logger.debug(
                f"Cache hit: {key[:8]}... (accesses={entry.access_count}, "
                f"age={time.time() - entry.created_at:.1f}s)"
            )

            return entry.summary

    async def set(
        self,
        key: str,
        summary: dict[str, Any],
        session_id: str,
        turn_id: int,
    ) -> None:
        """Store summary in cache.

        Args:
            key: Cache key
            summary: Summary content
            session_id: Session that created this entry
            turn_id: Turn ID at creation
        """
        async with self._lock:
            # Check if key already exists (idempotent)
            if key in self._cache:
                logger.debug("Cache key already exists: %s... (idempotent)", key[:8])
                return

            # Estimate size
            size_bytes = len(json.dumps(summary))

            # Create entry
            entry = CacheEntry(
                key=key,
                summary=summary,
                size_bytes=size_bytes,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                session_id=session_id,
                turn_id=turn_id,
            )

            # Evict if necessary (before adding)
            await self._evict_if_needed(size_bytes)

            # Add to cache
            self._cache[key] = entry
            self._current_memory_bytes += size_bytes
            self._sets += 1

            # Record set in rolling window
            current_time = time.time()
            self._set_history.append((current_time, self._sets))
            self._cleanup_history(self._set_history)

            logger.debug(
                f"Cache set: {key[:8]}... (size={size_bytes} bytes, "
                f"entries={len(self._cache)}, memory={self._current_memory_bytes / 1_000_000:.1f}MB)"
            )

    async def _evict_if_needed(self, incoming_size_bytes: int) -> None:
        """Evict entries if adding incoming entry would exceed limits.

        LRU eviction: Remove least recently used entries first.

        Args:
            incoming_size_bytes: Size of entry about to be added
        """
        # Evict by entry count
        while len(self._cache) >= self.max_entries:
            await self._evict_lru()

        # Evict by memory budget
        while self._current_memory_bytes + incoming_size_bytes > self.max_memory_bytes:
            if len(self._cache) == 0:
                break  # Can't evict anymore
            await self._evict_lru()

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if len(self._cache) == 0:
            return

        # OrderedDict: first item is least recently used
        lru_key, lru_entry = self._cache.popitem(last=False)

        self._current_memory_bytes -= lru_entry.size_bytes
        self._evictions += 1

        # Record eviction in rolling window
        current_time = time.time()
        self._eviction_history.append((current_time, self._evictions))
        self._cleanup_history(self._eviction_history)

        logger.debug(
            f"Evicted LRU entry: {lru_key[:8]}... (size={lru_entry.size_bytes} bytes, "
            f"age={time.time() - lru_entry.created_at:.1f}s, accesses={lru_entry.access_count})"
        )

    async def invalidate(self, session_id: str) -> None:
        """Invalidate all cache entries for a session.

        This should be called when a session is rotated to prevent stale
        cache hits from old context.

        Args:
            session_id: Session to invalidate
        """
        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items() if entry.session_id == session_id
            ]

            for key in keys_to_remove:
                entry = self._cache.pop(key)
                self._current_memory_bytes -= entry.size_bytes

            if keys_to_remove:
                logger.info(
                    "Invalidated %s cache entries for session %s", len(keys_to_remove), session_id
                )

    async def clear(self) -> None:
        """Clear entire cache."""
        async with self._lock:
            self._cache.clear()
            self._current_memory_bytes = 0
            logger.info("Cache cleared")

    def _cleanup_history(self, history: deque[tuple[float, int]]) -> None:
        """Remove entries older than eviction window.

        Args:
            history: Deque of (timestamp, count) tuples
        """
        current_time = time.time()
        cutoff_time = current_time - self._eviction_window_seconds

        # Remove old entries from the front
        while history and history[0][0] < cutoff_time:
            history.popleft()

    def _compute_eviction_rate(self) -> dict[str, Any]:
        """Compute eviction rate metrics over rolling window.

        Returns:
            Dict with eviction rate metrics
        """
        current_time = time.time()
        current_time - self._eviction_window_seconds

        # Count evictions in window
        evictions_in_window = 0
        if len(self._eviction_history) > 0:
            # Get earliest and latest eviction counts in window
            earliest_count = self._eviction_history[0][1] if self._eviction_history else 0
            latest_count = self._eviction_history[-1][1] if self._eviction_history else 0
            evictions_in_window = latest_count - earliest_count

        # Count sets in window
        sets_in_window = 0
        if len(self._set_history) > 0:
            earliest_count = self._set_history[0][1] if self._set_history else 0
            latest_count = self._set_history[-1][1] if self._set_history else 0
            sets_in_window = latest_count - earliest_count

        # Compute rates
        window_minutes = self._eviction_window_seconds / 60
        eviction_rate_per_minute = (
            evictions_in_window / window_minutes if window_minutes > 0 else 0.0
        )
        eviction_rate_pct = (
            (evictions_in_window / sets_in_window * 100) if sets_in_window > 0 else 0.0
        )

        # Check if sustained high eviction (>10% for 10 minutes)
        sustained_high_eviction = eviction_rate_pct > 10.0 and len(self._eviction_history) > 0

        return {
            "evictions_in_window": evictions_in_window,
            "sets_in_window": sets_in_window,
            "eviction_rate_per_minute": eviction_rate_per_minute,
            "eviction_rate_pct": eviction_rate_pct,
            "sustained_high_eviction": sustained_high_eviction,
            "window_seconds": self._eviction_window_seconds,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with stats including eviction pressure metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        # Get eviction rate metrics
        eviction_metrics = self._compute_eviction_rate()

        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "memory_bytes": self._current_memory_bytes,
            "max_memory_bytes": self.max_memory_bytes,
            "memory_utilization": self._current_memory_bytes / self.max_memory_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "sets": self._sets,
            # Eviction pressure metrics
            "evictions_in_window": eviction_metrics["evictions_in_window"],
            "sets_in_window": eviction_metrics["sets_in_window"],
            "eviction_rate_per_minute": eviction_metrics["eviction_rate_per_minute"],
            "eviction_rate_pct": eviction_metrics["eviction_rate_pct"],
            "sustained_high_eviction": eviction_metrics["sustained_high_eviction"],
            "eviction_window_seconds": eviction_metrics["window_seconds"],
        }

    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash.

        Args:
            text: Text to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"SummaryCache(entries={stats['entries']}/{stats['max_entries']}, "
            f"memory={stats['memory_bytes'] / 1_000_000:.1f}MB, "
            f"hit_rate={stats['hit_rate']:.1%})"
        )


# Global cache instance (singleton pattern)
_global_cache: SummaryCache | None = None


def get_summary_cache(max_entries: int = 10, max_memory_bytes: int = 50_000_000) -> SummaryCache:
    """Get global summary cache instance (singleton).

    Args:
        max_entries: Maximum entries (only used on first call)
        max_memory_bytes: Maximum memory (only used on first call)

    Returns:
        SummaryCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = SummaryCache(max_entries=max_entries, max_memory_bytes=max_memory_bytes)

    return _global_cache
