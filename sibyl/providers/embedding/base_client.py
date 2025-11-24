"""Base embedding client with common functionality."""

from abc import ABC, abstractmethod

import numpy as np


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients."""

    def __init__(self, provider_name: str, **kwargs) -> None:
        """Initialize base embedding client.

        Args:
            provider_name: Provider identifier ("fastembed", "openai", etc.)
            **kwargs: Provider-specific config
        """
        self.provider_name = provider_name
        self.config = kwargs

    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding vector dimension
        """

    @abstractmethod
    def _get_version(self) -> str:
        """Get provider SDK/library version.

        Returns:
            Version string
        """

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """

    def get_provider_info(self) -> dict:
        """Get provider information.

        Returns:
            Dictionary with provider metadata
        """
        return {
            "provider": self.provider_name,
            "version": self._get_version(),
            "dimension": self.get_dimension(),
            "config": self.config,
        }
