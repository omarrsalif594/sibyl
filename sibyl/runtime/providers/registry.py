"""Provider registry for managing runtime provider instances.

This module provides the ProviderRegistry class which holds all provider instances
and the build_providers factory function which constructs the registry from
WorkspaceSettings configuration.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sibyl.core.protocols.infrastructure.data_providers import (
    EmbeddingsProvider,
    VectorStoreProvider,
)
from sibyl.core.protocols.infrastructure.llm import LLMProvider
from sibyl.core.protocols.infrastructure.mcp import MCPProvider
from sibyl.runtime.providers.mcp import HTTPMCPProvider, StdIOMCPProvider

# Import at runtime to avoid circular imports
if TYPE_CHECKING:
    from sibyl.workspace.schema import WorkspaceSettings

logger = logging.getLogger(__name__)


@dataclass
class ProviderRegistry:
    """Registry for all provider instances.

    This class holds references to all configured providers and provides
    convenient access methods.

    Attributes:
        llm: Dictionary of LLM provider instances (name -> provider)
        embeddings: Dictionary of embeddings provider instances
        vector_store: Dictionary of vector store provider instances
        mcp: Dictionary of MCP provider instances
    """

    llm: dict[str, LLMProvider] = field(default_factory=dict)
    embeddings: dict[str, EmbeddingsProvider] = field(default_factory=dict)
    vector_store: dict[str, VectorStoreProvider] = field(default_factory=dict)
    mcp: dict[str, MCPProvider] = field(default_factory=dict)

    def get_llm(self, name: str = "default") -> LLMProvider | None:
        """Get an LLM provider by name.

        Args:
            name: Provider name (defaults to "default")

        Returns:
            LLM provider instance or None if not found
        """
        return self.llm.get(name)

    def get_embeddings(self, name: str = "default") -> EmbeddingsProvider | None:
        """Get an embeddings provider by name.

        Args:
            name: Provider name (defaults to "default")

        Returns:
            Embeddings provider instance or None if not found
        """
        return self.embeddings.get(name)

    def get_vector_store(self, name: str = "default") -> VectorStoreProvider | None:
        """Get a vector store provider by name.

        Args:
            name: Provider name (defaults to "default")

        Returns:
            Vector store provider instance or None if not found
        """
        return self.vector_store.get(name)

    def get_mcp(self, name: str) -> MCPProvider | None:
        """Get an MCP provider by name.

        Args:
            name: Provider name

        Returns:
            MCP provider instance or None if not found
        """
        return self.mcp.get(name)

    def list_providers(self) -> dict[str, list[str]]:
        """List all available providers by type.

        Returns:
            Dictionary mapping provider type to list of provider names
        """
        return {
            "llm": list(self.llm.keys()),
            "embeddings": list(self.embeddings.keys()),
            "vector_store": list(self.vector_store.keys()),
            "mcp": list(self.mcp.keys()),
        }


def build_providers(workspace: "WorkspaceSettings") -> ProviderRegistry:
    """Build a ProviderRegistry from WorkspaceSettings configuration.

    This is the main factory function that constructs all provider instances
    based on the workspace configuration.

    Args:
        workspace: Workspace settings containing provider configurations

    Returns:
        Configured ProviderRegistry instance

    Raises:
        ValueError: If required provider configuration is missing or invalid
        ImportError: If required provider implementation is not available

    Example:
        >>> from sibyl.workspace import load_workspace
        >>> workspace = load_workspace("config/workspaces/example.yaml")
        >>> registry = build_providers(workspace)
        >>> llm = registry.get_llm("default")
    """
    # Import here to avoid circular imports
    from sibyl.runtime.providers.factories import (
        create_embeddings_provider,
        create_llm_provider,
        create_vector_store_provider,
    )

    logger.info("Building providers for workspace: %s", workspace.name)

    registry = ProviderRegistry()

    # Build LLM providers
    for name, config in workspace.providers.llm.items():
        try:
            logger.debug("Creating LLM provider: %s", name)
            provider = create_llm_provider(config)
            registry.llm[name] = provider
            logger.info("Registered LLM provider: %s (%s/%s)", name, config.provider, config.model)
        except Exception as e:
            logger.exception("Failed to create LLM provider '%s': %s", name, e)
            raise

    # Build embeddings providers
    for name, config in workspace.providers.embeddings.items():
        try:
            logger.debug("Creating embeddings provider: %s", name)
            provider = create_embeddings_provider(config)
            registry.embeddings[name] = provider
            logger.info(
                "Registered embeddings provider: %s (%s/%s)", name, config.provider, config.model
            )
        except Exception as e:
            logger.exception("Failed to create embeddings provider '%s': %s", name, e)
            raise

    # Build vector store providers
    for name, config in workspace.providers.vector_store.items():
        try:
            logger.debug("Creating vector store provider: %s", name)
            provider = create_vector_store_provider(config)
            registry.vector_store[name] = provider
            logger.info("Registered vector store provider: %s (%s)", name, config.kind)
        except Exception as e:
            logger.exception("Failed to create vector store provider '%s': %s", name, e)
            raise

    # Build MCP providers
    for name, config in workspace.providers.mcp.items():
        try:
            logger.debug("Creating MCP provider: %s", name)
            if config.type == "http_mcp":
                provider = HTTPMCPProvider(
                    endpoint=config.endpoint,
                    tools=config.tools,
                    timeout_s=config.timeout_s,
                    auth=config.auth,
                )
            elif config.type == "stdio_mcp":
                provider = StdIOMCPProvider(
                    command=config.endpoint,
                    tools=config.tools,
                    timeout_s=config.timeout_s,
                )
            else:
                msg = f"Unknown MCP type: {config.type}"
                raise ValueError(msg)

            registry.mcp[name] = provider
            logger.info("Registered MCP provider: %s (%s)", name, config.type)
        except Exception as e:
            logger.exception("Failed to create MCP provider '%s': %s", name, e)
            raise

    logger.info(
        f"Provider registry built successfully: "
        f"{len(registry.llm)} LLM, "
        f"{len(registry.embeddings)} embeddings, "
        f"{len(registry.vector_store)} vector store, "
        f"{len(registry.mcp)} MCP"
    )

    return registry
