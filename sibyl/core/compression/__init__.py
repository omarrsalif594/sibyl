"""Core compression interfaces and artifacts.

This module provides the foundation for the compression wall pattern:
- Compressor protocol for implementing compression strategies
- CompressionResult artifact for capturing compression metadata
- Standard interfaces for compression chains

The compression wall sits before routing to reduce prompt size while
preserving intent and context.
"""

from .artifacts import CompressionMetrics, CompressionResult
from .interfaces import CompressionChain, Compressor

__all__ = [
    "CompressionChain",
    "CompressionMetrics",
    "CompressionResult",
    "Compressor",
]
