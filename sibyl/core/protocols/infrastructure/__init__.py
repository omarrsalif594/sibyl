"""
Infrastructure protocol interfaces.

This module provides the STABLE PUBLIC API for infrastructure-related protocol interfaces
that define provider contracts and extension points.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

This module exports all infrastructure-related protocol interfaces:
- LLM provider protocols (LLMProvider, CompletionOptions, CompletionResult, etc.)
- Data provider protocols (LineageProvider, PatternProvider, VectorProvider, CacheProvider, EmbeddingsProvider, VectorStoreProvider)
- MCP provider protocols (MCPProvider, MCPToolDefinition, error types)
- Hook protocols (ToolHook, HookContext)

Example:
    from sibyl.core.protocols.infrastructure import LLMProvider, CompletionOptions

    class MyLLMProvider(LLMProvider):
        async def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
            # Your implementation
            pass
"""

# Re-export from new location
from sibyl.core.contracts.hooks import HookResult

from .data_providers import (
    CacheProvider,
    EmbeddingsProvider,
    LineageProvider,
    PatternProvider,
    VectorProvider,
    VectorStoreProvider,
)
from .hooks import (
    HookContext,
    ToolHook,
)
from .llm import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    ProviderFeatures,
    ProviderFingerprint,
)
from .mcp import (
    MCPConnectionError,
    MCPError,
    MCPProvider,
    MCPToolDefinition,
    MCPToolError,
    MCPToolNotFoundError,
)

__all__ = [
    "CacheProvider",
    "CompletionOptions",
    "CompletionResult",
    "EmbeddingsProvider",
    "HookContext",
    "HookResult",
    # LLM protocols
    "LLMProvider",
    # Data provider protocols
    "LineageProvider",
    "MCPConnectionError",
    "MCPError",
    # MCP protocols
    "MCPProvider",
    "MCPToolDefinition",
    "MCPToolError",
    "MCPToolNotFoundError",
    "PatternProvider",
    "ProviderFeatures",
    "ProviderFingerprint",
    # Hook protocols
    "ToolHook",
    "VectorProvider",
    "VectorStoreProvider",
]
