"""Provider factory for dynamic provider instantiation.

This module provides a factory pattern for creating provider instances from configuration.
Supports LLM providers, embedding providers, and MCP adapters.
"""

import logging
import os

from sibyl.core.protocols.infrastructure.llm import LLMProvider
from sibyl.techniques.rag_pipeline.search.impls.core.vector_index import EmbeddingProvider

from .config import ProviderConfig

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating provider instances from configuration."""

    # Registry of provider type -> provider class mappings
    _llm_providers: dict[str, type] = {}
    _embedding_providers: dict[str, type] = {}
    _mcp_adapters: dict[str, type] = {}

    @classmethod
    def register_llm_provider(cls, provider_name: str, provider_class: type) -> None:
        """Register an LLM provider class.

        Args:
            provider_name: Provider identifier (e.g., "anthropic", "openai")
            provider_class: Provider class to instantiate
        """
        cls._llm_providers[provider_name] = provider_class
        logger.debug("Registered LLM provider: %s", provider_name)

    @classmethod
    def register_embedding_provider(cls, provider_name: str, provider_class: type) -> None:
        """Register an embedding provider class.

        Args:
            provider_name: Provider identifier (e.g., "fastembed", "openai-embeddings")
            provider_class: Provider class to instantiate
        """
        cls._embedding_providers[provider_name] = provider_class
        logger.debug("Registered embedding provider: %s", provider_name)

    @classmethod
    def register_mcp_adapter(cls, adapter_name: str, adapter_class: type) -> None:
        """Register an MCP adapter class.

        Args:
            adapter_name: Adapter identifier (e.g., "mcp-llm", "mcp-embedding")
            adapter_class: Adapter class to instantiate
        """
        cls._mcp_adapters[adapter_name] = adapter_class
        logger.debug("Registered MCP adapter: %s", adapter_name)

    @classmethod
    def create_llm_provider(cls, config: ProviderConfig) -> LLMProvider:
        """Create an LLM provider instance from configuration.

        Args:
            config: Provider configuration

        Returns:
            Instantiated LLM provider

        Raises:
            ValueError: If provider type is unknown or configuration is invalid
        """
        if not config.enabled:
            msg = f"Provider {config.name} is disabled"
            raise ValueError(msg)

        # Handle MCP providers
        if config.type == "mcp":
            return cls._create_mcp_llm_adapter(config)

        # Handle API and local providers
        provider_class = cls._llm_providers.get(config.name)
        if not provider_class:
            msg = (
                f"Unknown LLM provider: {config.name}. Available: {list(cls._llm_providers.keys())}"
            )
            raise ValueError(msg)

        # Extract API key from environment if specified
        kwargs = {}
        if config.connection.api_key_env:
            api_key = os.getenv(config.connection.api_key_env)
            if not api_key:
                msg = f"API key not found in environment variable: {config.connection.api_key_env}"
                raise ValueError(msg)
            kwargs["api_key"] = api_key

        # Add optional connection parameters
        if config.connection.endpoint:
            kwargs["base_url"] = config.connection.endpoint

        # Add default model if available
        if config.models:
            best_model = config.get_best_model()
            if best_model:
                kwargs["default_model"] = best_model.name

        # Add timeout
        kwargs["timeout_seconds"] = config.connection.timeout_seconds

        try:
            provider = provider_class(**kwargs)
            logger.info("Created LLM provider: %s (type: %s)", config.name, config.type)
            return provider
        except Exception as e:
            msg = f"Failed to create LLM provider {config.name}: {e}"
            raise ValueError(msg) from e

    @classmethod
    def create_embedding_provider(cls, config: ProviderConfig) -> EmbeddingProvider:
        """Create an embedding provider instance from configuration.

        Args:
            config: Provider configuration

        Returns:
            Instantiated embedding provider

        Raises:
            ValueError: If provider type is unknown or configuration is invalid
        """
        if not config.enabled:
            msg = f"Provider {config.name} is disabled"
            raise ValueError(msg)

        # Handle MCP providers
        if config.type == "mcp":
            return cls._create_mcp_embedding_adapter(config)

        # Handle API and local providers
        provider_class = cls._embedding_providers.get(config.name)
        if not provider_class:
            msg = (
                f"Unknown embedding provider: {config.name}. "
                f"Available: {list(cls._embedding_providers.keys())}"
            )
            raise ValueError(msg)

        # Extract API key from environment if specified
        kwargs = {}
        if config.connection.api_key_env:
            api_key = os.getenv(config.connection.api_key_env)
            if not api_key:
                msg = f"API key not found in environment variable: {config.connection.api_key_env}"
                raise ValueError(msg)
            kwargs["api_key"] = api_key

        # Add model if available
        if config.models:
            best_model = config.get_best_model()
            if best_model:
                kwargs["model"] = best_model.name
        # For local providers like fastembed, use model_name instead
        elif config.type == "local" and config.name == "fastembed":
            # Default to all-MiniLM-L6-v2 for FastEmbed
            kwargs["model_name"] = "sentence-transformers/all-MiniLM-L6-v2"

        try:
            provider = provider_class(**kwargs)
            logger.info("Created embedding provider: %s (type: %s)", config.name, config.type)
            return provider
        except Exception as e:
            msg = f"Failed to create embedding provider {config.name}: {e}"
            raise ValueError(msg) from e

    @classmethod
    def _create_mcp_llm_adapter(cls, config: ProviderConfig) -> LLMProvider:
        """Create an MCP LLM adapter.

        Args:
            config: Provider configuration

        Returns:
            MCP LLM adapter instance

        Raises:
            ValueError: If MCP adapter not registered
        """
        adapter_class = cls._mcp_adapters.get("mcp-llm")
        if not adapter_class:
            msg = "MCP LLM adapter not registered. Use ProviderFactory.register_mcp_adapter()"
            raise ValueError(msg)

        # Extract MCP-specific configuration
        kwargs = {
            "provider_name": config.name,
            "endpoint": config.connection.endpoint,
        }

        try:
            adapter = adapter_class(**kwargs)
            logger.info("Created MCP LLM adapter: %s", config.name)
            return adapter
        except Exception as e:
            msg = f"Failed to create MCP LLM adapter {config.name}: {e}"
            raise ValueError(msg) from e

    @classmethod
    def _create_mcp_embedding_adapter(cls, config: ProviderConfig) -> EmbeddingProvider:
        """Create an MCP embedding adapter.

        Args:
            config: Provider configuration

        Returns:
            MCP embedding adapter instance

        Raises:
            ValueError: If MCP adapter not registered
        """
        adapter_class = cls._mcp_adapters.get("mcp-embedding")
        if not adapter_class:
            msg = "MCP embedding adapter not registered. Use ProviderFactory.register_mcp_adapter()"
            raise ValueError(msg)

        # Extract MCP-specific configuration
        kwargs = {
            "provider_name": config.name,
            "endpoint": config.connection.endpoint,
            "embedding_dim": config.capabilities.embedding_dim,
        }

        try:
            adapter = adapter_class(**kwargs)
            logger.info("Created MCP embedding adapter: %s", config.name)
            return adapter
        except Exception as e:
            msg = f"Failed to create MCP embedding adapter {config.name}: {e}"
            raise ValueError(msg) from e


# Auto-register built-in providers
def _register_builtin_providers() -> None:
    """Register built-in provider implementations."""
    try:
        from sibyl.providers.llm.api import AnthropicClient, OpenAIClient  # plugin registration

        ProviderFactory.register_llm_provider("anthropic", AnthropicClient)
        ProviderFactory.register_llm_provider("openai", OpenAIClient)
    except ImportError as e:
        logger.warning("Failed to register LLM providers: %s", e)

    try:
        from sibyl.providers.embedding.api import OpenAIEmbeddingClient  # plugin registration
        from sibyl.providers.embedding.local import FastEmbedClient  # plugin registration

        ProviderFactory.register_embedding_provider("openai-embeddings", OpenAIEmbeddingClient)
        ProviderFactory.register_embedding_provider("fastembed", FastEmbedClient)
        # Also register with alternative names
        ProviderFactory.register_embedding_provider("sentence-transformer", FastEmbedClient)
    except ImportError as e:
        logger.warning("Failed to register embedding providers: %s", e)

    # Register MCP adapters
    try:
        from sibyl.providers.embedding.mcp import MCPEmbeddingAdapter  # plugin registration
        from sibyl.providers.llm.mcp import MCPLLMAdapter  # plugin registration

        ProviderFactory.register_mcp_adapter("mcp-llm", MCPLLMAdapter)
        ProviderFactory.register_mcp_adapter("mcp-embedding", MCPEmbeddingAdapter)
    except ImportError as e:
        logger.warning("Failed to register MCP adapters: %s", e)


# Register built-in providers on module import
_register_builtin_providers()
