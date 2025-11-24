"""
Provider management for Sibyl runtime.

This module provides the STABLE PUBLIC API for provider management, including
registry and factory functions for building LLM, embeddings, vector store, and MCP providers.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

Only the registry and factory functions are part of the public API. Concrete provider
implementations (LocalLLMProvider, DuckDBVectorStore, etc.) are internal and may change.

Example:
    from sibyl.runtime.providers import ProviderRegistry, build_providers
    from sibyl.workspace import load_workspace

    # Build all providers from workspace
    workspace = load_workspace("config/workspaces/my_workspace.yaml")
    providers = build_providers(workspace)

    # Access providers from registry
    llm = providers.get_llm_provider("default")
    embeddings = providers.get_embeddings_provider("default")

    # Build individual provider
    from sibyl.runtime.providers import build_llm_provider
    llm = build_llm_provider(workspace.providers.llm["default"])
"""

import contextlib

from .factories import (
    create_embeddings_provider,
    create_llm_provider,
    create_vector_store_provider,
)
from .registry import ProviderRegistry, build_providers

# Internal implementations - not part of public API
# These are imported lazily to avoid import errors if they don't exist
with contextlib.suppress(ImportError):
    from .embeddings import EmbeddingsProvider

with contextlib.suppress(ImportError):
    from .llm_local import LocalLLMProvider

with contextlib.suppress(ImportError):
    from .mcp import MCPProvider

with contextlib.suppress(ImportError):
    from .vector_store_duckdb import DuckDBVectorStore

# Public API - only registry and factories
__all__ = [
    # Registry
    "ProviderRegistry",
    "build_providers",
    "create_embeddings_provider",
    # Factories
    "create_llm_provider",
    "create_vector_store_provider",
]
