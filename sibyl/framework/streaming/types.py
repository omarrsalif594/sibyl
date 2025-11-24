"""Minimal streaming interface for MCP operations.

This module provides basic primitives for streaming responses from long-running
MCP operations. It defines data structures only - no complex implementations.

Design Principles:
- Minimal: Just data structures, no UI logic
- Async-compatible: Uses AsyncIterator for streaming
- Extensible: Can be enhanced later without breaking changes

Example:
    from sibyl.framework.streaming import StreamChunk, StreamChunkType

    # Progress chunk
    chunk = StreamChunk(
        type=StreamChunkType.PROGRESS,
        data={"percentage": 45, "message": "Processing batch 3/10"},
        timestamp=datetime.now()
    )

    # Intermediate result chunk
    chunk = StreamChunk(
        type=StreamChunkType.INTERMEDIATE,
        data={"partial_results": [...]},
        timestamp=datetime.now()
    )

    # Final result chunk
    chunk = StreamChunk(
        type=StreamChunkType.FINAL,
        data={"status": "completed", "result": {...}},
        timestamp=datetime.now()
    )
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class StreamChunkType(Enum):
    """Types of streaming chunks.

    These types categorize the different kinds of updates that can be sent
    during a streaming operation.
    """

    PROGRESS = "progress"  # Progress update (percentage, status message)
    INTERMEDIATE = "intermediate"  # Intermediate result (partial data)
    FINAL = "final"  # Final result (job completed)


@dataclass
class StreamChunk:
    """A single chunk in a streaming response.

    This is a minimal data structure for streaming updates from long-running
    MCP operations. It contains no UI logic - just data.

    Attributes:
        type: Type of chunk (progress, intermediate, final)
        data: Chunk payload (structure depends on type)
        timestamp: When chunk was created
        sequence: Optional sequence number for ordering

    Example:
        # Progress chunk
        chunk = StreamChunk(
            type=StreamChunkType.PROGRESS,
            data={"percentage": 45, "message": "Processing batch 3/10"},
            timestamp=datetime.now()
        )

        # Check if final
        if chunk.is_final():
            print("Job completed!")

        # Serialize
        chunk_dict = chunk.to_dict()
    """

    type: StreamChunkType
    data: dict[str, Any]
    timestamp: datetime
    sequence: int = 0

    def is_final(self) -> bool:
        """Check if this is the final chunk.

        Returns:
            True if chunk type is FINAL
        """
        return self.type == StreamChunkType.FINAL

    def is_progress(self) -> bool:
        """Check if this is a progress chunk.

        Returns:
            True if chunk type is PROGRESS
        """
        return self.type == StreamChunkType.PROGRESS

    def is_intermediate(self) -> bool:
        """Check if this is an intermediate result chunk.

        Returns:
            True if chunk type is INTERMEDIATE
        """
        return self.type == StreamChunkType.INTERMEDIATE

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation (JSON-serializable)
        """
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }


# Type alias for streaming functions
StreamGenerator = AsyncIterator[StreamChunk]
