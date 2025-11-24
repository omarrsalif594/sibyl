"""
Data Provider protocol interfaces for dependency inversion.

These protocols define the contracts for querying lineage, patterns, vectors, and caching.
Application services depend only on these interfaces, not concrete implementations.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LineageProvider(Protocol):
    """Abstract interface for lineage queries."""

    def get_downstream(
        self, model_id: str, depth: int, max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Get downstream dependencies of a model.

        Args:
            model_id: Model identifier
            depth: How many hops to traverse (1 = direct children)
            max_results: Optional limit on result count

        Returns:
            List of model nodes with metadata
        """
        ...

    def get_upstream(
        self, model_id: str, depth: int, max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Get upstream dependencies of a model.

        Args:
            model_id: Model identifier
            depth: How many hops to traverse (1 = direct parents)
            max_results: Optional limit on result count

        Returns:
            List of model nodes with metadata
        """
        ...

    def find_path(self, from_model: str, to_model: str, max_hops: int = 10) -> list[str] | None:
        """Find shortest path between two models.

        Args:
            from_model: Source model ID
            to_model: Target model ID
            max_hops: Maximum path length to search

        Returns:
            List of model IDs forming the path, or None if no path exists
        """
        ...

    def get_model_info(self, model_id: str) -> dict[str, Any] | None:
        """Get metadata for a single model.

        Args:
            model_id: Model identifier

        Returns:
            Model metadata dict or None if not found
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get pre-aggregated statistics about the lineage graph.

        Returns:
            Dict with keys: total_models, total_edges, avg_depth, etc.
        """
        ...


@runtime_checkable
class PatternProvider(Protocol):
    """Abstract interface for pattern queries."""

    def search_patterns(
        self, error_text: str, limit: int = 10, min_success_rate: float = 0.0
    ) -> list[dict[str, Any]]:
        """Search for patterns matching an error.

        Args:
            error_text: Error message or SQL fragment to match
            limit: Maximum number of patterns to return
            min_success_rate: Minimum success rate filter (0.0-1.0)

        Returns:
            List of pattern dicts with metadata
        """
        ...

    def get_pattern(self, pattern_id: int) -> dict[str, Any] | None:
        """Get full details of a specific pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern dict or None if not found
        """
        ...

    def record_application(
        self, pattern_id: int, model_id: str, successful: bool, notes: str | None = None
    ) -> None:
        """Record that a pattern was applied to a model.

        Args:
            pattern_id: Pattern that was applied
            model_id: Model it was applied to
            successful: Whether the fix worked
            notes: Optional notes about the application
        """
        ...

    def get_top_patterns(self, limit: int = 10, time_window_days: int = 30) -> list[dict[str, Any]]:
        """Get best-performing patterns by success rate.

        Args:
            limit: Maximum number of patterns
            time_window_days: Look back window for recency

        Returns:
            List of pattern dicts sorted by success rate
        """
        ...


@runtime_checkable
class VectorProvider(Protocol):
    """Abstract interface for vector search."""

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> list[dict[str, Any]]:
        """Perform semantic vector search.

        Args:
            query: Natural language query
            limit: Maximum results
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of results with model_id, score, and metadata
        """
        ...

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (vector + keyword + graph).

        Args:
            query: Natural language query
            limit: Maximum results
            weights: Weight dict with keys: vector, keyword, graph
            filters: Optional filters (e.g., {"source": "stripe"})

        Returns:
            List of results with combined scoring
        """
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """Abstract interface for caching with namespacing."""

    def get(self, namespace: str, key: str) -> Any | None:
        """Get cached value.

        Args:
            namespace: Cache namespace (e.g., "lineage", "patterns")
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        ...

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
        """Set cached value with TTL.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be pickle-able)
            ttl_seconds: Time to live in seconds
        """
        ...

    def invalidate(self, namespace: str, pattern: str | None = None) -> int:
        """Invalidate cached entries.

        Args:
            namespace: Cache namespace
            pattern: Optional glob pattern for keys (e.g., "model_*")
                     If None, invalidates entire namespace

        Returns:
            Number of entries invalidated
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, etc.
        """
        ...


@runtime_checkable
class EmbeddingsProvider(Protocol):
    """Abstract interface for text embeddings generation."""

    def embed(self, text: str) -> list[float]:
        """Generate embeddings for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            RateLimitError: Provider rate limit hit (429)
            TransientProviderError: Temporary provider error (5xx)
            ProviderError: Permanent provider error (4xx)
            TimeoutError: Request timeout exceeded
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one per input text

        Raises:
            Same as embed()
        """
        ...

    async def embed_async(self, text: str) -> list[float]:
        """Async version of embed.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector

        Raises:
            Same as embed()
        """
        ...

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Async version of embed_batch.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors

        Raises:
            Same as embed()
        """
        ...

    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider.

        Returns:
            Embedding dimension (e.g., 384, 768, 1536)
        """
        ...


@runtime_checkable
class VectorStoreProvider(Protocol):
    """Abstract interface for vector storage and retrieval.

    Note: This is an alias for VectorProvider for backward compatibility
    and clearer naming in the framework layer.
    """

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> list[dict[str, Any]]:
        """Perform semantic vector search.

        Args:
            query: Natural language query
            limit: Maximum results
            min_score: Minimum similarity score (0.0-1.0)

        Returns:
            List of results with model_id, score, and metadata
        """
        ...

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (vector + keyword + graph).

        Args:
            query: Natural language query
            limit: Maximum results
            weights: Weight dict with keys: vector, keyword, graph
            filters: Optional filters (e.g., {"source": "stripe"})

        Returns:
            List of results with combined scoring
        """
        ...

    def upsert(self, records: list["VectorRecord"]) -> None:
        """Insert or update vector records.

        Args:
            records: List of VectorRecord objects to insert or update
        """
        ...

    def delete(self, ids: list[str]) -> int:
        """Delete records by ID.

        Args:
            ids: List of record IDs to delete

        Returns:
            Number of records deleted
        """
        ...

    def get_stats(self) -> "VectorStoreStats":
        """Get store statistics.

        Returns:
            VectorStoreStats object with store information
        """
        ...


# Supporting dataclasses for DocumentSourceProvider


@dataclass
class DocumentMetadata:
    """Metadata for a document."""

    id: str
    uri: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Document:
    """A document with content and metadata."""

    id: str
    content: str
    metadata: dict[str, Any]
    uri: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


# Supporting dataclasses for VectorStoreProvider


@dataclass
class VectorRecord:
    """A vector record for storage."""

    id: str
    embedding: list[float]
    metadata: dict[str, Any]
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class VectorSearchResult:
    """A vector search result."""

    id: str
    score: float
    metadata: dict[str, Any]
    embedding: list[float] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class VectorStoreStats:
    """Vector store statistics."""

    total_records: int
    dimension: int
    index_type: str


# Supporting dataclasses for SQLDataProvider


@dataclass
class SQLResult:
    """Result from SQL query execution."""

    rows_affected: int
    last_insert_id: int | None = None
    rows: list[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.rows is None:
            self.rows = []


# New Protocol: DocumentSourceProvider


@runtime_checkable
class DocumentSourceProvider(Protocol):
    """Provider for document sources (filesystem, S3, databases, etc.)."""

    def list_documents(self, **filters) -> list[DocumentMetadata]:
        """List available documents with optional filtering.

        Args:
            **filters: Optional filters to apply (e.g., pattern="*.md", since=datetime)

        Returns:
            List of DocumentMetadata objects
        """
        ...

    def get_document(self, doc_id: str) -> Document:
        """Retrieve a specific document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document object with content and metadata

        Raises:
            KeyError: If document not found
        """
        ...

    def iterate_documents(self, **filters) -> Iterator[Document]:
        """Stream documents for processing.

        Args:
            **filters: Optional filters to apply

        Yields:
            Document objects one at a time
        """
        ...


# New Protocol: SQLDataProvider


@runtime_checkable
class SQLDataProvider(Protocol):
    """Provider for SQL database access."""

    def execute(self, query: str, params: dict | None = None) -> SQLResult:
        """Execute SQL query with parameterized values.

        Args:
            query: SQL query string
            params: Optional parameter dictionary for query

        Returns:
            SQLResult object with execution results

        Raises:
            Exception: Database-specific exceptions for query errors
        """
        ...

    def fetch_all(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute query and return all rows.

        Args:
            query: SQL query string
            params: Optional parameter dictionary for query

        Returns:
            List of row dictionaries

        Raises:
            Exception: Database-specific exceptions for query errors
        """
        ...

    async def execute_async(self, query: str, params: dict | None = None) -> SQLResult:
        """Async version of execute.

        Args:
            query: SQL query string
            params: Optional parameter dictionary for query

        Returns:
            SQLResult object with execution results

        Raises:
            Exception: Database-specific exceptions for query errors
        """
        ...
