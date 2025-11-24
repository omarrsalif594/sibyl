"""Embedding technique protocols and shared types.

This module defines the protocol interfaces and data structures for embedding operations.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Protocol for embedding implementations."""

    @property
    def name(self) -> str:
        """Implementation name for identification."""
        ...

    def embed(self, texts: list[str], config: dict[str, Any]) -> list[list[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            config: Configuration options

        Returns:
            List of embedding vectors
        """
        ...
