"""Core contracts and base abstractions.

This module provides the STABLE PUBLIC API for foundational contracts and base classes
that define the core abstractions in Sibyl.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

These are generic, domain-agnostic interfaces that techniques and applications build upon.
Use these contracts to extend Sibyl with custom tools, validators, and resources.

Exports:
- Graph abstractions (GraphProvider, NodeId, etc.)
- Provider protocols (LLMProvider, LineageProvider, etc.)
- Resource base classes (SibylResource)
- Tool base classes are available from sibyl.framework.tools
- Validator base classes (SibylValidator, ValidationResult)

Example:
    from sibyl.core.contracts import GraphProvider, LLMProvider
    from sibyl.framework.tools import SibylTool, ToolResult

    class MyCustomTool(SibylTool):
        async def execute(self, **kwargs) -> ToolResult:
            # Your implementation
            return ToolResult(success=True, data={...})
"""

# Graph abstractions
from sibyl.core.contracts.graph import (
    Edge,
    EdgeType,
    GraphAnalyzer,
    GraphProvider,
    GraphQuery,
    Node,
    NodeId,
)

# Hook abstractions
from sibyl.core.contracts.hooks import (
    HookContext,
    HookResult,
)

# Resource abstractions
from sibyl.core.contracts.resource_base import (
    ResourceManager,
    ResourceMetadata,
    SibylResource,
)

# Tool abstractions removed from this module to enforce strict layering
# Import tools directly from sibyl.framework.tools instead:
#   from sibyl.framework.tools import SibylTool, ToolResult, etc.
# Validator abstractions
from sibyl.core.contracts.validator_base import (
    SibylValidator,
    ValidationResult,
    ValidatorRegistry,
)

# Provider protocols
from sibyl.core.protocols.infrastructure.data_providers import (
    CacheProvider,
    LineageProvider,
    PatternProvider,
    VectorProvider,
)
from sibyl.core.protocols.infrastructure.llm import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    ProviderFeatures,
    ProviderFingerprint,
)

__all__ = [
    "CacheProvider",
    "CompletionOptions",
    "CompletionResult",
    "Edge",
    "EdgeType",
    "GraphAnalyzer",
    "GraphProvider",
    "GraphQuery",
    # Hooks
    "HookContext",
    "HookResult",
    "LLMProvider",
    # Providers
    "LineageProvider",
    "Node",
    # Graph
    "NodeId",
    "PatternProvider",
    "ProviderFeatures",
    "ProviderFingerprint",
    "ResourceManager",
    "ResourceMetadata",
    # Resources
    "SibylResource",
    # Tools - removed for strict layering, import from sibyl.framework.tools
    # Validators
    "SibylValidator",
    "ValidationResult",
    "ValidatorRegistry",
    "VectorProvider",
]
