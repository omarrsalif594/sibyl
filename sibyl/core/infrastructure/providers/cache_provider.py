"""
Cache provider implementation for CacheProvider protocol.

This module provides an adapter that wraps CacheManager from techniques
and implements the CacheProvider protocol with namespace support.
"""

from typing import Any

from sibyl.core.contracts.providers import CacheProvider
from sibyl.techniques.infrastructure.caching.subtechniques.lru_ttl.default.cache_manager import (
    CacheManager,
)


class CacheProviderAdapter:
    """
    Adapter that implements CacheProvider protocol using CacheManager.

    Adds namespace prefixing to all cache keys for better organization
    and scoped invalidation.
    """

    def __init__(self, cache_manager: CacheManager | None = None, ttl_seconds: int = 300) -> None:
        """
        Initialize cache provider adapter.

        Args:
            cache_manager: Underlying CacheManager instance (creates default if None)
            ttl_seconds: Default TTL in seconds
        """
        self._cache = cache_manager or CacheManager(
            max_size=1000,
            default_ttl=float(ttl_seconds),
            enable_stats=True,
        )
        self._default_ttl = ttl_seconds

    def get(self, namespace: str, key: str) -> Any | None:
        """
        Get cached value.

        Args:
            namespace: Cache namespace (e.g., "lineage", "patterns")
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        prefixed_key = self._make_key(namespace, key)
        return self._cache.get(prefixed_key)

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Set cached value with TTL.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be pickle-able)
            ttl_seconds: Time to live in seconds
        """
        prefixed_key = self._make_key(namespace, key)
        self._cache.set(prefixed_key, value, ttl=float(ttl_seconds))

    def invalidate(self, namespace: str, pattern: str | None = None) -> int:
        """
        Invalidate cached entries.

        Args:
            namespace: Cache namespace
            pattern: Optional glob pattern for keys (e.g., "model_*")
                     If None, invalidates entire namespace

        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            # Invalidate entire namespace
            namespace_pattern = f"{namespace}:*"
        else:
            # Invalidate specific pattern within namespace
            namespace_pattern = self._make_key(namespace, pattern)

        return self._cache.invalidate_by_pattern(namespace_pattern)

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, etc.
        """
        return self._cache.get_stats()

    def _make_key(self, namespace: str, key: str) -> str:
        """
        Build namespaced cache key.

        Args:
            namespace: Cache namespace
            key: Original key

        Returns:
            Prefixed key (e.g., "lineage:downstream:model_123")
        """
        return f"{namespace}:{key}"


# Type checking: verify adapter implements protocol
def _check_protocol_compliance() -> None:
    """Type check that adapter implements CacheProvider protocol."""
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        _: CacheProvider = CacheProviderAdapter()  # type: ignore


def create_cache_provider(ttl_seconds: int = 300) -> CacheProvider:
    """
    Create a CacheProvider instance.

    Args:
        ttl_seconds: Default TTL in seconds

    Returns:
        CacheProvider implementation
    """
    return CacheProviderAdapter(ttl_seconds=ttl_seconds)  # type: ignore


__all__ = [
    "CacheProviderAdapter",
    "create_cache_provider",
]
