"""MCP adapter for embedding providers.

This adapter enables communication with MCP servers that provide embedding services.
"""

import logging

import numpy as np

from sibyl.providers.mcp.base import BaseMCPAdapter, MCPRequestError, MCPTimeoutError
from sibyl.providers.mcp.utils import MCPClient

logger = logging.getLogger(__name__)


class MCPEmbeddingAdapter(BaseMCPAdapter):
    """MCP adapter for embedding providers.

    This adapter implements the EmbeddingProvider protocol to communicate with
    MCP servers providing embedding services.
    """

    def __init__(
        self,
        provider_name: str,
        endpoint: str,
        embedding_dim: int,
        timeout_seconds: int = 30,
        **kwargs,
    ) -> None:
        """Initialize MCP embedding adapter.

        Args:
            provider_name: Provider identifier
            endpoint: MCP server endpoint URL
            embedding_dim: Expected embedding dimension
            timeout_seconds: Request timeout
            **kwargs: Additional configuration
        """
        super().__init__(provider_name, endpoint, timeout_seconds, **kwargs)
        self._client = MCPClient(endpoint, timeout_seconds)
        self._embedding_dim = embedding_dim

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        try:
            # Perform health check to verify connection
            await self.health_check()
            self._connected = True
            logger.info("Connected to MCP embedding server: %s", self.endpoint)
        except Exception as e:
            logger.exception("Failed to connect to MCP embedding server: %s", e)
            raise

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if self._client:
            await self._client.close()
        self._connected = False
        logger.info("Disconnected from MCP embedding server: %s", self.endpoint)

    async def health_check(self) -> bool:
        """Check if MCP server is healthy.

        Returns:
            True if server is healthy

        Raises:
            MCPConnectionError: If health check fails
        """
        try:
            response = await self._client.request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.exception("MCP health check failed: %s", e)
            raise

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        # Synchronous wrapper for async method
        import asyncio

        return asyncio.run(self._embed_async(text))

    async def _embed_async(self, text: str) -> np.ndarray:
        """Generate embedding for a single text (async).

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        embeddings = await self._embed_batch_async([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Synchronous wrapper for async method
        import asyncio

        return asyncio.run(self._embed_batch_async(texts))

    async def _embed_batch_async(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts (async).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            MCPRequestError: If request fails
            MCPTimeoutError: If request times out
        """
        if not texts:
            return []

        # Build MCP request
        request_data = {"texts": texts}

        try:
            # Make request to MCP server
            response = await self._client.request("POST", "/v1/embeddings", data=request_data)

            # Extract embeddings
            embeddings_data = response.get("embeddings", [])

            if len(embeddings_data) != len(texts):
                msg = f"Expected {len(texts)} embeddings, got {len(embeddings_data)}"
                raise MCPRequestError(msg)

            # Convert to numpy arrays
            embeddings = [np.array(emb, dtype=np.float32) for emb in embeddings_data]

            # Validate dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != self._embedding_dim:
                    msg = (
                        f"Expected embedding dimension {self._embedding_dim}, "
                        f"got {len(emb)} for text {i}"
                    )
                    raise MCPRequestError(msg)

            return embeddings

        except (MCPRequestError, MCPTimeoutError):
            raise
        except Exception as e:
            logger.exception("MCP embedding failed: %s", e)
            msg = f"Embedding failed: {e}"
            raise MCPRequestError(msg) from e

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding vector dimension
        """
        return self._embedding_dim
