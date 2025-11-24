"""FastEmbed local embedding provider."""

import logging

import numpy as np

from sibyl.providers.embedding.base_client import BaseEmbeddingClient

logger = logging.getLogger(__name__)


class FastEmbedClient(BaseEmbeddingClient):
    """FastEmbed local embedding client."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        **kwargs,
    ) -> None:
        """Initialize FastEmbed client.

        Args:
            model_name: FastEmbed model name
            **kwargs: Additional config
        """
        super().__init__("fastembed", **kwargs)

        self.model_name = model_name
        self._model = None
        self._dimension = 384  # Default for all-MiniLM-L6-v2

    def _load_model(self) -> None:
        """Lazy-load FastEmbed model."""
        if self._model is None:
            try:
                from fastembed import TextEmbedding

                logger.info("Loading FastEmbed model: %s", self.model_name)
                self._model = TextEmbedding(model_name=self.model_name)
                logger.info("FastEmbed model loaded successfully")

                # Update dimension based on actual model
                # Generate a test embedding to get the dimension
                test_embedding = next(iter(self._model.embed(["test"])))
                self._dimension = len(test_embedding)
                logger.info("Embedding dimension: %s", self._dimension)

            except ImportError:
                msg = "FastEmbed not installed. Install with: pip install fastembed"
                raise ImportError(msg) from None

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding vector dimension
        """
        if self._model is None:
            self._load_model()
        return self._dimension

    def _get_version(self) -> str:
        """Get FastEmbed version.

        Returns:
            Version string
        """
        try:
            import fastembed

            return fastembed.__version__
        except (ImportError, AttributeError):
            return "unknown"

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        # FastEmbed's embed() always expects a list
        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self._model is None:
            self._load_model()

        # FastEmbed returns a generator, convert to list of numpy arrays
        embeddings = list(self._model.embed(texts))

        # Ensure we return numpy arrays
        return [np.array(emb, dtype=np.float32) for emb in embeddings]
