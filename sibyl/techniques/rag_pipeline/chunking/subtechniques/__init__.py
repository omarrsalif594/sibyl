"""
Chunking Subtechniques

This module contains various chunking strategies:
- semantic: Semantic-based chunking
- fixed_size: Fixed-size chunking
- plugin_adapter: Adapter for existing plugin-based chunkers
"""

from .fixed_size import FixedSizeChunking
from .plugin_adapter import PluginAdapterChunking
from .semantic import SemanticChunking

__all__ = [
    "FixedSizeChunking",
    "PluginAdapterChunking",
    "SemanticChunking",
]
