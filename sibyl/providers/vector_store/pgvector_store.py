"""PostgreSQL with pgvector extension vector store implementation.

This module provides a VectorStoreProvider implementation using PostgreSQL
with the pgvector extension for efficient vector similarity search.

Dependencies:
    - psycopg2-binary or psycopg (psycopg3)
    - PostgreSQL with pgvector extension installed

Example:
    >>> from sibyl.providers.vector_store import PgVectorStore
    >>> store = PgVectorStore(
    ...     dsn="postgresql://user:pass@localhost:5432/mydb",
    ...     table="embeddings",
    ...     embedding_dim=384
    ... )
    >>> store.upsert([VectorRecord(id="doc1", embedding=[0.1]*384, metadata={"title": "Test"})])
    >>> results = store.search(query_embedding=[0.1]*384, limit=5)
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from sibyl.core.protocols.infrastructure.data_providers import (
    VectorRecord,
    VectorSearchResult,
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


class PgVectorStore:
    """Vector store implementation using PostgreSQL with pgvector extension.

    This implementation leverages PostgreSQL's pgvector extension for efficient
    vector similarity search using cosine distance, L2 distance, or inner product.

    Features:
    - Efficient vector similarity search using specialized indexes (IVFFlat, HNSW)
    - JSONB metadata storage for flexible filtering
    - Transaction support and ACID guarantees
    - Upsert operations with conflict resolution

    Args:
        dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db")
        table: Table name for storing vectors (default: "embeddings")
        embedding_dim: Dimension of embedding vectors (default: 1536)
        distance_metric: Distance metric to use - "cosine", "l2", or "inner_product" (default: "cosine")
        auto_create_table: Whether to automatically create table if it doesn't exist (default: True)

    Raises:
        ImportError: If psycopg2 is not installed
        psycopg2.Error: If connection or table creation fails
    """

    def __init__(
        self,
        dsn: str,
        table: str = "embeddings",
        embedding_dim: int = 1536,
        distance_metric: str = "cosine",
        auto_create_table: bool = True,
    ) -> None:
        if not PSYCOPG2_AVAILABLE:
            msg = (
                "psycopg2 is required for PgVectorStore. "
                "Install it with: pip install psycopg2-binary"
            )
            raise ImportError(msg)

        # Validate table name before using it
        _validate_table_name(table)

        self.dsn = dsn
        self.table = table
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        self._conn = None

        # Map distance metric to pgvector operator
        self._distance_ops = {
            "cosine": "<=>",  # Cosine distance
            "l2": "<->",  # L2 distance (Euclidean)
            "inner_product": "<#>",  # Negative inner product
        }

        if distance_metric not in self._distance_ops:
            msg = (
                f"Invalid distance_metric: {distance_metric}. "
                f"Must be one of: {list(self._distance_ops.keys())}"
            )
            raise ValueError(msg)

        logger.info(
            f"Initializing PgVectorStore: table={table}, dim={embedding_dim}, "
            f"metric={distance_metric}"
        )

        if auto_create_table:
            self._init_db()

    def _get_connection(self) -> Any:
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.dsn)
        return self._conn

    def _init_db(self) -> None:
        """Initialize database with pgvector extension and create table if needed."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # Create table with vector column
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    id TEXT PRIMARY KEY,
                    embedding vector({self.embedding_dim}),
                    metadata JSONB DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
                cur.execute(create_table_sql)

                # Create index for vector similarity search
                # Using IVFFlat index - good balance of performance and accuracy
                # For HNSW index (faster but more memory): USING hnsw (embedding vector_cosine_ops)
                index_name = f"{self.table}_embedding_idx"
                distance_op = "cosine" if self.distance_metric == "cosine" else "l2"

                # Check if index exists (using parameterized query)
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = %s AND indexname = %s
                    );
                    """,
                    (self.table, index_name),
                )
                index_exists = cur.fetchone()[0]

                if not index_exists:
                    create_index_sql = f"""
                    CREATE INDEX {index_name}
                    ON {self.table}
                    USING ivfflat (embedding vector_{distance_op}_ops)
                    WITH (lists = 100);
                    """
                    cur.execute(create_index_sql)
                    logger.info("Created IVFFlat index on %s.embedding", self.table)

                conn.commit()
                logger.info("Database initialized: table '%s' ready", self.table)

        except Exception as e:
            logger.exception("Failed to initialize database: %s", e)
            if self._conn:
                self._conn.rollback()
            raise

    def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or update vector records.

        Uses PostgreSQL's ON CONFLICT DO UPDATE for efficient upserts.

        Args:
            records: List of VectorRecord objects to insert or update

        Raises:
            psycopg2.Error: If database operation fails
        """
        if not records:
            return

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Prepare data for bulk insert
                values = [
                    (
                        r.id,
                        json.dumps(r.embedding),  # Convert list to JSON for vector type
                        json.dumps(r.metadata),
                        r.timestamp or datetime.utcnow(),
                    )
                    for r in records
                ]

                # Upsert query with conflict resolution
                # Safe: table name validated in __init__ via _validate_table_name()
                upsert_sql = f"""
                INSERT INTO {self.table} (id, embedding, metadata, created_at)
                VALUES %s
                ON CONFLICT (id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    created_at = EXCLUDED.created_at;
                """

                execute_values(
                    cur,
                    upsert_sql,
                    values,
                    template="(%s, %s::vector, %s::jsonb, %s)",
                )

                conn.commit()
                logger.debug("Upserted %s records to %s", len(records), self.table)

        except Exception as e:
            logger.exception("Failed to upsert records: %s", e)
            if self._conn:
                self._conn.rollback()
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
            min_score: Minimum similarity score (0.0-1.0). For cosine distance,
                      score is converted to similarity (1 - distance)

        Returns:
            List of VectorSearchResult objects sorted by score (descending)

        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                distance_op = self._distance_ops[self.distance_metric]

                # For cosine distance, convert to similarity: 1 - distance
                # For L2 distance, use negative distance as score
                if self.distance_metric == "cosine":
                    score_expr = f"1 - (embedding {distance_op} %s::vector)"
                elif self.distance_metric == "l2":
                    score_expr = f"1 / (1 + (embedding {distance_op} %s::vector))"
                else:  # inner_product
                    score_expr = f"-(embedding {distance_op} %s::vector)"

                # Safe: table name validated in __init__ via _validate_table_name()
                search_sql = f"""
                SELECT
                    id,
                    embedding,
                    metadata,
                    {score_expr} as score
                FROM {self.table}
                WHERE {score_expr} >= %s
                ORDER BY embedding {distance_op} %s::vector
                LIMIT %s;
                """

                query_json = json.dumps(query_embedding)
                cur.execute(search_sql, (query_json, min_score, query_json, limit))

                rows = cur.fetchall()

                results = [
                    VectorSearchResult(
                        id=row["id"],
                        score=float(row["score"]),
                        metadata=row["metadata"] or {},
                        embedding=row["embedding"] if row["embedding"] else None,
                    )
                    for row in rows
                ]

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
        combining vector, keyword, and graph search is not implemented.

        This implementation supports:
        - Metadata filtering using JSONB operators
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
            "Use search() with pre-computed query embeddings instead."
        )
        raise NotImplementedError(msg)

    def delete(self, ids: list[str]) -> int:
        """Delete records by ID.

        Args:
            ids: List of record IDs to delete

        Returns:
            Number of records actually deleted

        Raises:
            psycopg2.Error: If database operation fails
        """
        if not ids:
            return 0

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Safe: table name validated in __init__ via _validate_table_name()
                delete_sql = f"""
                DELETE FROM {self.table}
                WHERE id = ANY(%s);
                """

                cur.execute(delete_sql, (ids,))
                deleted_count = cur.rowcount

                conn.commit()
                logger.debug("Deleted %s records from %s", deleted_count, self.table)
                return deleted_count

        except Exception as e:
            logger.exception("Failed to delete records: %s", e)
            if self._conn:
                self._conn.rollback()
            raise

    def get_stats(self) -> VectorStoreStats:
        """Get vector store statistics.

        Returns:
            VectorStoreStats with total_records, dimension, and index_type

        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total record count
                # Safe: table name validated in __init__ via _validate_table_name()
                cur.execute(f"SELECT COUNT(*) as count FROM {self.table};")
                count = cur.fetchone()["count"]

                # Get index information (using parameterized query)
                cur.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s AND indexdef LIKE '%%ivfflat%%';
                    """,
                    (self.table,),
                )
                index_row = cur.fetchone()
                index_type = "ivfflat" if index_row else "none"

                return VectorStoreStats(
                    total_records=count,
                    dimension=self.embedding_dim,
                    index_type=index_type,
                )

        except Exception as e:
            logger.exception("Failed to get stats: %s", e)
            raise

    def close(self) -> None:
        """Close database connection.

        Should be called when done using the store to free resources.
        """
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.debug("Database connection closed")

    def __enter__(self) -> Any:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - closes connection."""
        self.close()
