"""DuckDB vector store provider implementation.

This module provides a vector store implementation using DuckDB that follows
the DC1 VectorStoreProvider protocol. It builds upon the existing runtime
implementation while adding protocol compliance and enhanced features.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sibyl.core.protocols.infrastructure.data_providers import (
    VectorRecord,
    VectorStoreStats,
)

logger = logging.getLogger(__name__)


def _validate_table_name(table_name: str) -> None:
    """Validate table name to prevent SQL injection.

    Args:
        table_name: The table name to validate

    Raises:
        ValueError: If table name contains invalid characters
    """
    if not table_name:
        msg = "Table name cannot be empty"
        raise ValueError(msg)

    # Only allow alphanumeric characters, underscores, and hyphens
    # Must start with a letter or underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", table_name):
        msg = (
            f"Invalid table name '{table_name}'. "
            "Table names must start with a letter or underscore and "
            "contain only alphanumeric characters, underscores, and hyphens."
        )
        raise ValueError(msg)

    # Prevent SQL keywords and common injection patterns
    sql_keywords = {
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "truncate",
        "union",
        "exec",
        "execute",
    }
    if table_name.lower() in sql_keywords:
        msg = f"Table name '{table_name}' is a reserved SQL keyword"
        raise ValueError(msg)


class DuckDBVectorStore:
    """Vector store using DuckDB with VSS extension.

    This provider implements vector storage and retrieval using DuckDB,
    following the VectorStoreProvider protocol from DC1. It supports:
    - Vector indexing with metadata
    - Similarity search (cosine, euclidean, dot product)
    - Upsert and delete operations
    - Statistics and monitoring

    The implementation uses DuckDB's array types and list functions for
    vector operations. If the VSS extension is available, it will be used
    for optimized similarity search.

    Example:
        >>> store = DuckDBVectorStore(
        ...     path="./data/vectors.duckdb",
        ...     table="embeddings",
        ...     dimension=384
        ... )
        >>> records = [
        ...     VectorRecord(
        ...         id="doc1",
        ...         embedding=[0.1, 0.2, ...],
        ...         metadata={"source": "test"}
        ...     )
        ... ]
        >>> store.upsert(records)
        >>> results = store.search("[0.1, 0.2, ...]", limit=10)
    """

    def __init__(
        self,
        path: str,
        table: str = "embeddings",
        dimension: int = 384,
        distance_metric: str = "cosine",
        **kwargs,
    ) -> None:
        """Initialize DuckDB vector store.

        Args:
            path: Path to DuckDB database file
            table: Table name for storing vectors (default: "embeddings")
            dimension: Vector dimension (default: 384)
            distance_metric: Distance metric ("cosine", "euclidean", "dot")
            **kwargs: Additional configuration options

        Raises:
            ValueError: If table name is invalid or contains SQL injection patterns
        """
        # Validate table name before using it
        _validate_table_name(table)

        self.path = Path(path)
        self.table = table
        self.dimension = dimension
        self.distance_metric = distance_metric
        self.kwargs = kwargs

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self._conn = None
        self._init_db()

        logger.info(
            f"Initialized DuckDBVectorStore: db={self.path}, table={table}, "
            f"dimension={dimension}, metric={distance_metric}"
        )

    def _init_db(self) -> None:
        """Initialize database connection and schema."""
        import duckdb

        self._conn = duckdb.connect(str(self.path))

        # Try to load VSS extension if available
        try:
            self._conn.execute("INSTALL vss")
            self._conn.execute("LOAD vss")
            logger.info("DuckDB VSS extension loaded successfully")
        except Exception as e:
            logger.debug("VSS extension not available, using manual similarity: %s", e)

        # Create table with schema matching VectorRecord
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                id VARCHAR PRIMARY KEY,
                embedding FLOAT[],
                metadata VARCHAR,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.debug("Initialized table: %s", self.table)

    def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or update vector records.

        Args:
            records: List of VectorRecord objects to insert or update

        Raises:
            ValueError: If records have inconsistent dimensions
        """
        if not records:
            return

        # Validate dimensions
        for record in records:
            if len(record.embedding) != self.dimension:
                msg = (
                    f"Embedding dimension mismatch: expected {self.dimension}, "
                    f"got {len(record.embedding)} for record {record.id}"
                )
                raise ValueError(msg)

        # Prepare batch upsert
        for record in records:
            metadata_json = json.dumps(record.metadata)
            timestamp = record.timestamp or datetime.utcnow()

            # Safe: table name validated in __init__ via _validate_table_name()
            self._conn.execute(
                f"""
                INSERT OR REPLACE INTO {self.table}
                (id, embedding, metadata, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                [record.id, record.embedding, metadata_json, timestamp],
            )

        logger.debug("Upserted %s records", len(records))

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> list[dict[str, Any]]:
        """Perform semantic vector search.

        Note: This method expects the query to be an embedding vector
        passed as a JSON string. For DC2, we accept embedding directly.

        Args:
            query: Query embedding vector as JSON string (e.g., "[0.1, 0.2, ...]")
            limit: Maximum results
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of results with id, score, and metadata
        """
        try:
            # Parse query as embedding vector
            query_vector = json.loads(query)
            if not isinstance(query_vector, list):
                logger.warning("Query is not an embedding vector, returning empty results")
                return []
        except (json.JSONDecodeError, TypeError):
            logger.warning("Query cannot be parsed as JSON embedding, returning empty results")
            return []

        return self._search_by_vector(query_vector, limit, min_score)

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (vector + keyword + graph).

        For DC2, this implements basic keyword search. In a full implementation,
        this would combine vector similarity with keyword matching and graph
        traversal.

        Args:
            query: Natural language query
            limit: Maximum results
            weights: Weight dict (ignored for now)
            filters: Optional metadata filters

        Returns:
            List of results with combined scoring
        """
        # Basic keyword search implementation
        # In production, this would be enhanced with vector search
        # Safe: table name validated in __init__ via _validate_table_name()
        results = self._conn.execute(
            f"""
            SELECT id, embedding, metadata, 1.0 as score
            FROM {self.table}
            WHERE metadata LIKE ?
            LIMIT ?
            """,
            [f"%{query}%", limit],
        ).fetchall()

        formatted_results = []
        for row in results:
            doc_id, _embedding, metadata_json, score = row

            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                metadata = {}

            formatted_results.append(
                {
                    "model_id": doc_id,
                    "id": doc_id,
                    "score": float(score),
                    "metadata": metadata,
                }
            )

        logger.debug("Found %s results for hybrid search", len(formatted_results))
        return formatted_results

    def delete(self, ids: list[str]) -> int:
        """Delete records by ID.

        Args:
            ids: List of record IDs to delete

        Returns:
            Number of records deleted
        """
        if not ids:
            return 0

        # Build placeholders for parameterized query
        placeholders = ", ".join(["?"] * len(ids))
        # Safe: table name validated in __init__ via _validate_table_name()
        query = f"DELETE FROM {self.table} WHERE id IN ({placeholders})"

        cursor = self._conn.execute(query, ids)
        deleted = cursor.fetchone()[0] if cursor else 0

        logger.debug("Deleted %s records", deleted)
        return deleted

    def get_stats(self) -> VectorStoreStats:
        """Get store statistics.

        Returns:
            VectorStoreStats object with store information
        """
        # Get total record count
        # Safe: table name validated in __init__ via _validate_table_name()
        result = self._conn.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()
        total_records = result[0] if result else 0

        return VectorStoreStats(
            total_records=total_records,
            dimension=self.dimension,
            index_type=f"duckdb_{self.distance_metric}",
        )

    def _search_by_vector(
        self,
        query_vector: list[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search by embedding vector directly.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of results with id, score, and metadata
        """
        # Validate query vector dimension
        if len(query_vector) != self.dimension:
            msg = (
                f"Query vector dimension mismatch: expected {self.dimension}, "
                f"got {len(query_vector)}"
            )
            raise ValueError(msg)

        # Calculate similarity based on metric
        if self.distance_metric == "cosine":
            similarity_expr = self._cosine_similarity_sql("embedding", query_vector)
        elif self.distance_metric == "euclidean":
            similarity_expr = self._euclidean_similarity_sql("embedding", query_vector)
        elif self.distance_metric == "dot":
            similarity_expr = self._dot_product_sql("embedding", query_vector)
        else:
            similarity_expr = self._cosine_similarity_sql("embedding", query_vector)

        # Build and execute query
        # Safe: table name validated in __init__ via _validate_table_name()
        query_sql = f"""
            SELECT
                id,
                metadata,
                {similarity_expr} as score
            FROM {self.table}
            WHERE {similarity_expr} >= ?
            ORDER BY score DESC
            LIMIT ?
        """

        results = self._conn.execute(query_sql, [min_score, limit]).fetchall()

        # Format results
        formatted_results = []
        for row in results:
            doc_id, metadata_json, score = row

            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                metadata = {}

            formatted_results.append(
                {
                    "model_id": doc_id,
                    "id": doc_id,
                    "score": float(score),
                    "metadata": metadata,
                }
            )

        logger.debug("Found %s results for vector search", len(formatted_results))
        return formatted_results

    def _cosine_similarity_sql(self, vector_col: str, query_vector: list[float]) -> str:
        """Generate SQL expression for cosine similarity.

        Cosine similarity = dot(a, b) / (||a|| * ||b||)

        Args:
            vector_col: Name of vector column
            query_vector: Query vector

        Returns:
            SQL expression for cosine similarity
        """
        query_array = f"[{', '.join(map(str, query_vector))}]::FLOAT[]"

        return f"""
            (list_dot_product({vector_col}, {query_array}) /
             (sqrt(list_dot_product({vector_col}, {vector_col})) *
              sqrt(list_dot_product({query_array}, {query_array}))))
        """

    def _euclidean_similarity_sql(self, vector_col: str, query_vector: list[float]) -> str:
        """Generate SQL expression for Euclidean similarity.

        Converts Euclidean distance to similarity: 1 / (1 + distance)

        Args:
            vector_col: Name of vector column
            query_vector: Query vector

        Returns:
            SQL expression for Euclidean similarity
        """
        query_array = f"[{', '.join(map(str, query_vector))}]::FLOAT[]"

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

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Closed DuckDB connection")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
