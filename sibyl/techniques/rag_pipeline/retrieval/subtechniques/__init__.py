"""
Retrieval Subtechniques

This module contains various retrieval strategies:
- semantic_search: Semantic similarity-based search
- chunk_searcher_adapter: Adapter for existing chunk searcher
"""

from .chunk_searcher_adapter import ChunkSearcherAdapter
from .semantic_search import SemanticSearch

__all__ = [
    "ChunkSearcherAdapter",
    "SemanticSearch",
]
