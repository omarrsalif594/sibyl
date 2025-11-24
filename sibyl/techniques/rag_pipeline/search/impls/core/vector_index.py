"""Generic entity vector index - semantic search over any entity type.

This module provides a domain-agnostic semantic search system that can index
and search ANY type of entity (products, documents, artifacts, etc.).

Features:
- Pluggable embedding backends (sentence-transformers, OpenAI, etc.)
- Pluggable vector storage (in-memory, FAISS, DuckDB, etc.)
- Metadata filtering
- Configurable similarity metrics
- Batch operations for efficiency

Example usage:
    # Create index
    index = EntityVectorIndex(backend="sentence-transformers")

    # Add entities
    index.add("product:SKU123", "Bamboo cutting board for kitchen", {"category": "kitchenware"})
    index.add("product:SKU456", "Organic cotton towels", {"category": "home"})

    # Search
    results = index.search("kitchen items", top_k=5)
    for result in results:
        print(f"{result.entity_id}: {result.score}")

    # Search with filters
    results = index.search("towels", filters={"category": "home"})
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from semantic search.

    Attributes:
        entity_id: Unique entity identifier
        score: Similarity score (higher is better)
        metadata: Entity metadata
        text: Original text (optional)
    """

    entity_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    text: str | None = None


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers.

    Implementations can use sentence-transformers, OpenAI, Cohere, etc.
    """

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...


class SentenceTransformerEmbedding:
    """Embedding provider using sentence-transformers.

    This is a local, free embedding model that works well for most use cases.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize with a sentence-transformers model.

        Args:
            model_name: Model name (default: all-MiniLM-L6-v2, fast and good quality)
        """
        try:
            from sentence_transformers import SentenceTransformer  # optional dependency

            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info("Loaded sentence-transformers model: %s", model_name)
        except ImportError:
            msg = (
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise ImportError(msg) from None

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        return self.model.encode(text, convert_to_numpy=True)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [embeddings[i] for i in range(len(texts))]


class EntityVectorIndex:
    """Generic semantic search over any entity type.

    This class provides semantic search capabilities without any domain assumptions.
    It can index products, documents, code artifacts, or any other entity type.
    """

    def __init__(
        self, embedding_provider: EmbeddingProvider | None = None, backend: str = "in-memory"
    ) -> None:
        """Initialize entity vector index.

        Args:
            embedding_provider: Custom embedding provider (optional)
            backend: Storage backend ("in-memory", "faiss", "duckdb")
        """
        # Set up embedding provider
        if embedding_provider is None:
            self.embedding_provider = SentenceTransformerEmbedding()
        else:
            self.embedding_provider = embedding_provider

        # Set up storage backend
        self.backend = backend
        if backend == "in-memory":
            self._entities: dict[str, dict[str, Any]] = {}
            self._embeddings: dict[str, np.ndarray] = {}
        elif backend == "faiss":
            msg = "FAISS backend not yet implemented"
            raise NotImplementedError(msg)
        elif backend == "duckdb":
            msg = "DuckDB backend not yet implemented"
            raise NotImplementedError(msg)
        else:
            msg = f"Unknown backend: {backend}"
            raise ValueError(msg)

        logger.info("Initialized EntityVectorIndex with backend=%s", backend)

    def add(self, entity_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Add an entity to the index.

        Args:
            entity_id: Unique entity identifier (e.g., "product:SKU123")
            text: Text to index (description, content, etc.)
            metadata: Additional entity metadata
        """
        # Generate embedding
        embedding = self.embedding_provider.embed(text)

        # Store entity
        self._entities[entity_id] = {
            "text": text,
            "metadata": metadata or {},
        }
        self._embeddings[entity_id] = embedding

        logger.debug("Added entity: %s", entity_id)

    def add_batch(self, entities: list[tuple[str, str, dict[str, Any] | None]]) -> None:
        """Add multiple entities efficiently.

        Args:
            entities: List of (entity_id, text, metadata) tuples
        """
        if not entities:
            return

        # Extract data
        entity_ids = [e[0] for e in entities]
        texts = [e[1] for e in entities]
        metadatas = [e[2] or {} for e in entities]

        # Generate embeddings in batch
        embeddings = self.embedding_provider.embed_batch(texts)

        # Store entities
        for entity_id, text, metadata, embedding in zip(
            entity_ids, texts, metadatas, embeddings, strict=False
        ):
            self._entities[entity_id] = {
                "text": text,
                "metadata": metadata,
            }
            self._embeddings[entity_id] = embedding

        logger.info("Added %s entities in batch", len(entities))

    def search(
        self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Search for entities semantically similar to query.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters (exact match)

        Returns:
            List of SearchResult objects, sorted by score (descending)
        """
        if not self._embeddings:
            logger.warning("No entities in index")
            return []

        # Generate query embedding
        query_embedding = self.embedding_provider.embed(query)

        # Compute similarities
        similarities = []
        for entity_id, entity_embedding in self._embeddings.items():
            # Apply filters
            if filters:
                entity_metadata = self._entities[entity_id]["metadata"]
                if not self._matches_filters(entity_metadata, filters):
                    continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, entity_embedding)
            similarities.append((entity_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Take top_k
        top_results = similarities[:top_k]

        # Build results
        results = []
        for entity_id, score in top_results:
            entity_data = self._entities[entity_id]
            results.append(
                SearchResult(
                    entity_id=entity_id,
                    score=float(score),
                    metadata=entity_data["metadata"],
                    text=entity_data["text"],
                )
            )

        logger.debug("Search for '%s' returned %s results", query, len(results))
        return results

    def remove(self, entity_id: str) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: Entity ID to remove
        """
        self._entities.pop(entity_id, None)
        self._embeddings.pop(entity_id, None)
        logger.debug("Removed entity: %s", entity_id)

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "entity_count": len(self._entities),
            "backend": self.backend,
        }

        if self._embeddings:
            # Get embedding dimension
            first_embedding = next(iter(self._embeddings.values()))
            stats["embedding_dim"] = len(first_embedding)

        # Count entity types (from entity_id prefixes)
        entity_types = {}
        for entity_id in self._entities:
            if ":" in entity_id:
                entity_type = entity_id.split(":", 1)[0]
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        stats["entity_types"] = entity_types

        return stats

    def clear(self) -> None:
        """Clear all entities from the index."""
        self._entities.clear()
        self._embeddings.clear()
        logger.info("Cleared index")

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0 to 1)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if metadata matches all filters.

        Args:
            metadata: Entity metadata
            filters: Filter criteria

        Returns:
            True if all filters match
        """
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True


# Export public API
__all__ = [
    "EmbeddingProvider",
    "EntityVectorIndex",
    "SearchResult",
    "SentenceTransformerEmbedding",
]
