"""OpenAI embeddings API provider."""

import logging
import os
from typing import Any

import numpy as np

from sibyl.providers.embedding.base_client import BaseEmbeddingClient

logger = logging.getLogger(__name__)


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """OpenAI embeddings API client."""

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        **kwargs,
    ) -> None:
        """Initialize OpenAI embeddings client.

        Args:
            api_key: OpenAI API key (or from OPENAI_API_KEY env)
            model: Embedding model to use
            **kwargs: Additional config
        """
        super().__init__("openai-embeddings", **kwargs)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            msg = "OpenAI API key required (pass api_key or set OPENAI_API_KEY)"
            raise ValueError(msg)

        self.model = model
        self._client = None

    def _get_client(self) -> Any:
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                msg = "openai SDK not installed. Install with: pip install openai"
                raise ImportError(msg) from None

        return self._client

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding vector dimension
        """
        return self.MODEL_DIMENSIONS.get(self.model, 1536)

    def _get_version(self) -> str:
        """Get OpenAI SDK version.

        Returns:
            Version string
        """
        try:
            import openai

            return openai.__version__
        except (ImportError, AttributeError):
            return "unknown"

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        client = self._get_client()

        try:
            response = client.embeddings.create(
                model=self.model,
                input=[text],
            )

            # Extract embedding from response
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)

        except Exception as e:
            logger.exception("Failed to generate embedding: %s", e)
            raise

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = self._get_client()

        try:
            # OpenAI supports batch embeddings
            response = client.embeddings.create(
                model=self.model,
                input=texts,
            )

            # Extract embeddings maintaining order
            return [np.array(item.embedding, dtype=np.float32) for item in response.data]

        except Exception as e:
            logger.exception("Failed to generate batch embeddings: %s", e)
            raise
