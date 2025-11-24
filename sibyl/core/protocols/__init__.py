"""
Core protocol interfaces for Sibyl.

This module provides the STABLE PUBLIC API for protocol interfaces that define
extension points and provider contracts.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

This module provides convenient access to the most commonly used protocols:
- LLM provider protocols
- RAG pipeline code processing protocols
- Hook system protocols

Use these protocols to implement custom providers and extend Sibyl's capabilities.

Example:
    from sibyl.core.protocols import LLMProvider, CompletionOptions
    from sibyl.core.protocols import CodeChunker, CodeValidator
    from sibyl.core.protocols import ToolHook, HookContext

    # Implement custom LLM provider
    class MyLLMProvider(LLMProvider):
        async def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
            # Your implementation
            pass

For additional protocols, see:
    - sibyl.core.protocols.infrastructure.data_providers (LineageProvider, etc.)
    - sibyl.core.protocols.infrastructure.mcp (MCPProvider)
"""

# Infrastructure protocols - LLM
# Infrastructure protocols - Hooks
from sibyl.core.protocols.infrastructure.hooks import (
    HookContext,
    ToolHook,
)
from sibyl.core.protocols.infrastructure.llm import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    ProviderFeatures,
    ProviderFingerprint,
)

# RAG pipeline protocols - Code processing
from sibyl.core.protocols.rag_pipeline.code_processing import (
    Chunk,
    CodeChunker,
    CodeType,
    CodeValidator,
    ComplexityScorer,
)

__all__ = [
    "Chunk",
    # Code processing protocols
    "CodeChunker",
    "CodeType",
    "CodeValidator",
    "CompletionOptions",
    "CompletionResult",
    "ComplexityScorer",
    "HookContext",
    # LLM Provider protocols
    "LLMProvider",
    "ProviderFeatures",
    "ProviderFingerprint",
    # Hook protocols
    "ToolHook",
]
