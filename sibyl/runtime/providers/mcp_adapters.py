"""MCP Tool Adapter Layer for Pipeline Integration.

This module provides adapters that wrap MCP tools so they can be used as
pipeline steps. It bridges the gap between external MCP providers and
Sibyl's pipeline execution system.

Enhanced to support automatic job polling for long-running operations.

Example:
    from sibyl.runtime.providers.mcp_adapters import create_mcp_tool_step
    from sibyl.runtime.providers.mcp import HTTPMCPProvider

    # Create provider
    provider = HTTPMCPProvider(
        endpoint="http://localhost:6000",
        tools=["search", "summarize"],
        timeout_s=30
    )

    # Create adapter for a specific tool
    search_step = create_mcp_tool_step(provider, "search")

    # Use in pipeline
    result = await search_step(query="Sibyl architecture")

    # Long-running job with automatic polling
    workflow_step = create_mcp_tool_step(
        provider,
        "start_workflow",
        status_tool="get_workflow_status",
        wait=True
    )
    result = await workflow_step(workflow_name="etl")
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sibyl.core.artifacts.job_handle import (
    JobCancelledError,
    JobFailedError,
    JobTimeoutError,
    PollableJobHandle,
)
from sibyl.core.artifacts.registry import convert_mcp_response
from sibyl.core.protocols.infrastructure.mcp import (
    MCPError,
    MCPProvider,
    MCPToolDefinition,
    MCPToolNotFoundError,
)

logger = logging.getLogger(__name__)


class MCPToolAdapterError(Exception):
    """Base exception for MCP tool adapter errors."""


class MCPToolExecutionError(MCPToolAdapterError):
    """Raised when MCP tool execution fails."""

    def __init__(self, tool_name: str, provider_endpoint: str, original_error: Exception) -> None:
        """Initialize MCP tool execution error.

        Args:
            tool_name: Name of the tool that failed
            provider_endpoint: Endpoint/connection string of the provider
            original_error: Original exception from MCP provider
        """
        self.tool_name = tool_name
        self.provider_endpoint = provider_endpoint
        self.original_error = original_error

        message = (
            f"MCP tool '{tool_name}' execution failed at {provider_endpoint}: "
            f"{type(original_error).__name__}: {original_error!s}"
        )
        super().__init__(message)


@dataclass
class MCPToolMetadata:
    """Metadata about an MCP tool for documentation and validation.

    Attributes:
        name: Tool name
        description: Tool description
        input_schema: JSON schema for tool inputs
        provider_endpoint: Provider endpoint/connection string
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    provider_endpoint: str


class MCPToolAdapter:
    """Adapter to use MCP tools as pipeline steps.

    This adapter wraps an MCP provider and a specific tool name, providing
    a clean async callable interface that can be used in pipeline execution.

    The adapter handles:
    - Tool validation
    - Async execution
    - Error wrapping and propagation
    - Result extraction
    - Automatic job polling

    Attributes:
        provider: MCP provider instance
        tool_name: Name of the tool to execute
        metadata: Cached tool metadata
        status_tool: Optional tool name for polling job status
        result_tool: Optional tool name for retrieving job results
        wait: If True, automatically poll until completion
        timeout_s: Timeout for job polling in seconds
    """

    def __init__(
        self,
        provider: MCPProvider,
        tool_name: str,
        status_tool: str | None = None,
        result_tool: str | None = None,
        wait: bool = False,
        timeout_s: float = 3600.0,
        artifact_type: str | None = None,
        auto_convert: bool = True,
        provider_name: str | None = None,
    ) -> None:
        """Initialize MCP tool adapter.

        Args:
            provider: MCP provider instance (implements MCPProvider protocol)
            tool_name: Name of the tool to wrap
            status_tool: Optional tool name for polling job status
            result_tool: Optional tool name for retrieving job results
            wait: If True, automatically poll until completion
            timeout_s: Timeout for job polling in seconds
            artifact_type: Optional artifact type for auto-conversion
            auto_convert: Whether to attempt auto-conversion to artifacts
            provider_name: Optional explicit provider name (recommended). If not provided,
                          will attempt to extract from endpoint (less reliable).

        Raises:
            MCPToolNotFoundError: If tool doesn't exist in provider
        """
        self.provider = provider
        self.tool_name = tool_name
        self._metadata: MCPToolMetadata | None = None

        # Polling configuration
        self.status_tool = status_tool
        self.result_tool = result_tool
        self.wait = wait
        self.timeout_s = timeout_s

        # Auto-conversion configuration
        self.artifact_type = artifact_type
        self.auto_convert = auto_convert

        # Provider name (explicit or inferred)
        self.provider_name = provider_name or self._extract_provider_name(provider.get_endpoint())

        # Validate that tool exists
        self._validate_tool_exists()

        logger.debug(
            f"Created MCPToolAdapter for tool '{tool_name}' "
            f"at provider {provider.get_endpoint()} (provider_name={self.provider_name}) "
            f"(wait={wait}, status_tool={status_tool}, "
            f"artifact_type={artifact_type}, auto_convert={auto_convert})"
        )

    def _validate_tool_exists(self) -> None:
        """Validate that the tool exists in the provider.

        Raises:
            MCPToolNotFoundError: If tool not found
        """
        tools = self.provider.get_tools()
        tool_names = [t["name"] for t in tools]

        if self.tool_name not in tool_names:
            available = ", ".join(tool_names)
            msg = (
                f"Tool '{self.tool_name}' not found in MCP provider at "
                f"{self.provider.get_endpoint()}. Available tools: {available}"
            )
            raise MCPToolNotFoundError(msg)

    async def __call__(
        self, progress_callback: Callable | None = None, **kwargs
    ) -> dict[str, Any] | PollableJobHandle:
        """Execute the MCP tool with given parameters.

        Enhanced to support automatic job polling. If the result contains
        a job_id and status_tool is configured, the result is treated as a pollable job.

        Behavior:
        - If wait=True: Automatically polls until completion, returns final result
        - If wait=False: Returns PollableJobHandle for manual polling
        - If not a pollable job: Returns raw result

        Args:
            progress_callback: Optional callback for polling progress
            **kwargs: Tool parameters (will be passed as arguments to MCP tool)

        Returns:
            - Final result dict if wait=True and job completes
            - PollableJobHandle if wait=False and job detected
            - Raw result dict if not a pollable job

        Raises:
            MCPToolExecutionError: If tool execution fails
            JobTimeoutError: If job exceeds timeout
            JobFailedError: If job fails
            JobCancelledError: If job is cancelled

        Example:
            # Regular tool call
            adapter = MCPToolAdapter(provider, "search")
            result = await adapter(query="test", limit=10)

            # Automatic polling
            adapter = MCPToolAdapter(provider, "start_workflow", status_tool="get_status", wait=True)
            result = await adapter(workflow_name="etl")

            # Manual polling
            adapter = MCPToolAdapter(provider, "start_workflow", status_tool="get_status", wait=False)
            handle = await adapter(workflow_name="etl")
            result = await handle.await_completion(adapter)
        """
        logger.info("Executing MCP tool '%s' with params: %s", self.tool_name, kwargs)

        try:
            # Call the MCP provider
            result = await self.provider.call_tool_async(self.tool_name, kwargs)

            logger.debug("MCP tool '%s' returned result", self.tool_name)

            # Check if result is a pollable job
            if self._is_pollable_job(result):
                logger.info("Detected pollable job: %s", result.get("job_id"))

                # Create job handle
                handle = PollableJobHandle(
                    provider=self.provider.get_endpoint(),
                    job_id=result["job_id"],
                    job_type=result.get("job_type", "unknown"),
                    status_tool=self.status_tool,
                    result_tool=self.result_tool,
                    timeout=self.timeout_s,
                )

                # Automatic polling if wait=True
                if self.wait:
                    logger.info("Automatic polling enabled for job %s", handle.job_id)

                    # Create status adapter for polling
                    status_adapter = MCPToolAdapter(self.provider, self.status_tool)

                    return await handle.await_completion(
                        status_adapter, progress_callback=progress_callback
                    )
                logger.info("Returning job handle for manual polling: %s", handle.job_id)
                return handle

            # Not a pollable job - attempt auto-conversion
            if self.auto_convert and isinstance(result, dict):
                result = self._convert_to_artifact(result)

            return result

        except (JobTimeoutError, JobFailedError, JobCancelledError):
            # Let job errors propagate
            raise
        except MCPError as e:
            # Wrap MCP errors in adapter-specific exception
            logger.exception("MCP tool '%s' failed: %s", self.tool_name, e)
            raise MCPToolExecutionError(
                tool_name=self.tool_name,
                provider_endpoint=self.provider.get_endpoint(),
                original_error=e,
            ) from e
        except Exception as e:
            # Catch any other errors and wrap them
            logger.exception(
                f"Unexpected error executing MCP tool '{self.tool_name}': {e}",
            )
            raise MCPToolExecutionError(
                tool_name=self.tool_name,
                provider_endpoint=self.provider.get_endpoint(),
                original_error=e,
            ) from e

    def _convert_to_artifact(self, response: dict[str, Any]) -> Any | dict[str, Any]:
        """Convert MCP response to typed artifact.

        Uses the artifact registry to convert raw MCP responses to typed artifacts
        when a mapping is configured or can be auto-detected.

        Args:
            response: Raw MCP tool response

        Returns:
            Typed artifact instance or raw dict if conversion fails/disabled

        Example:
            # With explicit artifact_type
            adapter = MCPToolAdapter(provider, "pagerank", artifact_type="GraphMetricsArtifact")
            result = await adapter(graph=graph_data)
            # result is GraphMetricsArtifact instance

            # With auto-detection
            adapter = MCPToolAdapter(provider, "chunk_file", auto_convert=True)
            result = await adapter(file_path="src/utils.py")
            # result is ChunkArtifact instance if detected, else dict
        """
        try:
            # Use explicit provider_name if available, otherwise fall back to heuristic
            # Note: self.provider_name is set in __init__ and prefers explicit values
            provider_name = self.provider_name

            # Attempt conversion
            return convert_mcp_response(
                response=response,
                tool_name=self.tool_name,
                provider=provider_name,
                artifact_type=self.artifact_type,
                auto_detect=self.auto_convert,
            )

        except Exception as e:
            logger.warning(
                f"Auto-conversion failed for tool '{self.tool_name}': {e}. Returning raw dict."
            )
            return response

    def _is_pollable_job(self, result: Any) -> bool:
        """Check if result represents a pollable job.

        A result is considered a pollable job if:
        1. It's a dictionary with a 'job_id' field, AND
        2. A status_tool is configured

        Args:
            result: MCP tool result

        Returns:
            True if result is a pollable job
        """
        # Must have status_tool configured
        if not self.status_tool:
            return False

        # Must be a dict with job_id
        if not isinstance(result, dict):
            return False

        return "job_id" in result

    def get_metadata(self) -> MCPToolMetadata:
        """Get tool metadata for documentation and validation.

        Returns:
            MCPToolMetadata with tool information

        Raises:
            MCPToolNotFoundError: If tool metadata cannot be retrieved
        """
        if self._metadata is None:
            # Fetch tool definition from provider
            tools = self.provider.get_tools()

            for tool in tools:
                if tool["name"] == self.tool_name:
                    self._metadata = MCPToolMetadata(
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("input_schema", {}),
                        provider_endpoint=self.provider.get_endpoint(),
                    )
                    break

            if self._metadata is None:
                msg = f"Tool '{self.tool_name}' not found in provider"
                raise MCPToolNotFoundError(msg)

        return self._metadata

    def get_tool_definition(self) -> MCPToolDefinition:
        """Get the raw tool definition from the provider.

        Returns:
            MCPToolDefinition dictionary

        Raises:
            MCPToolNotFoundError: If tool not found
        """
        tools = self.provider.get_tools()

        for tool in tools:
            if tool["name"] == self.tool_name:
                return tool

        msg = f"Tool '{self.tool_name}' not found in provider"
        raise MCPToolNotFoundError(msg)


def create_mcp_tool_step(
    provider: MCPProvider,
    tool_name: str,
    status_tool: str | None = None,
    result_tool: str | None = None,
    wait: bool = False,
    timeout_s: float = 3600.0,
    artifact_type: str | None = None,
    auto_convert: bool = True,
    provider_name: str | None = None,
) -> Callable:
    """Factory function to create a callable MCP tool step for pipelines.

    This is a convenience function that creates an MCPToolAdapter and returns
    it as a callable. The returned function can be used directly in pipeline
    step execution.

    Enhanced to support automatic job polling for long-running operations.
    Enhanced to support automatic artifact conversion.

    Args:
        provider: MCP provider instance
        tool_name: Name of the tool to wrap
        status_tool: Optional tool name for polling job status
        result_tool: Optional tool name for retrieving job results
        wait: If True, automatically poll until completion
        timeout_s: Timeout for job polling in seconds
        artifact_type: Optional artifact type for auto-conversion
        auto_convert: Whether to attempt auto-conversion to artifacts
        provider_name: Optional explicit provider name (recommended for reliable artifact conversion)

    Returns:
        Async callable that executes the MCP tool

    Raises:
        MCPToolNotFoundError: If tool doesn't exist in provider

    Example:
        # Regular tool call
        provider = HTTPMCPProvider(...)
        search_tool = create_mcp_tool_step(provider, "search")
        result = await search_tool(query="test")

        # With automatic polling
        workflow_tool = create_mcp_tool_step(
            provider,
            "start_workflow",
            status_tool="get_workflow_status",
            wait=True
        )
        result = await workflow_tool(workflow_name="etl")

        # With auto-conversion and explicit provider name
        pagerank_tool = create_mcp_tool_step(
            provider,
            "pagerank",
            artifact_type="GraphMetricsArtifact",
            provider_name="networkx"  # Explicit name (recommended)
        )
        metrics = await pagerank_tool(graph=graph_data)
        # metrics is GraphMetricsArtifact, not dict
    """
    return MCPToolAdapter(
        provider,
        tool_name,
        status_tool=status_tool,
        result_tool=result_tool,
        wait=wait,
        timeout_s=timeout_s,
        artifact_type=artifact_type,
        auto_convert=auto_convert,
        provider_name=provider_name,
    )


def validate_mcp_tool_params(
    adapter: MCPToolAdapter, params: dict[str, Any]
) -> tuple[bool, str | None]:
    """Validate parameters against tool's input schema.

    This function validates parameters before execution and ENFORCES validation.
    Changed in FIX3-E to fail-close instead of fail-open for security and correctness.

    Args:
        adapter: MCP tool adapter
        params: Parameters to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.

    Raises:
        MCPToolExecutionError: If validation fails (when called in enforcement mode)

    Example:
        adapter = MCPToolAdapter(provider, "search")
        valid, error = validate_mcp_tool_params(adapter, {"query": "test"})
        if not valid:
            raise MCPToolExecutionError(
                adapter.tool_name,
                adapter.provider.get_endpoint(),
                ValueError(error)
            )
    """
    try:
        metadata = adapter.get_metadata()
        schema = metadata.input_schema

        # Check if schema defines required properties
        required = schema.get("required", [])

        for req_field in required:
            if req_field not in params:
                error_msg = (
                    f"Missing required parameter '{req_field}' for tool '{adapter.tool_name}' "
                    f"from provider '{adapter.provider_name}'. "
                    f"Required parameters: {required}"
                )
                return False, error_msg

        return True, None

    except MCPToolNotFoundError:
        # If tool metadata can't be retrieved, that's a hard error
        error_msg = (
            f"Cannot validate params: tool '{adapter.tool_name}' not found in provider "
            f"'{adapter.provider_name}'"
        )
        return False, error_msg
    except Exception as e:
        # Changed from fail-open to fail-close for FIX3-E
        # If we can't validate due to unexpected error, reject rather than allow
        error_msg = (
            f"Parameter validation failed for tool '{adapter.tool_name}': {type(e).__name__}: {e!s}"
        )
        logger.exception(error_msg)
        return False, error_msg
