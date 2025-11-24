"""
Tool protocol interfaces.

This module contains the protocol abstractions for the tool system.
These are the interfaces that both framework and techniques depend on.

Layering:
    core/protocols/tools.py (this file) - Protocol definitions
    ├─> framework/tools/* - Concrete implementations
    └─> techniques/*/tools/* - Domain-specific tools

Key protocols:
- ITool: Base tool interface
- IToolContext: Execution context interface
- IToolMetadata: Tool metadata interface
- IToolRegistry: Tool registry interface
"""

from typing import Any, Protocol, TypedDict, runtime_checkable


class IToolInputSchema(TypedDict, total=False):
    """JSON Schema for tool input validation."""

    type: str
    properties: dict[str, Any]
    required: list[str]
    additionalProperties: bool


class IToolOutputSchema(TypedDict, total=False):
    """JSON Schema for tool output validation."""

    type: str
    properties: dict[str, Any]
    required: list[str]


@runtime_checkable
class IToolMetadata(Protocol):
    """Protocol for tool metadata.

    This defines the interface that all tool metadata must implement.
    """

    @property
    def name(self) -> str:
        """Tool name identifier."""
        ...

    @property
    def version(self) -> str:
        """Tool version (semver format)."""
        ...

    @property
    def category(self) -> str:
        """Tool category (e.g., 'lineage', 'search', 'analysis')."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def input_schema(self) -> IToolInputSchema:
        """JSON Schema for input validation."""
        ...

    @property
    def output_schema(self) -> IToolOutputSchema:
        """JSON Schema for output validation."""
        ...


@runtime_checkable
class IToolContext(Protocol):
    """Protocol for tool execution context.

    This provides dependencies and request metadata to tools.
    """

    @property
    def correlation_id(self) -> str:
        """Unique identifier for this execution."""
        ...


@runtime_checkable
class ITool(Protocol):
    """Protocol for tool interface.

    All tools must implement this protocol to be usable by the framework.
    """

    @property
    def metadata(self) -> IToolMetadata:
        """Tool metadata."""
        ...

    def execute(self, ctx: IToolContext, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute tool with context and validated input.

        Args:
            ctx: Tool execution context with dependencies
            input_data: Input data (validated against input_schema)

        Returns:
            Output data (will be validated against output_schema)
        """
        ...


@runtime_checkable
class IToolRegistry(Protocol):
    """Protocol for tool registry.

    The registry manages tool registration and discovery.
    """

    def register(self, tool: ITool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register
        """
        ...

    def get(self, name: str, version: str | None = None) -> ITool | None:
        """Get tool by name and optional version.

        Args:
            name: Tool name
            version: Optional version constraint

        Returns:
            Tool instance or None
        """
        ...

    def list_tools(self) -> list[ITool]:
        """List all registered tools.

        Returns:
            List of tool instances
        """
        ...


__all__ = [
    "ITool",
    "IToolContext",
    "IToolInputSchema",
    "IToolMetadata",
    "IToolOutputSchema",
    "IToolRegistry",
]
