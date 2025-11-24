"""DuckDB vector store provider implementation.

This module provides a vector store implementation using DuckDB,
supporting vector indexing and similarity search.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_table_name(name: str) -> None:
    """
    Validate table/collection name to prevent SQL injection.

    Args:
        name: Table or collection name to validate

    Raises:
        ValueError: If name contains invalid characters
    """
    if not name:
        msg = "Table name cannot be empty"
        raise ValueError(msg)

    # Allow only alphanumeric characters, underscores, and hyphens
    # Must start with a letter or underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
        msg = (
            f"Invalid table name '{name}'. "
            "Table names must start with a letter or underscore and contain only "
            "alphanumeric characters, underscores, and hyphens."
        )
        raise ValueError(msg)

    # Prevent reserved SQL keywords
    reserved_keywords = {
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "table",
        "from",
        "where",
        "join",
        "union",
        "order",
        "group",
        "having",
    }
    if name.lower() in reserved_keywords:
        msg = f"Table name '{name}' is a reserved SQL keyword"
        raise ValueError(msg)


class DuckDBVectorStoreProvider:
    """DuckDB-based vector store provider.

    This provider implements vector storage and retrieval using DuckDB.
    It supports:
    - Vector indexing with metadata
    - Similarity search (cosine similarity, dot product)
    - Filtering by metadata
    - Hybrid search (vector + keyword)

    Storage format:
    - Vectors are stored as FLOAT arrays in DuckDB
    - Metadata is stored as JSON strings
    - Each document has an ID, content, vector, and metadata
    """

    def __init__(
        self,
        dsn: str,
        collection_name: str = "vectors",
        distance_metric: str = "cosine",
        dimension: int | None = None,
        **kwargs,
    ) -> None:
        """Initialize DuckDB vector store provider.

        Args:
            dsn: DuckDB connection string (e.g., "duckdb://./data/vectors.duckdb")
            collection_name: Name of the collection/table
            distance_metric: Distance metric ("cosine", "euclidean", "dot")
            dimension: Vector dimension (will be detected if not provided)
            **kwargs: Additional configuration

        Raises:
            ValueError: If collection_name contains invalid characters
        """
        # Validate collection name to prevent SQL injection
        validate_table_name(collection_name)

        self.dsn = dsn
        self.collection_name = collection_name
        self.distance_metric = distance_metric
        self.dimension = dimension
        self.kwargs = kwargs

        # Parse DSN to get database path
        if dsn.startswith("duckdb://"):
            self.db_path = Path(dsn.replace("duckdb://", ""))
        else:
            self.db_path = Path(dsn)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self._conn = None
        self._initialize_db()

        logger.info(
            f"Initialized DuckDBVectorStoreProvider: "
            f"db={self.db_path}, collection={collection_name}, "
            f"metric={distance_metric}"
        )

    def _initialize_db(self) -> None:
        """Initialize database connection and schema."""
        import duckdb

        self._conn = duckdb.connect(str(self.db_path))

        # Create table if it doesn't exist
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id VARCHAR PRIMARY KEY,
                content TEXT,
                vector FLOAT[],
                metadata VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.debug("Initialized table: %s", self.collection_name)

    def index(
        self, documents: list[dict[str, Any]], embeddings: list[list[float]], batch_size: int = 1000
    ) -> int:
        """Index documents with their embeddings.

        Args:
            documents: List of documents with 'id', 'content', and 'metadata'
            embeddings: List of embedding vectors
            batch_size: Batch size for insertion

        Returns:
            Number of documents indexed
        """
        if len(documents) != len(embeddings):
            msg = f"Mismatch: {len(documents)} documents but {len(embeddings)} embeddings"
            raise ValueError(msg)

        if not documents:
            return 0

        # Detect dimension from first embedding
        if self.dimension is None:
            self.dimension = len(embeddings[0])
            logger.info("Detected embedding dimension: %s", self.dimension)

        # Prepare batch insertion
        indexed_count = 0

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            # Prepare values for batch insert
            values = []
            for doc, embedding in zip(batch_docs, batch_embeddings, strict=False):
                doc_id = doc.get("id", f"doc_{i}")
                content = doc.get("content", "")
                metadata = json.dumps(doc.get("metadata", {}))

                values.append((doc_id, content, embedding, metadata))

            # Insert batch
            # Safe: collection_name validated in __init__ via validate_table_name()
            self._conn.executemany(
                f"""
                INSERT OR REPLACE INTO {self.collection_name}
                (id, content, vector, metadata)
                VALUES (?, ?, ?, ?)
                """,
                values,
            )

            indexed_count += len(batch_docs)
            logger.debug("Indexed batch: %s documents", len(batch_docs))

        logger.info("Indexed %s documents total", indexed_count)
        return indexed_count

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> list[dict[str, Any]]:
        """Perform semantic vector search.

        Note: This method expects the query to be an embedding vector
        passed as a JSON string, or it will return empty results.

        For text queries, use hybrid_search() instead, or embed the
        query first using an embeddings provider.

        Args:
            query: Query (expected to be embedding vector as JSON string)
            limit: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of results with id, content, score, and metadata
        """
        try:
            # Try to parse query as embedding vector
            query_vector = json.loads(query)
            if not isinstance(query_vector, list):
                logger.warning("Query is not an embedding vector, returning empty results")
                return []
        except (json.JSONDecodeError, TypeError):
            logger.warning("Query cannot be parsed as JSON embedding, returning empty results")
            return []

        return self.search_by_vector(query_vector, limit, min_score)

    def search_by_vector(
        self,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search by embedding vector directly.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results
            min_score: Minimum similarity score
            filters: Optional metadata filters

        Returns:
            List of results with id, content, score, and metadata
        """
        # Calculate similarity based on metric
        if self.distance_metric == "cosine":
            similarity_expr = self._cosine_similarity_sql("vector", query_vector)
        elif self.distance_metric == "euclidean":
            similarity_expr = self._euclidean_similarity_sql("vector", query_vector)
        elif self.distance_metric == "dot":
            similarity_expr = self._dot_product_sql("vector", query_vector)
        else:
            similarity_expr = self._cosine_similarity_sql("vector", query_vector)

        # Build query
        # Safe: collection_name validated in __init__ via validate_table_name()
        query_sql = f"""
            SELECT
                id,
                content,
                metadata,
                {similarity_expr} as score
            FROM {self.collection_name}
            WHERE {similarity_expr} >= ?
            ORDER BY score DESC
            LIMIT ?
        """

        # Execute query
        results = self._conn.execute(query_sql, [min_score, limit]).fetchall()

        # Format results
        formatted_results = []
        for row in results:
            doc_id, content, metadata_json, score = row

            # Parse metadata
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                metadata = {}

            formatted_results.append(
                {
                    "model_id": doc_id,  # For compatibility with VectorProvider protocol
                    "id": doc_id,
                    "content": content,
                    "score": float(score),
                    "metadata": metadata,
                }
            )

        logger.debug("Found %s results for vector search", len(formatted_results))
        return formatted_results

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (vector + keyword).

        Note: For now, this performs keyword search only since we need
        an embeddings provider to convert text to vectors.

        Args:
            query: Natural language query
            limit: Maximum results
            weights: Weight dict (ignored for now)
            filters: Optional metadata filters

        Returns:
            List of results with combined scoring
        """
        # For now, perform simple keyword search
        # In a full implementation, this would combine vector + keyword + graph

        # Build keyword search query
        # Safe: collection_name validated in __init__ via validate_table_name()
        query_sql = f"""
            SELECT
                id,
                content,
                metadata,
                1.0 as score
            FROM {self.collection_name}
            WHERE content LIKE ?
            LIMIT ?
        """

        # Execute query
        search_pattern = f"%{query}%"
        results = self._conn.execute(query_sql, [search_pattern, limit]).fetchall()

        # Format results
        formatted_results = []
        for row in results:
            doc_id, content, metadata_json, score = row

            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                metadata = {}

            formatted_results.append(
                {
                    "model_id": doc_id,
                    "id": doc_id,
                    "content": content,
                    "score": float(score),
                    "metadata": metadata,
                }
            )

        logger.debug("Found %s results for hybrid search", len(formatted_results))
        return formatted_results

    def _cosine_similarity_sql(self, vector_col: str, query_vector: list[float]) -> str:
        """Generate SQL expression for cosine similarity.

        Args:
            vector_col: Name of vector column
            query_vector: Query vector

        Returns:
            SQL expression for cosine similarity
        """
        # Convert query vector to SQL array literal
        query_array = f"[{', '.join(map(str, query_vector))}]::FLOAT[]"

        # Cosine similarity formula: dot(a, b) / (norm(a) * norm(b))
        # Note: Using sqrt() instead of list_sqrt() for compatibility
        return f"""
            (list_dot_product({vector_col}, {query_array}) /
             (sqrt(list_dot_product({vector_col}, {vector_col})) *
              sqrt(list_dot_product({query_array}, {query_array}))))
        """

    def _euclidean_similarity_sql(self, vector_col: str, query_vector: list[float]) -> str:
        """Generate SQL expression for Euclidean similarity.

        Args:
            vector_col: Name of vector column
            query_vector: Query vector

        Returns:
            SQL expression (converted to similarity: 1 / (1 + distance))
        """
        query_array = f"[{', '.join(map(str, query_vector))}]::FLOAT[]"

        # Euclidean distance, converted to similarity
        # Note: Using sqrt() instead of list_sqrt() for compatibility
        return f"""
            (1.0 / (1.0 + sqrt(list_sum(
                list_transform(
                    list_zip({vector_col}, {query_array}),
                    x -> (x[1] - x[2]) * (x[1] - x[2])
                )
            ))))
        """

    def _dot_product_sql(self, vector_col: str, query_vector: list[float]) -> str:
        """Generate SQL expression for dot product.

        Args:
            vector_col: Name of vector column
            query_vector: Query vector

        Returns:
            SQL expression for dot product
        """
        query_array = f"[{', '.join(map(str, query_vector))}]::FLOAT[]"
        return f"list_dot_product({vector_col}, {query_array})"

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        # Get count
        # Safe: collection_name validated in __init__ via validate_table_name()
        result = self._conn.execute(f"SELECT COUNT(*) FROM {self.collection_name}").fetchone()

        total_docs = result[0] if result else 0

        return {
            "total_documents": total_docs,
            "collection_name": self.collection_name,
            "distance_metric": self.distance_metric,
            "dimension": self.dimension,
        }

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Closed DuckDB connection")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
