"""Chunking technique protocols and shared types.

This module defines the protocol interfaces and data structures for chunking operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class Chunk:
    """Single chunk of content."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    start_index: int = 0
    end_index: int = 0
    chunk_id: str = ""


@dataclass
class ChunkingResult:
    """Result from a chunking operation."""

    chunks: list[Chunk]
    original_content: str
    chunking_method: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Chunker(Protocol):
    """Protocol for chunking implementations."""

    @property
    def name(self) -> str:
        """Chunker name for identification."""
        ...

    def chunk(self, content: str, config: dict[str, Any]) -> list[Chunk]:
        """Chunk content into smaller pieces.

        Args:
            content: Content to chunk
            config: Configuration options (chunk_size, overlap, etc.)

        Returns:
            List of chunks
        """
        ...


@runtime_checkable
class FixedSizeChunker(Protocol):
    """Protocol for fixed-size chunking implementations."""

    @property
    def name(self) -> str:
        """Chunker name for identification."""
        ...

    def chunk(
        self, content: str, chunk_size: int, overlap: int, config: dict[str, Any]
    ) -> list[Chunk]:
        """Chunk content into fixed-size pieces.

        Args:
            content: Content to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            config: Additional configuration options

        Returns:
            List of fixed-size chunks
        """
        ...


@runtime_checkable
class SemanticChunker(Protocol):
    """Protocol for semantic chunking implementations."""

    @property
    def name(self) -> str:
        """Chunker name for identification."""
        ...

    async def chunk(self, content: str, config: dict[str, Any]) -> list[Chunk]:
        """Chunk content based on semantic boundaries.

        Args:
            content: Content to chunk
            config: Configuration options (threshold, model, etc.)

        Returns:
            List of semantically coherent chunks
        """
        ...
