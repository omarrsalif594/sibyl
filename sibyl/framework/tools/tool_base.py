"""
Unified Tool Base Classes for Sibyl Framework.

This module provides compatible SibylTool classes that bridge
the domain/template-style API with the framework's protocol-based architecture.

It combines features from:
- domain/tool_base.py: Simple async API for templates
- platform/extensibility/tool_base.py: Rich metadata and composability
- framework/tools/tool_interface.py: Protocol-based design with DI

Key Features:
- Dual API: Support both simple (domain) and rich (platform) styles
- Async/sync execution with safe_execute wrappers
- Pre/post execution hooks
- Input validation with JSON schema
- MCP and OpenAPI tool definitions
- Composable tool architecture
- Integration with ToolContext and DI container

Usage (Simple Domain Style):
    ```python
    from sibyl.framework.tools import SibylTool, ToolResult

    class PytestTool(SibylTool):
        name = "run_tests"
        description = "Execute pytest suite"
        input_schema = {
            "type": "object",
            "properties": {
                "test_path": {"type": "string"},
                "markers": {"type": "array", "items": {"type": "string"}}
            }
        }

        async def execute(self, **kwargs) -> ToolResult:
            # Implementation
            return ToolResult(success=True, output={"tests": 42})
    ```

Usage (Rich Platform Style):
    ```python
    from sibyl.framework.tools import SibylTool, ToolMetadata, ToolResult

    class SearchTool(SibylTool):
        def __init__(self, vector_index):
            super().__init__()
            self.vector_index = vector_index

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                name="search_models",
                version="1.0.0",
                category="search",
                description="Search models by semantic similarity",
                input_schema={...},
                output_schema={...},
                max_execution_time_ms=5000,
                tags=["search", "vector"]
            )

        def execute(self, **kwargs) -> ToolResult:
            results = self.vector_index.search(kwargs["query"])
            return ToolResult(success=True, data=results)
    ```
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from ._tool_async import measure_execution_time, run_coroutine_sync, safe_await_if_needed
from ._tool_errors import (
    log_execution_complete,
    log_execution_error,
    log_execution_start,
    log_validation_failure,
)

# Internal modules (not exported)
from ._tool_validation import get_default_metadata_from_class, validate_input_schema
from .tool_interface import ToolMetadata as FrameworkToolMetadata

logger = logging.getLogger(__name__)


# ===================================================================
# Result Types
# ===================================================================


@dataclass
class ToolResult:
    """
    Result of tool execution (unified across domain and platform layers).

    Supports both styles:
    - Domain style: ToolResult(success=True, output={...})
    - Platform style: ToolResult(success=True, data={...})

    Attributes:
        success: Whether the tool execution succeeded
        output: Tool output data (domain style)
        data: Tool output data (platform style, alias for output)
        error: Optional error message if failed
        metadata: Additional context (execution time, etc.)
        tool_name: Name of the tool that produced this result
        execution_id: Unique identifier for this execution
        execution_time_ms: Time taken to execute in milliseconds
        timestamp: When the execution completed
    """

    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_name: str = ""
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    execution_time_ms: float | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __init__(
        self,
        success: bool,
        output: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        tool_name: str = "",
        execution_id: str | None = None,
        execution_time_ms: float | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Initialize ToolResult with support for both 'output' and 'data' parameters.

        Args:
            success: Whether the tool execution succeeded
            output: Tool output data (preferred)
            data: Tool output data (alias, for backward compatibility)
            error: Optional error message if failed
            metadata: Additional context
            tool_name: Name of the tool that produced this result
            execution_id: Unique identifier for this execution
            execution_time_ms: Time taken to execute in milliseconds
            timestamp: When the execution completed
        """
        self.success = success
        # Support both 'data' and 'output' - prefer whichever is provided
        self.output = data if output is None and data is not None else output
        self.error = error
        self.metadata = metadata or {}
        self.tool_name = tool_name
        self.execution_id = execution_id or str(uuid4())
        self.execution_time_ms = execution_time_ms
        self.timestamp = timestamp or datetime.utcnow()

    @property
    def data(self) -> dict[str, Any] | None:
        """Alias for output (platform style)."""
        return self.output

    @data.setter
    def data(self, value: dict[str, Any] | None) -> None:
        """Set output via data property."""
        self.output = value

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        result = {
            "success": self.success,
            "metadata": self.metadata,
        }
        if self.output is not None:
            result["output"] = self.output
            result["data"] = self.output  # Include both for compatibility
        if self.error is not None:
            result["error"] = self.error
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.execution_id:
            result["execution_id"] = self.execution_id
        result["timestamp"] = self.timestamp.isoformat()
        return result


class ToolExecutionError(Exception):
    """Raised when tool execution fails critically."""


# ===================================================================
# Unified ToolMetadata
# ===================================================================


@dataclass
class ToolMetadata:
    """
    Unified tool metadata combining domain and platform features.

    Attributes:
        name: Unique tool identifier (e.g., "run_tests", "search_models")
        description: Human-readable description
        input_schema: JSON Schema for input validation
        output_schema: Optional JSON Schema for output
        version: Tool version for compatibility (default "1.0.0")
        category: Tool category (default "general")
        tags: Categorization tags
        author: Tool author/maintainer
        examples: Example usage patterns
        max_execution_time_ms: Maximum execution time in milliseconds
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    version: str = "1.0.0"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    author: str | None = None
    examples: list[dict[str, Any]] = field(default_factory=list)
    max_execution_time_ms: int = 120000  # 2 minutes default

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "version": self.version,
            "category": self.category,
            "tags": self.tags,
            "author": self.author,
            "examples": self.examples,
            "max_execution_time_ms": self.max_execution_time_ms,
        }

    def to_framework_metadata(self) -> FrameworkToolMetadata:
        """Convert to framework ToolMetadata for protocol compliance."""
        return FrameworkToolMetadata(
            name=self.name,
            version=self.version,
            category=self.category,
            description=self.description,
            input_schema=self.input_schema,  # type: ignore
            output_schema=self.output_schema or {"type": "object"},  # type: ignore
            max_execution_time_ms=self.max_execution_time_ms,
            examples=self.examples,
            tags=self.tags,
        )


# ===================================================================
# Unified SibylTool Base Class
# ===================================================================


class SibylTool(ABC):
    """
    Unified base class for all Sibyl tools.

    This class bridges the domain/template-style API with the framework's
    protocol-based architecture. It supports both simple (domain) and rich
    (platform) usage patterns.

    Features:
    - Async and sync execution
    - Input validation with JSON schema
    - Pre/post execution hooks
    - Safe execution with error handling and timing
    - MCP and OpenAPI tool definitions
    - Integration with ToolContext and DI container

    Subclasses can use two styles:

    1. Domain style (simple, class attributes):
        ```python
        class MyTool(SibylTool):
            name = "my_tool"
            description = "Does something"
            input_schema = {...}

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, output={...})
        ```

    2. Platform style (rich, get_metadata method):
        ```python
        class MyTool(SibylTool):
            def get_metadata(self) -> ToolMetadata:
                return ToolMetadata(name="my_tool", ...)

            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={...})
        ```
    """

    # Class attributes for domain-style tools
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    # Execution behavior
    requires_confirmation: bool = False
    timeout: int = 120  # 2 minutes default

    def __init__(self) -> None:
        """Initialize tool."""
        self._metadata_cache: ToolMetadata | None = None

    @property
    def metadata(self) -> ToolMetadata:
        """
        Get tool metadata (property for Tool protocol compliance).

        Returns:
            ToolMetadata instance
        """
        return self.get_metadata()

    def get_metadata(self) -> ToolMetadata:
        """
        Get tool metadata.

        Default implementation uses class attributes (domain style).
        Override for rich metadata (platform style).

        Returns:
            ToolMetadata with name, description, schema, etc.
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        # Build from class attributes using internal module
        metadata_dict = get_default_metadata_from_class(self, self.timeout)
        self._metadata_cache = ToolMetadata(**metadata_dict)
        return self._metadata_cache

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool with provided inputs.

        This method can be either synchronous or asynchronous.
        The safe_execute wrappers will handle both cases automatically.

        Subclasses must implement this method.

        Args:
            **kwargs: Tool inputs matching input_schema

        Returns:
            ToolResult with success/output/error (or coroutine returning ToolResult)

        Raises:
            ToolExecutionError: If execution fails critically
        """
        ...

    def execute_sync(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool synchronously.

        Default implementation runs async execute() in event loop.
        Override for native sync implementation.

        Args:
            **kwargs: Tool inputs matching input_schema

        Returns:
            ToolResult with success/output/error
        """
        try:
            return run_coroutine_sync(self.execute(**kwargs))
        except Exception as e:
            logger.exception("Sync execution failed: %s", e)
            return ToolResult(
                success=False, error=str(e), metadata={"error_type": type(e).__name__}
            )

    async def execute_async(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool asynchronously.

        Alias for execute() for compatibility.

        Args:
            **kwargs: Tool inputs matching input_schema

        Returns:
            ToolResult with success/output/error
        """
        return await self.execute(**kwargs)

    async def validate_inputs(self, **kwargs: Any) -> tuple[bool, str | None]:
        """
        Validate inputs against input_schema.

        Delegates to internal validation module.

        Args:
            **kwargs: Inputs to validate

        Returns:
            (is_valid, error_message)
        """
        metadata = self.get_metadata()
        return await validate_input_schema(metadata.input_schema, kwargs)

    async def pre_execute(self, **kwargs: Any) -> None:
        """
        Hook called before execute().

        Subclasses can override for setup (e.g., check dependencies).

        Args:
            **kwargs: Tool inputs
        """

    async def post_execute(self, result: ToolResult) -> ToolResult:
        """
        Hook called after execute().

        Subclasses can override for cleanup or result transformation.

        Args:
            result: Tool execution result

        Returns:
            Potentially modified result
        """
        return result

    async def safe_execute_async(self, **kwargs: Any) -> ToolResult:
        """
        Execute tool with validation, error handling, and timing (async).

        Uses internal modules for validation, async handling, and error management.

        Args:
            **kwargs: Input parameters

        Returns:
            ToolResult (always returns, never raises)
        """
        metadata = self.get_metadata()
        start_time = datetime.now()

        try:
            # Validate inputs
            is_valid, error_msg = await self.validate_inputs(**kwargs)
            if not is_valid:
                log_validation_failure(metadata.name, error_msg or "Unknown validation error")
                return ToolResult(
                    success=False,
                    error=f"Input validation failed: {error_msg}",
                    tool_name=metadata.name,
                    metadata={"validation_error": error_msg},
                )

            # Pre-execute hook
            await self.pre_execute(**kwargs)

            # Execute (handle both sync and async execute methods)
            log_execution_start(metadata.name)
            result = self.execute(**kwargs)

            # Check if result is a coroutine and await it if needed
            result = await safe_await_if_needed(result)

            # Set tool name if not already set
            if not result.tool_name:
                result.tool_name = metadata.name

            # Add timing if not already set
            if result.execution_time_ms is None:
                result.execution_time_ms = measure_execution_time(start_time)

            # Post-execute hook
            result = await self.post_execute(result)

            log_execution_complete(metadata.name, result.execution_time_ms)
            return result

        except Exception as e:
            execution_time = measure_execution_time(start_time)
            log_execution_error(metadata.name, e)

            return ToolResult(
                success=False,
                error=str(e),
                tool_name=metadata.name,
                execution_time_ms=execution_time,
                metadata={"error_type": type(e).__name__},
            )

    def safe_execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute tool with validation, error handling, and timing (sync).

        Args:
            **kwargs: Input parameters

        Returns:
            ToolResult (always returns, never raises)
        """
        try:
            return run_coroutine_sync(self.safe_execute_async(**kwargs))
        except Exception as e:
            metadata = self.get_metadata()
            logger.exception("Safe execute failed: %s", e)
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=metadata.name,
                metadata={"error_type": type(e).__name__},
            )

    def get_name(self) -> str:
        """Get tool name from metadata."""
        return self.get_metadata().name

    def get_description(self) -> str:
        """Get tool description from metadata."""
        return self.get_metadata().description

    def get_tags(self) -> list[str]:
        """Get tool tags from metadata."""
        return self.get_metadata().tags

    def get_version(self) -> str:
        """Get tool version from metadata."""
        return self.get_metadata().version

    def to_mcp_tool(self) -> dict[str, Any]:
        """
        Convert to MCP tool schema (domain style).

        Returns:
            MCP tool definition dict
        """
        metadata = self.get_metadata()
        return {
            "name": metadata.name,
            "description": metadata.description,
            "inputSchema": metadata.input_schema,
        }

    def to_mcp_tool_definition(self) -> dict[str, Any]:
        """
        Convert to MCP tool definition format (platform style).

        Alias for to_mcp_tool() for compatibility.

        Returns:
            Dictionary compatible with MCP Tool definition
        """
        return self.to_mcp_tool()

    def to_openapi_definition(self) -> dict[str, Any]:
        """
        Convert to OpenAPI/Swagger definition format.

        Returns:
            Dictionary compatible with OpenAPI spec
        """
        metadata = self.get_metadata()
        return {
            "operationId": metadata.name,
            "summary": metadata.description,
            "tags": metadata.tags,
            "requestBody": {"content": {"application/json": {"schema": metadata.input_schema}}},
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {"schema": metadata.output_schema or {"type": "object"}}
                    },
                }
            },
        }


# ===================================================================
# Composable Tool
# ===================================================================


class ComposableTool(SibylTool):
    """
    Base class for tools that compose other tools.

    ComposableTool enables building higher-level workflows by combining
    multiple Sibyl tools into orchestrated sequences.

    Example:
        A "validate_and_report" tool that composes:
        - validate_data
        - search_similar_patterns
        - generate_report

    Usage:
        ```python
        class ValidateAndReportTool(ComposableTool):
            def __init__(self, validate_tool, search_tool, report_tool):
                super().__init__([validate_tool, search_tool, report_tool])

            def get_metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="validate_and_report",
                    description="Validate data and generate report",
                    input_schema={...}
                )

            async def execute(self, **kwargs) -> ToolResult:
                # Execute child tools in sequence
                val_result = await self.execute_child_async("validate_data", **kwargs)
                if not val_result.success:
                    return val_result

                search_result = await self.execute_child_async("search_patterns", query=val_result.output["pattern"])
                # ... continue workflow
                return ToolResult(success=True, output={"report": ...})
        ```
    """

    def __init__(self, tools: list[SibylTool]) -> None:
        """
        Initialize with child tools.

        Args:
            tools: List of Sibyl tools to compose
        """
        super().__init__()
        self.tools = {tool.get_name(): tool for tool in tools}

    def execute_child(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a child tool synchronously.

        Args:
            tool_name: Name of child tool
            **kwargs: Input parameters

        Returns:
            ToolResult from child tool
        """
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Child tool not found: {tool_name}")

        return self.tools[tool_name].safe_execute(**kwargs)

    async def execute_child_async(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        Execute a child tool asynchronously.

        Args:
            tool_name: Name of child tool
            **kwargs: Input parameters

        Returns:
            ToolResult from child tool
        """
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Child tool not found: {tool_name}")

        return await self.tools[tool_name].safe_execute_async(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the composable tool workflow.

        Subclasses must implement this to define the workflow.

        Args:
            **kwargs: Tool inputs

        Returns:
            ToolResult from the workflow
        """
        ...
