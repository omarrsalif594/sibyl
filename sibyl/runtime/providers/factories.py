"""Factory functions for creating provider instances.

This module provides factory functions that create concrete provider instances
from workspace configuration objects. These factories abstract away the details
of provider construction and allow for easy extension and testing.
"""

import logging
import os
from typing import Any, Never

from sibyl.core.protocols.infrastructure.data_providers import (
    EmbeddingsProvider,
    VectorStoreProvider,
)
from sibyl.core.protocols.infrastructure.llm import LLMProvider
from sibyl.workspace.schema import (
    EmbeddingsProviderConfig,
    LLMProviderConfig,
    VectorStoreConfig,
)

logger = logging.getLogger(__name__)


class MockLLMProvider:
    """Mock LLM provider for testing and development.

    This is a placeholder implementation that satisfies the LLMProvider protocol.
    Real implementations should be integrated from existing infrastructure.
    """

    def __init__(self, provider: str, model: str, api_key: str | None = None, **kwargs) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.kwargs = kwargs
        logger.info("Initialized MockLLMProvider: %s/%s", provider, model)

    def complete(self, prompt: str, options: Any) -> Never:
        msg = "MockLLMProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    async def complete_async(self, prompt: str, options: Any) -> Never:
        msg = "MockLLMProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    async def structured_complete(self, prompt: str, schema: dict, options: Any) -> Never:
        msg = "MockLLMProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    def complete_stream(self, prompt: str, options: Any) -> Never:
        msg = "MockLLMProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    def count_tokens(self, text: str, model: str) -> int:
        # Simple approximation: ~4 chars per token
        return len(text) // 4

    def get_features(self) -> Any:
        from sibyl.core.protocols.infrastructure.llm import ProviderFeatures

        return ProviderFeatures(
            supports_structured=False,
            supports_seed=False,
            supports_streaming=False,
            supports_tools=False,
            max_tokens_limit=4096,
            token_counting_method="estimate",  # S106 false positive: not a password
        )


class MockEmbeddingsProvider:
    """Mock embeddings provider for testing and development."""

    def __init__(self, provider: str, model: str, dimension: int = 384, **kwargs) -> None:
        self.provider = provider
        self.model = model
        self.dimension = dimension
        self.kwargs = kwargs
        logger.info("Initialized MockEmbeddingsProvider: %s/%s", provider, model)

    def embed(self, text: str) -> list[float]:
        msg = "MockEmbeddingsProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        msg = "MockEmbeddingsProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    async def embed_async(self, text: str) -> list[float]:
        msg = "MockEmbeddingsProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        msg = "MockEmbeddingsProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    def get_dimension(self) -> int:
        return self.dimension


class MockVectorStoreProvider:
    """Mock vector store provider for testing and development."""

    def __init__(self, kind: str, dsn: str, **kwargs) -> None:
        self.kind = kind
        self.dsn = dsn
        self.kwargs = kwargs
        logger.info("Initialized MockVectorStoreProvider: %s", kind)

    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> Never:
        msg = "MockVectorStoreProvider: Use real provider implementations"
        raise NotImplementedError(msg)

    def hybrid_search(
        self, query: str, limit: int = 10, weights: Any = None, filters: Any = None
    ) -> Never:
        msg = "MockVectorStoreProvider: Use real provider implementations"
        raise NotImplementedError(msg)


def create_llm_provider(config: LLMProviderConfig) -> LLMProvider:
    """Create an LLM provider instance from configuration.

    This factory function creates concrete LLM provider instances based on
    the provider type specified in the configuration. It handles API key
    resolution from environment variables and provider-specific initialization.

    Args:
        config: LLM provider configuration

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider type is not supported or configuration is invalid
        ImportError: If required provider implementation is not available
        KeyError: If required API key environment variable is not set

    Example:
        >>> config = LLMProviderConfig(
        ...     provider="openai",
        ...     model="gpt-4",
        ...     api_key_env="OPENAI_API_KEY"
        ... )
        >>> provider = create_llm_provider(config)
    """
    # Resolve API key from environment if specified
    api_key = None
    if config.api_key_env:
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            logger.warning(
                "API key environment variable '%s' not set for %s",
                config.api_key_env,
                config.provider,
            )

    # Build provider-specific kwargs
    kwargs: dict[str, Any] = {}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    if config.max_tokens:
        kwargs["max_tokens"] = config.max_tokens
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature

    provider_type = config.provider.lower()

    # OpenAI provider
    if provider_type == "openai":
        from sibyl.providers.llm.api.openai import OpenAIClient

        logger.info("Creating OpenAI LLM provider: %s", config.model)
        return OpenAIClient(
            model=config.model,
            api_key=api_key,
            base_url=config.base_url,
        )

    # Anthropic provider
    if provider_type == "anthropic":
        from sibyl.providers.llm.api.anthropic import AnthropicClient

        logger.info("Creating Anthropic LLM provider: %s", config.model)
        return AnthropicClient(
            model=config.model,
            api_key=api_key,
            base_url=config.base_url,
        )

    # MCP LLM provider
    if provider_type in {"mcp", "mcp_llm"}:
        from sibyl.providers.llm.mcp.mcp_adapter import MCPLLMAdapter

        if not config.base_url:
            msg = "MCP provider requires base_url (MCP server endpoint)"
            raise ValueError(msg)

        logger.info("Creating MCP LLM provider: %s/%s", config.base_url, config.model)
        return MCPLLMAdapter(
            endpoint=config.base_url,
            model=config.model,
        )

    # Fallback to mock for unknown providers (development/testing)
    logger.warning(
        f"Unknown provider type '{config.provider}', using mock implementation. "
        f"Supported types: openai, anthropic, mcp"
    )
    return MockLLMProvider(
        provider=config.provider,
        model=config.model,
        api_key=api_key,
        **kwargs,
    )


def create_embeddings_provider(config: EmbeddingsProviderConfig) -> EmbeddingsProvider:
    """Create an embeddings provider instance from configuration.

    Args:
        config: Embeddings provider configuration

    Returns:
        Configured embeddings provider instance

    Raises:
        ValueError: If provider type is not supported
        ImportError: If required provider implementation is not available

    Example:
        >>> config = EmbeddingsProviderConfig(
        ...     provider="local_sentence_transformer",
        ...     model="all-MiniLM-L6-v2",
        ...     dimension=384
        ... )
        >>> provider = create_embeddings_provider(config)
    """
    # Resolve API key from environment if specified
    api_key = None
    if config.api_key_env:
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            logger.warning(
                f"API key environment variable '{config.api_key_env}' not set for {config.provider}"
            )

    # TODO: Integrate with existing embeddings infrastructure
    logger.info(
        f"Creating embeddings provider: {config.provider}/{config.model} "
        f"(using mock implementation - integrate real providers)"
    )

    return MockEmbeddingsProvider(
        provider=config.provider,
        model=config.model,
        dimension=config.dimension or 384,
        api_key=api_key,
    )


def create_vector_store_provider(config: VectorStoreConfig) -> VectorStoreProvider:
    """Create a vector store provider instance from configuration.

    Supported vector stores:
    - pgvector: PostgreSQL with pgvector extension
    - qdrant: Qdrant vector search engine (local or cloud)
    - duckdb: DuckDB with vector support (handled by DC2)

    Args:
        config: Vector store configuration

    Returns:
        Configured vector store provider instance

    Raises:
        ValueError: If vector store kind is not supported
        ImportError: If required vector store implementation is not available

    Example:
        >>> # PostgreSQL with pgvector
        >>> config = VectorStoreConfig(
        ...     kind="pgvector",
        ...     dsn="postgresql://user:pass@localhost:5432/mydb",
        ...     collection_name="embeddings"
        ... )
        >>> provider = create_vector_store_provider(config)

        >>> # Qdrant
        >>> config = VectorStoreConfig(
        ...     kind="qdrant",
        ...     dsn="http://localhost:6333",
        ...     collection_name="documents"
        ... )
        >>> provider = create_vector_store_provider(config)
    """
    kind = config.kind.lower()

    logger.info("Creating vector store provider: %s at %s", kind, config.dsn)

    # pgvector: PostgreSQL with vector extension
    if kind == "pgvector":
        from sibyl.providers.vector_store.pgvector_store import PgVectorStore

        # Extract dimension from config if available
        # TODO: Better way to pass dimension through config
        dimension = getattr(config, "dimension", 1536)

        return PgVectorStore(
            dsn=config.dsn,
            table=config.collection_name or "embeddings",
            embedding_dim=dimension,
            distance_metric=config.distance_metric or "cosine",
            auto_create_table=True,
        )

    # Qdrant: Cloud-native vector search engine
    if kind == "qdrant":
        from sibyl.providers.vector_store.qdrant_store import QdrantVectorStore

        # Parse API key from environment if specified in DSN
        # Format: qdrant://api_key@host or http://host
        api_key = None
        url = config.dsn

        # Check for API key in environment variables
        api_key_env = getattr(config, "api_key_env", None)
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                logger.warning("API key environment variable '%s' not set", api_key_env)

        # Extract dimension from config if available
        dimension = getattr(config, "dimension", 384)

        return QdrantVectorStore(
            url=url,
            api_key=api_key,
            collection=config.collection_name or "documents",
            dimension=dimension,
            distance_metric=config.distance_metric or "cosine",
            auto_create_collection=True,
        )

    # DuckDB: Handled by DC2
    if kind == "duckdb":
        from sibyl.providers.vector_store.duckdb_store import DuckDBVectorStore

        # Parse DSN to extract path
        # Format: duckdb://./data/vectors.duckdb or just a file path
        if config.dsn.startswith("duckdb://"):
            db_path = config.dsn.replace("duckdb://", "")
        else:
            db_path = config.dsn

        # Extract dimension from config if available
        dimension = getattr(config, "dimension", 384)

        return DuckDBVectorStore(
            path=db_path,
            table=config.collection_name or "embeddings",
            dimension=dimension,
            distance_metric=config.distance_metric or "cosine",
        )

    # Unknown vector store type
    msg = f"Unsupported vector store kind: {kind}. Supported types: pgvector, qdrant, duckdb"
    raise ValueError(msg)
