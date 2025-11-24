"""Minimal streaming interface for MCP operations.

This module provides basic primitives for streaming responses from long-running
MCP operations. It defines data structures only - no complex implementations.

Design Principles:
- Minimal: Just data structures, no UI logic
- Async-compatible: Uses AsyncIterator for streaming
- Extensible: Can be enhanced later without breaking changes
"""

from sibyl.framework.streaming.types import (
    StreamChunk,
    StreamChunkType,
    StreamGenerator,
)

__all__ = [
    "StreamChunk",
    "StreamChunkType",
    "StreamGenerator",
]
