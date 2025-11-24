"""Qdrant vector store implementation.

This module provides a VectorStoreProvider implementation using Qdrant,
a cloud-native vector search engine optimized for high-performance similarity search.

Dependencies:
    - qdrant-client

Example:
    >>> from sibyl.providers.vector_store import QdrantVectorStore
    >>> # Local instance
    >>> store = QdrantVectorStore(
    ...     url="http://localhost:6333",
    ...     collection="documents",
    ...     dimension=384
    ... )
    >>> # Cloud instance with API key
    >>> store = QdrantVectorStore(
    ...     url="https://xyz.qdrant.io",
    ...     api_key="your-api-key",
    ...     collection="documents",
    ...     dimension=384
    ... )
    >>> store.upsert([VectorRecord(id="doc1", embedding=[0.1]*384, metadata={"title": "Test"})])
    >>> results = store.search(query_embedding=[0.1]*384, limit=5)
"""

import logging
from datetime import datetime
from typing import Any

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        SearchParams,
        VectorParams,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from sibyl.core.protocols.infrastructure.data_providers import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreStats,
)

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Vector store implementation using Qdrant.

    Qdrant is a high-performance vector search engine with:
    - Fast similarity search using HNSW algorithm
    - Flexible payload filtering
    - Distributed architecture for scalability
    - Support for multiple distance metrics

    Features:
    - Cosine, Euclidean, and Dot product similarity
    - JSON-based payload storage with filtering
    - Efficient indexing with HNSW
    - Local and cloud deployment support

    Args:
        url: Qdrant server URL (e.g., "http://localhost:6333" or "https://xyz.qdrant.io")
        api_key: Optional API key for authentication (required for cloud instances)
        collection: Collection name for storing vectors (default: "documents")
        dimension: Dimension of embedding vectors (default: 384)
        distance_metric: Distance metric - "cosine", "euclidean", or "dot" (default: "cosine")
        auto_create_collection: Whether to create collection if it doesn't exist (default: True)

    Raises:
        ImportError: If qdrant-client is not installed
        Exception: If connection or collection creation fails
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        collection: str = "documents",
        dimension: int = 384,
        distance_metric: str = "cosine",
        auto_create_collection: bool = True,
    ) -> None:
        if not QDRANT_AVAILABLE:
            msg = (
                "qdrant-client is required for QdrantVectorStore. "
                "Install it with: pip install qdrant-client"
            )
            raise ImportError(msg)

        self.url = url
        self.collection = collection
        self.dimension = dimension
        self.distance_metric = distance_metric

        # Map distance metric to Qdrant Distance enum
        self._distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT,
        }

        if distance_metric not in self._distance_map:
            msg = (
                f"Invalid distance_metric: {distance_metric}. "
                f"Must be one of: {list(self._distance_map.keys())}"
            )
            raise ValueError(msg)

        logger.info(
            f"Initializing QdrantVectorStore: collection={collection}, "
            f"dim={dimension}, metric={distance_metric}"
        )

        # Initialize Qdrant client
        self.client = QdrantClient(url=url, api_key=api_key)

        if auto_create_collection:
            self._init_collection()

    def _init_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection not in collection_names:
                # Create collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=self._distance_map[self.distance_metric],
                    ),
                )
                logger.info("Created Qdrant collection: %s", self.collection)
            else:
                logger.debug("Collection %s already exists", self.collection)

        except Exception as e:
            logger.exception("Failed to initialize collection: %s", e)
            raise

    def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or update vector records.

        Qdrant automatically handles upserts - if a point with the same ID exists,
        it will be updated; otherwise, it will be inserted.

        Args:
            records: List of VectorRecord objects to insert or update

        Raises:
            Exception: If Qdrant operation fails
        """
        if not records:
            return

        try:
            # Convert VectorRecord to Qdrant PointStruct
            points = []
            for record in records:
                # Qdrant requires UUID or integer IDs internally, but we can use payload
                # Generate numeric ID from string ID
                point_id = abs(hash(record.id)) % (10**10)

                # Include original ID in payload
                payload = dict(record.metadata)
                payload["_id"] = record.id
                payload["_timestamp"] = (
                    record.timestamp.isoformat()
                    if record.timestamp
                    else datetime.utcnow().isoformat()
                )

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=record.embedding,
                        payload=payload,
                    )
                )

            # Upsert points to collection
            self.client.upsert(
                collection_name=self.collection,
                points=points,
            )

            logger.debug("Upserted %s records to %s", len(records), self.collection)

        except Exception as e:
            logger.exception("Failed to upsert records: %s", e)
            raise

    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        """Perform vector similarity search.

        Searches for vectors similar to the query embedding using the configured
        distance metric. Returns results sorted by similarity (highest first).

        Args:
            query_embedding: Query vector to search for
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of VectorSearchResult objects sorted by score (descending)

        Raises:
            Exception: If Qdrant operation fails
        """
        try:
            # Perform search
            search_result = self.client.search(
                collection_name=self.collection,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score if min_score > 0.0 else None,
            )

            # Convert Qdrant results to VectorSearchResult
            results = []
            for hit in search_result:
                payload = hit.payload or {}
                # Extract original ID from payload
                original_id = payload.pop("_id", str(hit.id))
                payload.pop("_timestamp", None)  # Remove internal timestamp

                results.append(
                    VectorSearchResult(
                        id=original_id,
                        score=hit.score,
                        metadata=payload,
                        embedding=hit.vector if hasattr(hit, "vector") else None,
                    )
                )

            logger.debug("Found %s results for search query", len(results))
            return results

        except Exception as e:
            logger.exception("Failed to search vectors: %s", e)
            raise

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search with metadata filters.

        Note: This is a simplified implementation for DC3. Full hybrid search
        combining vector, keyword, and graph search requires additional components.

        This implementation supports:
        - Metadata filtering using Qdrant's filter system
        - Vector similarity search

        Args:
            query: Query string (requires embedding provider to convert to vector)
            limit: Maximum number of results
            weights: Not used in this implementation
            filters: Optional metadata filters (e.g., {"source": "docs", "year": 2024})

        Returns:
            List of result dictionaries with id, score, and metadata

        Raises:
            NotImplementedError: This simplified implementation requires pre-computed embeddings
        """
        msg = (
            "Hybrid search requires an embeddings provider. "
            "Use search() with pre-computed query embeddings instead. "
            "For metadata filtering, use search_with_filter()."
        )
        raise NotImplementedError(msg)

    def search_with_filter(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Perform vector search with metadata filtering.

        This is a Qdrant-specific extension that supports metadata filtering
        during vector search.

        Args:
            query_embedding: Query vector to search for
            limit: Maximum number of results to return
            min_score: Minimum similarity score (0.0-1.0)
            filters: Metadata filters (e.g., {"source": "docs", "year": 2024})

        Returns:
            List of VectorSearchResult objects sorted by score (descending)

        Raises:
            Exception: If Qdrant operation fails
        """
        try:
            # Build Qdrant filter from dict
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)

            # Perform search with filter
            search_result = self.client.search(
                collection_name=self.collection,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=limit,
                score_threshold=min_score if min_score > 0.0 else None,
            )

            # Convert results
            results = []
            for hit in search_result:
                payload = hit.payload or {}
                original_id = payload.pop("_id", str(hit.id))
                payload.pop("_timestamp", None)

                results.append(
                    VectorSearchResult(
                        id=original_id,
                        score=hit.score,
                        metadata=payload,
                        embedding=hit.vector if hasattr(hit, "vector") else None,
                    )
                )

            logger.debug("Found %s filtered results", len(results))
            return results

        except Exception as e:
            logger.exception("Failed to search with filter: %s", e)
            raise

    def delete(self, ids: list[str]) -> int:
        """Delete records by ID.

        Args:
            ids: List of record IDs to delete (original string IDs)

        Returns:
            Number of records deleted

        Raises:
            Exception: If Qdrant operation fails
        """
        if not ids:
            return 0

        try:
            # Convert string IDs to numeric point IDs
            point_ids = [abs(hash(id_str)) % (10**10) for id_str in ids]

            # Delete points
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.PointIdsList(
                    points=point_ids,
                ),
            )

            logger.debug("Deleted %s records from %s", len(ids), self.collection)
            return len(ids)

        except Exception as e:
            logger.exception("Failed to delete records: %s", e)
            raise

    def get_stats(self) -> VectorStoreStats:
        """Get vector store statistics.

        Returns:
            VectorStoreStats with total_records, dimension, and index_type

        Raises:
            Exception: If Qdrant operation fails
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection)

            # Extract statistics
            total_records = collection_info.points_count or 0

            # Qdrant uses HNSW index by default
            index_type = "hnsw"

            return VectorStoreStats(
                total_records=total_records,
                dimension=self.dimension,
                index_type=index_type,
            )

        except Exception as e:
            logger.exception("Failed to get stats: %s", e)
            raise

    def close(self) -> None:
        """Close Qdrant client connection.

        Qdrant client automatically manages connections, but this method
        is provided for consistency with other store implementations.
        """
        if hasattr(self.client, "close"):
            self.client.close()
        logger.debug("Qdrant client closed")

    def __enter__(self) -> Any:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - closes connection."""
        self.close()
