"""
Runtime adapters module.

Provides base adapter classes and standardized interfaces for all adapter types.
"""

from .base import (
    AdapterConfig,
    AdapterResult,
    BaseAdapter,
    EmbeddingAdapterBase,
    LLMAdapterBase,
    VectorStoreAdapterBase,
)

__all__ = [
    "AdapterConfig",
    "AdapterResult",
    "BaseAdapter",
    "EmbeddingAdapterBase",
    "LLMAdapterBase",
    "VectorStoreAdapterBase",
]
