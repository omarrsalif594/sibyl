"""
Tool interface protocol and metadata structures.

All MCP tools must implement the Tool protocol with versioned metadata.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, TypedDict


class ToolInputSchema(TypedDict, total=False):
    """JSON Schema for tool input validation."""

    type: str
    properties: dict[str, Any]
    required: list[str]
    additionalProperties: bool


class ToolOutputSchema(TypedDict, total=False):
    """JSON Schema for tool output validation."""

    type: str
    properties: dict[str, Any]
    required: list[str]


@dataclass
class ToolMetadata:
    """Metadata for a tool."""

    name: str
    version: str  # Semver string (e.g., "1.0.0", "2.3.1")
    category: str  # "lineage", "search", "analysis", "pattern", "intelligence", etc.
    description: str
    input_schema: ToolInputSchema
    output_schema: ToolOutputSchema
    max_execution_time_ms: int  # Maximum allowed execution time
    examples: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate metadata after initialization."""
        if not self.name:
            msg = "Tool name cannot be empty"
            raise ValueError(msg)
        if not self.version:
            msg = "Tool version cannot be empty"
            raise ValueError(msg)
        if not self._is_valid_semver(self.version):
            msg = f"Invalid semver: {self.version}"
            raise ValueError(msg)
        if self.max_execution_time_ms <= 0:
            msg = "max_execution_time_ms must be positive"
            raise ValueError(msg)

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """Check if version string is valid semver."""
        parts = version.split(".")
        if len(parts) != 3:
            return False
        try:
            [int(p) for p in parts]
            return True
        except ValueError:
            return False


@dataclass
class ToolContext:
    """
    Context injected into tool execution.

    Contains all dependencies needed by tools, plus request-level metadata.
    """

    # Provider dependencies (injected by DI container)
    lineage: "LineageProvider"  # type: ignore
    patterns: "PatternProvider"  # type: ignore
    vectors: Optional["VectorProvider"]  # type: ignore
    cache: Optional["CacheProvider"]  # type: ignore

    # Request-level metadata
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    session_id: str | None = None

    def cache_key(self, *parts: Any) -> str:
        """Build a cache key from parts.

        Example:
            ctx.cache_key("lineage", "downstream", model_id, depth)
            -> "lineage:downstream:example_resource:2"
        """
        return ":".join(str(p) for p in parts)


class Tool(Protocol):
    """
    Tool interface - all tools must implement this.

    Tools are stateless, pure functions that:
    - Accept a ToolContext with injected dependencies
    - Accept validated input data (dict matching input_schema)
    - Return dict matching output_schema
    - Raise typed exceptions from application/errors.py
    """

    metadata: ToolMetadata

    def execute(self, ctx: ToolContext, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute tool with injected context and validated input.

        Args:
            ctx: ToolContext with dependencies and correlation_id
            input_data: Input dict (already validated against input_schema)

        Returns:
            Output dict (will be validated against output_schema)

        Raises:
            ValidationError: If input assumptions violated during execution
            NotFoundError: If required resource not found
            TimeoutError: If operation takes too long (internal timeout)
            ConflictError: If resource conflict detected
            InternalError: If unexpected error occurs
        """
        ...


@dataclass
class ToolExecutionResult:
    """Result of tool execution with metadata."""

    tool_name: str
    tool_version: str
    correlation_id: str
    success: bool
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    execution_time_ms: float = 0.0
    cache_hit: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        result = {
            "tool": self.tool_name,
            "version": self.tool_version,
            "correlation_id": self.correlation_id,
            "success": self.success,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "cache_hit": self.cache_hit,
        }
        if self.output is not None:
            result["output"] = self.output
        if self.error is not None:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result
