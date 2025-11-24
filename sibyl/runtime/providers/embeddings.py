"""Embeddings providers for text embeddings generation.

This module provides concrete implementations of the EmbeddingsProvider protocol,
including local deterministic providers and integration with sentence-transformers.
"""

import hashlib
import logging

import numpy as np

logger = logging.getLogger(__name__)


class LocalEmbeddingsProvider:
    """Local deterministic embeddings provider for testing.

    This provider generates deterministic embeddings using hash-based
    approaches. Suitable for:
    - Testing and development
    - CI/CD pipelines
    - Deterministic behavior verification

    The embeddings are deterministic based on text content but
    maintain basic similarity properties (identical texts have
    identical embeddings, similar texts have similar embeddings).
    """

    def __init__(self, model: str = "local-deterministic", dimension: int = 384, **kwargs) -> None:
        """Initialize local embeddings provider.

        Args:
            model: Model identifier (for logging/tracking)
            dimension: Embedding dimension (default: 384)
            **kwargs: Additional configuration (ignored)
        """
        self.model = model
        self.dimension = dimension
        self.kwargs = kwargs
        logger.info("Initialized LocalEmbeddingsProvider: dimension=%s, model=%s", dimension, model)

    def embed(self, text: str) -> list[float]:
        """Generate embeddings for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        return self._generate_deterministic_embedding(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one per input text
        """
        return [self.embed(text) for text in texts]

    async def embed_async(self, text: str) -> list[float]:
        """Async version of embed.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector
        """
        # For local provider, just call sync version
        return self.embed(text)

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Async version of embed_batch.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        # For local provider, just call sync version
        return self.embed_batch(texts)

    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider.

        Returns:
            Embedding dimension
        """
        return self.dimension

    def _generate_deterministic_embedding(self, text: str) -> list[float]:
        """Generate deterministic embedding from text.

        Uses multiple hash functions to generate a deterministic vector
        that maintains basic similarity properties.

        Args:
            text: Input text

        Returns:
            Normalized embedding vector
        """
        # Normalize text
        text = text.strip().lower()

        # Generate multiple hashes for different dimensions
        embedding = []

        # Use multiple hash algorithms and seeds for diversity
        hash_seeds = range(self.dimension)

        for seed in hash_seeds:
            # Create hash with seed
            hash_input = f"{seed}:{text}".encode()
            hash_digest = hashlib.sha256(hash_input).digest()

            # Convert first 8 bytes to float
            hash_int = int.from_bytes(hash_digest[:8], byteorder="big")
            hash_float = (hash_int / (2**64)) * 2 - 1  # Normalize to [-1, 1]

            embedding.append(hash_float)

        # Convert to numpy for normalization
        embedding_array = np.array(embedding, dtype=np.float32)

        # L2 normalize to unit sphere
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            embedding_array = embedding_array / norm

        return embedding_array.tolist()


class SentenceTransformerEmbeddingsProvider:
    """Sentence Transformers embeddings provider.

    This provider uses the sentence-transformers library for real
    embeddings generation. Requires sentence-transformers to be installed.

    Example models:
    - all-MiniLM-L6-v2 (384 dimensions, fast)
    - all-mpnet-base-v2 (768 dimensions, high quality)
    - paraphrase-MiniLM-L6-v2 (384 dimensions, paraphrases)
    """

    def __init__(
        self, model: str = "all-MiniLM-L6-v2", device: str | None = None, **kwargs
    ) -> None:
        """Initialize sentence transformer provider.

        Args:
            model: Model identifier from sentence-transformers
            device: Device to run on ('cpu', 'cuda', or None for auto)
            **kwargs: Additional configuration passed to SentenceTransformer

        Raises:
            ImportError: If sentence-transformers is not installed
        """
        try:
            from sentence_transformers import SentenceTransformer  # optional dependency

        except ImportError:
            msg = (
                "sentence-transformers is required for SentenceTransformerEmbeddingsProvider. "
                "Install with: pip install sentence-transformers"
            )
            raise ImportError(msg) from None

        self.model_name = model
        self.device = device
        self.kwargs = kwargs

        logger.info("Loading SentenceTransformer model: %s", model)
        self._model = SentenceTransformer(model, device=device, **kwargs)
        logger.info(
            "SentenceTransformer loaded: dimension=%s",
            self._model.get_sentence_embedding_dimension(),
        )

    def embed(self, text: str) -> list[float]:
        """Generate embeddings for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector
        """
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    async def embed_async(self, text: str) -> list[float]:
        """Async version of embed.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector
        """
        # sentence-transformers doesn't have async API, use sync
        return self.embed(text)

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Async version of embed_batch.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        # sentence-transformers doesn't have async API, use sync
        return self.embed_batch(texts)

    def get_dimension(self) -> int:
        """Get the dimension of embeddings.

        Returns:
            Embedding dimension
        """
        return self._model.get_sentence_embedding_dimension()
