"""Workspace-aware MCP server implementation.

This module provides the main MCP server wrapper that:
1. Loads a workspace YAML configuration
2. Builds providers and runtime from workspace settings
3. Registers MCP tools based on workspace.mcp.tools
4. Maps tool calls to WorkspaceRuntime.run_pipeline()

Architecture:
- LLM → Sibyl MCP → WorkspaceRuntime → Techniques → Providers (incl. MCP providers)
- Does NOT expose sub-MCPs directly
- All calls go through the workspace runtime

Example:
    # Start MCP server with workspace
    python -m sibyl.server.mcp_server --workspace config/workspaces/example_local.yaml

    # Or use CLI entry point
    sibyl mcp serve --workspace config/workspaces/example_local.yaml
"""

import asyncio
import logging
import sys
from collections.abc import Iterable
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    Server = None
    stdio_server = None
    Tool = None
    MCP_AVAILABLE = False

from sibyl.runtime.pipeline import PipelineResult, WorkspaceRuntime
from sibyl.runtime.providers import build_providers
from sibyl.server.schemas import validate_pipeline_input
from sibyl.workspace import WorkspaceLoadError, load_workspace
from sibyl.workspace.schema import MCPToolConfig

logger = logging.getLogger(__name__)


class WorkspaceMCPServer:
    """MCP server backed by a Sibyl workspace configuration.

    This server loads a workspace, builds the runtime infrastructure,
    and exposes workspace pipelines as MCP tools.

    Attributes:
        workspace: Loaded workspace configuration
        providers: Provider registry built from workspace
        runtime: Workspace runtime for executing pipelines
        server: MCP server instance
    """

    def __init__(
        self,
        workspace_path: str,
        server_name: str | None = None,
    ) -> None:
        """Initialize workspace MCP server.

        Args:
            workspace_path: Path to workspace YAML file
            server_name: Optional override for MCP server name

        Raises:
            WorkspaceLoadError: If workspace cannot be loaded
            ImportError: If MCP package is not available
        """
        if not MCP_AVAILABLE:
            msg = "MCP package not installed. Install with: pip install mcp"
            raise ImportError(msg)

        # Load workspace configuration
        logger.info("Loading workspace from: %s", workspace_path)
        self.workspace = load_workspace(workspace_path)
        logger.info(
            f"Loaded workspace '{self.workspace.name}' with "
            f"{len(self.workspace.pipelines)} pipelines"
        )

        # Build providers from workspace
        logger.info("Building providers from workspace configuration")
        self.providers = build_providers(self.workspace)
        logger.info("Built %s provider instances", len(self.providers._providers))

        # Create workspace runtime
        logger.info("Initializing workspace runtime")
        self.runtime = WorkspaceRuntime(self.workspace, self.providers)
        logger.info("Runtime initialized with %s shops", len(self.runtime.shops))

        # Create MCP server
        mcp_name = server_name or self.workspace.mcp.server_name or "sibyl-workspace"
        self.server = Server(mcp_name)
        logger.info("Created MCP server: %s", mcp_name)

        # Register MCP endpoints
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools from workspace configuration."""

        # Register list_tools handler
        @self.server.list_tools()
        async def list_tools() -> Iterable[Tool]:
            """List all tools defined in the workspace."""
            return self._build_tool_list()

        # Register call_tool handler
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
            """Handle tool invocation by mapping to pipeline execution."""
            return await self._handle_tool_call(name, arguments)

        logger.info("Registered %s MCP tools from workspace", len(self.workspace.mcp.tools))

    def _build_tool_list(self) -> list[Tool]:
        """Build list of MCP tools from workspace configuration.

        Returns:
            List of MCP Tool objects
        """
        tools = []

        for tool_config in self.workspace.mcp.tools:
            # Build input schema
            input_schema = tool_config.input_schema or {
                "type": "object",
                "properties": {},
            }

            tool = Tool(
                name=tool_config.name,
                description=tool_config.description,
                inputSchema=input_schema,
            )
            tools.append(tool)

            logger.debug(
                f"Registered tool '{tool_config.name}' -> pipeline '{tool_config.pipeline}'"
            )

        return tools

    async def _handle_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[Any]:
        """Handle tool invocation by executing the corresponding pipeline.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool input parameters

        Returns:
            List containing tool result (MCP format)

        Raises:
            ValueError: If tool not found in workspace or validation fails
        """
        logger.info("Tool call: %s with arguments: %s", tool_name, arguments)

        # Find tool configuration
        tool_config = self._find_tool_config(tool_name)
        if tool_config is None:
            available = [t.name for t in self.workspace.mcp.tools]
            msg = f"Tool '{tool_name}' not found. Available tools: {available}"
            raise ValueError(msg)

        # Get pipeline name
        pipeline_name = tool_config.pipeline

        # Validate and sanitize input arguments
        try:
            # Trim whitespace from string values
            sanitized_args = self._sanitize_arguments(arguments)

            # Validate against schema (if available for this pipeline)
            validated_input = validate_pipeline_input(pipeline_name, **sanitized_args)
            # Convert Pydantic model to dict for pipeline execution
            validated_args = validated_input.dict()

            logger.info("Input validation passed for pipeline '%s'", pipeline_name)
        except ValueError as e:
            # Pipeline doesn't have a schema, use raw arguments (with sanitization)
            logger.debug(
                f"No schema defined for pipeline '{pipeline_name}', skipping validation: {e}"
            )
            validated_args = self._sanitize_arguments(arguments)
        except Exception as e:
            # Validation failed
            logger.exception(
                f"Input validation failed for pipeline '{pipeline_name}': {e}",
                extra={"arguments": arguments},
            )
            # Return validation error to user
            return [
                {
                    "type": "text",
                    "text": f"Input validation failed: {e}\n\n"
                    f"Please check your input parameters and try again.",
                }
            ]

        logger.info("Executing pipeline '%s' for tool '%s'", pipeline_name, tool_name)

        # Execute pipeline with validated arguments using the new v2 API
        result: PipelineResult = await self.runtime.run_pipeline_v2(
            pipeline_name,
            **validated_args,
        )

        if result.ok:
            logger.info(
                f"Pipeline '{pipeline_name}' completed successfully",
                extra={
                    "trace_id": result.trace_id,
                    "duration_ms": result.duration_ms,
                },
            )

            # Format success result for MCP
            return [
                {
                    "type": "text",
                    "text": self._format_success_result(result),
                }
            ]
        logger.error(
            f"Pipeline '{pipeline_name}' failed: {result.error.type} - {result.error.message}",
            extra={
                "trace_id": result.trace_id,
                "duration_ms": result.duration_ms,
                "error_type": result.error.type,
            },
        )

        # Format error result for MCP
        # Return user-friendly error message, but include trace_id for support
        return [
            {
                "type": "text",
                "text": self._format_error_result(result),
            }
        ]

    def _find_tool_config(self, tool_name: str) -> MCPToolConfig | None:
        """Find tool configuration by name.

        Args:
            tool_name: Tool name to search for

        Returns:
            Tool configuration or None if not found
        """
        for tool_config in self.workspace.mcp.tools:
            if tool_config.name == tool_name:
                return tool_config
        return None

    def _sanitize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Sanitize input arguments before validation.

        Performs basic sanitization:
        - Trim whitespace from string values
        - Remove None values
        - Ensure numeric types are within reasonable bounds

        Args:
            arguments: Raw input arguments

        Returns:
            Sanitized arguments dictionary
        """
        sanitized = {}

        for key, value in arguments.items():
            # Skip None values
            if value is None:
                continue

            # Trim whitespace from strings
            if isinstance(value, str):
                sanitized[key] = value.strip()
            # Ensure integers are within reasonable bounds (prevent overflow)
            elif isinstance(value, int):
                # Cap at reasonable limits to prevent resource exhaustion
                sanitized[key] = max(-2147483648, min(2147483647, value))
            else:
                sanitized[key] = value

        return sanitized

    def _format_success_result(self, result: PipelineResult) -> str:
        """Format successful pipeline result for MCP response.

        Args:
            result: PipelineResult with success status

        Returns:
            Formatted text representation
        """
        output_parts = []

        # Add pipeline metadata
        if "pipeline_name" in result.data:
            output_parts.append(f"Pipeline: {result.data['pipeline_name']}")

        # Add execution metadata
        if result.duration_ms is not None:
            output_parts.append(f"Duration: {result.duration_ms:.2f}ms")

        # Add last result if present
        if "last_result" in result.data:
            output_parts.append(f"\nResult:\n{result.data['last_result']}")

        # Add any other relevant context
        exclude_keys = {
            "pipeline_name",
            "pipeline_shop",
            "last_result",
            "success",
            "trace_id",
        }
        other_data = {k: v for k, v in result.data.items() if k not in exclude_keys}

        if other_data:
            import json  # can be moved to top

            output_parts.append(f"\nAdditional Data:\n{json.dumps(other_data, indent=2)}")

        # Add trace ID for debugging (at the bottom)
        if result.trace_id:
            output_parts.append(f"\n[Trace ID: {result.trace_id}]")

        return "\n".join(output_parts) if output_parts else "Pipeline completed successfully"

    def _format_error_result(self, result: PipelineResult) -> str:
        """Format error pipeline result for MCP response.

        Args:
            result: PipelineResult with error status

        Returns:
            Formatted error message (user-friendly, no stack traces)
        """
        error = result.error
        output_parts = []

        # User-friendly error message
        output_parts.append(f"Pipeline execution failed: {error.message}")

        # Add error type for context
        output_parts.append(f"\nError Type: {error.type}")

        # Add relevant details (but filter out sensitive info)
        if error.details:
            # Filter out stack traces and internal details
            safe_details = {
                k: v for k, v in error.details.items() if k not in {"stack_trace", "exception"}
            }
            if safe_details:
                import json  # can be moved to top

                output_parts.append(f"\nDetails:\n{json.dumps(safe_details, indent=2)}")

        # Add trace ID for support
        if result.trace_id:
            output_parts.append(
                f"\n[Trace ID: {result.trace_id}] (Include this ID when reporting issues)"
            )

        return "\n".join(output_parts)

    async def run(self) -> None:
        """Run the MCP server using stdio transport.

        This is the main entry point for starting the server.
        """
        logger.info("Starting Sibyl workspace MCP server")

        async with stdio_server() as (read, write):
            await self.server.run(read, write)


def serve_mcp(workspace_path: str, server_name: str | None = None) -> None:
    """Start MCP server with workspace configuration.

    This is the main entry point for the CLI command:
    sibyl mcp serve --workspace config/workspaces/example_local.yaml

    Args:
        workspace_path: Path to workspace YAML file
        server_name: Optional override for MCP server name

    Raises:
        WorkspaceLoadError: If workspace cannot be loaded
        ImportError: If MCP package is not available
    """
    global _global_server

    try:
        # Create and run server
        _global_server = WorkspaceMCPServer(workspace_path, server_name)
        asyncio.run(_global_server.run())

    except WorkspaceLoadError as e:
        logger.exception("Failed to load workspace: %s", e)
        sys.exit(1)

    except ImportError as e:
        logger.exception("MCP dependencies not available: %s", e)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)

    except Exception as e:
        logger.exception("Server error: %s", e)
        sys.exit(1)


def main() -> None:
    """CLI entry point for workspace MCP server.

    Supports command-line arguments:
    --workspace: Path to workspace YAML file (optional if SIBYL_WORKSPACE_FILE is set)
    --server-name: Optional MCP server name override

    Workspace can be specified via:
    1. --workspace CLI flag (highest priority)
    2. SIBYL_WORKSPACE_FILE environment variable
    """
    import argparse  # can be moved to top
    import os  # can be moved to top

    parser = argparse.ArgumentParser(
        description="Sibyl Workspace MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with workspace (CLI flag)
  sibyl mcp serve --workspace config/workspaces/example_local.yaml

  # Start server with environment variable
  export SIBYL_WORKSPACE_FILE=config/workspaces/prod_web_research.yaml
  sibyl mcp serve

  # With custom server name
  sibyl mcp serve --workspace my_workspace.yaml --server-name my-server

  # Multiple workspaces in parallel (different terminal sessions)
  Terminal 1: SIBYL_WORKSPACE_FILE=workspace_a.yaml sibyl mcp serve
  Terminal 2: SIBYL_WORKSPACE_FILE=workspace_b.yaml sibyl mcp serve
        """,
    )

    parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="Path to workspace YAML configuration file (overrides SIBYL_WORKSPACE_FILE env var)",
    )

    parser.add_argument(
        "--server-name",
        type=str,
        help="Optional MCP server name override",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Determine workspace path with priority order:
    # 1. CLI flag (--workspace)
    # 2. SIBYL_WORKSPACE_FILE environment variable
    workspace_path = args.workspace or os.getenv("SIBYL_WORKSPACE_FILE")

    if not workspace_path:
        parser.error(
            "No workspace path provided. Use --workspace flag or set "
            "SIBYL_WORKSPACE_FILE environment variable"
        )

    # Start server
    serve_mcp(workspace_path, args.server_name)


def run_stdio(workspace_path: str) -> None:
    """Entry point for stdio transport.

    Args:
        workspace_path: Path to workspace YAML file
    """
    serve_mcp(workspace_path)


__all__ = [
    "WorkspaceMCPServer",
    "run_stdio",
    "serve_mcp",
]


if __name__ == "__main__":
    main()
