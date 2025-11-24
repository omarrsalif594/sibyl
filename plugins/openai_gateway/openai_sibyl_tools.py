"""
OpenAI Gateway: Sibyl Tools Adapter

This module provides an adapter layer that exposes Sibyl pipelines as OpenAI-style tools.
It enables integration with OpenAI SDK clients, ChatGPT, and other OpenAI-compatible frontends.

Architecture:
- Reads tool mappings from tools_mapping.yaml
- Converts Sibyl pipeline definitions to OpenAI tool schemas
- Handles tool call payloads and routes them to appropriate pipelines
- Returns results in OpenAI-compatible format

Usage:
    from plugins.openai_gateway.openai_sibyl_tools import OpenAISibylAdapter

    # Initialize adapter
    adapter = OpenAISibylAdapter()

    # Get OpenAI tool definitions
    tools = adapter.export_tool_definitions()

    # Handle tool call from OpenAI
    result = await adapter.handle_tool_call(
        tool_name="northwind_revenue_analysis",
        arguments={"question": "Why is revenue down in Q3?", "time_period": "2024-Q3"}
    )
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.runtime import WorkspaceRuntime, load_workspace_runtime

logger = logging.getLogger(__name__)


class ToolMappingError(Exception):
    """Raised when tool mapping configuration is invalid."""


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""


class OpenAISibylAdapter:
    """
    Adapter that exposes Sibyl pipelines as OpenAI-style tools.

    This adapter:
    1. Loads tool mappings from configuration
    2. Converts pipeline schemas to OpenAI tool definitions
    3. Routes tool calls to appropriate Sibyl pipelines
    4. Handles async execution and error handling

    Attributes:
        config_path: Path to tools_mapping.yaml
        tools_config: Loaded tool configuration
        workspace_cache: Cache of WorkspaceRuntime instances
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize the OpenAI Sibyl adapter.

        Args:
            config_path: Path to tools_mapping.yaml. If None, uses default location.

        Raises:
            ToolMappingError: If configuration file is invalid or missing
        """
        if config_path is None:
            # Default to same directory as this module
            module_dir = Path(__file__).parent
            config_path = module_dir / "tools_mapping.yaml"

        self.config_path = config_path
        self.tools_config = self._load_config()
        self.workspace_cache: dict[str, WorkspaceRuntime] = {}

        logger.info(
            "OpenAI Sibyl Adapter initialized with %s tools", len(self.tools_config["tools"])
        )

    def _load_config(self) -> dict[str, Any]:
        """
        Load and validate tools mapping configuration.

        Returns:
            Parsed configuration dictionary

        Raises:
            ToolMappingError: If config is invalid or missing
        """
        if not self.config_path.exists():
            msg = f"Config file not found: {self.config_path}"
            raise ToolMappingError(msg)

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Failed to parse config YAML: {e}"
            raise ToolMappingError(msg) from e
        except Exception as e:
            msg = f"Failed to load config: {e}"
            raise ToolMappingError(msg) from e
        else:
            if not config or "tools" not in config:
                msg = "Config must contain 'tools' key"
                raise ToolMappingError(msg)

            # Validate each tool definition
            for tool_name, tool_def in config["tools"].items():
                required_fields = ["workspace", "pipeline", "description", "params_schema"]
                for field in required_fields:
                    if field not in tool_def:
                        msg = f"Tool '{tool_name}' missing required field: {field}"
                        raise ToolMappingError(msg)

            return config

    def export_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Export Sibyl pipelines as OpenAI tool definitions.

        Converts the tool mapping configuration into the format expected by
        OpenAI's function calling API.

        Returns:
            List of tool definitions in OpenAI format:
            [
                {
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "description": "Tool description",
                        "parameters": {
                            "type": "object",
                            "properties": {...},
                            "required": [...]
                        }
                    }
                },
                ...
            ]

        Example:
            >>> adapter = OpenAISibylAdapter()
            >>> tools = adapter.export_tool_definitions()
            >>> # Pass tools to OpenAI API
            >>> response = client.chat.completions.create(
            ...     model="gpt-4",
            ...     messages=[{"role": "user", "content": "Analyze Q3 revenue"}],
            ...     tools=tools
            ... )
        """
        tool_definitions = []

        for tool_name, tool_config in self.tools_config["tools"].items():
            # Convert params_schema to OpenAI format
            properties = {}
            required = []

            for param_name, param_def in tool_config["params_schema"].items():
                # Extract parameter definition
                param_type = param_def.get("type", "string")
                param_desc = param_def.get("description", "")
                is_required = param_def.get("required", False)

                # Build property definition
                prop = {
                    "type": param_type,
                    "description": param_desc,
                }

                # Add optional fields
                if "default" in param_def:
                    prop["default"] = param_def["default"]
                if "enum" in param_def:
                    prop["enum"] = param_def["enum"]
                if "minimum" in param_def:
                    prop["minimum"] = param_def["minimum"]
                if "maximum" in param_def:
                    prop["maximum"] = param_def["maximum"]
                if "items" in param_def:
                    prop["items"] = param_def["items"]
                if "properties" in param_def:
                    prop["properties"] = param_def["properties"]

                properties[param_name] = prop

                if is_required:
                    required.append(param_name)

            # Build OpenAI tool definition
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_config["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            tool_definitions.append(tool_def)

        logger.debug("Exported %s tool definitions", len(tool_definitions))
        return tool_definitions

    def get_tool_config(self, tool_name: str) -> dict[str, Any]:
        """
        Get configuration for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool configuration dictionary

        Raises:
            ToolMappingError: If tool not found
        """
        if tool_name not in self.tools_config["tools"]:
            available = ", ".join(self.tools_config["tools"].keys())
            msg = f"Tool '{tool_name}' not found. Available tools: {available}"
            raise ToolMappingError(msg)

        return self.tools_config["tools"][tool_name]

    def _get_workspace_runtime(self, workspace_path: str) -> WorkspaceRuntime:
        """
        Get or create a workspace runtime instance.

        Uses caching to avoid reloading the same workspace multiple times.

        Args:
            workspace_path: Path to workspace configuration

        Returns:
            WorkspaceRuntime instance

        Raises:
            ToolExecutionError: If workspace cannot be loaded
        """
        if workspace_path in self.workspace_cache:
            return self.workspace_cache[workspace_path]

        try:
            runtime = load_workspace_runtime(workspace_path)
            self.workspace_cache[workspace_path] = runtime
            logger.debug("Loaded workspace runtime: %s", workspace_path)
            return runtime
        except Exception as e:
            msg = f"Failed to load workspace '{workspace_path}': {e}"
            raise ToolExecutionError(msg) from e

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle an OpenAI tool call by executing the corresponding Sibyl pipeline.

        This is the main entry point for processing tool calls from OpenAI clients.
        It:
        1. Looks up the tool configuration
        2. Loads the appropriate workspace
        3. Executes the pipeline with provided arguments
        4. Returns results in OpenAI-compatible format

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool parameters (from OpenAI function call)

        Returns:
            Dictionary with execution results:
            {
                "success": bool,
                "result": Any,  # Pipeline output
                "metadata": {
                    "tool_name": str,
                    "pipeline_name": str,
                    "workspace": str,
                    "execution_time_ms": float,
                },
                "error": str | None  # Only present if success=False
            }

        Raises:
            ToolMappingError: If tool not found or configuration invalid
            ToolExecutionError: If pipeline execution fails

        Example:
            >>> adapter = OpenAISibylAdapter()
            >>> result = await adapter.handle_tool_call(
            ...     tool_name="northwind_revenue_analysis",
            ...     arguments={
            ...         "question": "Why is revenue down in Q3?",
            ...         "time_period": "2024-Q3"
            ...     }
            ... )
            >>> if result["success"]:
            ...     print(result["result"]["analysis"])
        """
        import time  # noqa: PLC0415

        start_time = time.time()

        try:
            # Get tool configuration
            tool_config = self.get_tool_config(tool_name)

            workspace_path = tool_config["workspace"]
            pipeline_name = tool_config["pipeline"]

            logger.info("Executing tool '%s' -> pipeline '%s'", tool_name, pipeline_name)
            logger.debug("Arguments: %s", arguments)

            # Get workspace runtime
            runtime = self._get_workspace_runtime(workspace_path)

            # Execute pipeline
            result = await runtime.run_pipeline(pipeline_name, **arguments)

            execution_time_ms = (time.time() - start_time) * 1000

            # Format response
            response = {
                "success": True,
                "result": result,
                "metadata": {
                    "tool_name": tool_name,
                    "pipeline_name": pipeline_name,
                    "workspace": workspace_path,
                    "execution_time_ms": execution_time_ms,
                },
            }

            logger.info("Tool '%s' completed successfully in %sms", tool_name, execution_time_ms)
            return response

        except ToolMappingError as e:
            logger.exception("Tool mapping error: %s", e)
            raise

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.exception("Tool execution failed: %s", e)

            # Return error in OpenAI-compatible format
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "tool_name": tool_name,
                    "execution_time_ms": execution_time_ms,
                },
            }

    def list_tools(self) -> list[str]:
        """
        List all available tool names.

        Returns:
            List of tool names
        """
        return list(self.tools_config["tools"].keys())

    def get_tool_description(self, tool_name: str) -> str:
        """
        Get human-readable description of a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool description

        Raises:
            ToolMappingError: If tool not found
        """
        tool_config = self.get_tool_config(tool_name)
        return tool_config["description"]


# Convenience functions for direct use
def export_tool_definitions(config_path: Path | None = None) -> list[dict[str, Any]]:
    """
    Export Sibyl pipelines as OpenAI tool definitions.

    Convenience function that creates an adapter and exports tool definitions.

    Args:
        config_path: Optional path to tools_mapping.yaml

    Returns:
        List of OpenAI tool definitions

    Example:
        >>> from plugins.openai_gateway.openai_sibyl_tools import export_tool_definitions
        >>> tools = export_tool_definitions()
        >>> # Use with OpenAI SDK
        >>> import openai
        >>> response = openai.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Analyze revenue"}],
        ...     tools=tools
        ... )
    """
    adapter = OpenAISibylAdapter(config_path)
    return adapter.export_tool_definitions()


async def handle_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    config_path: Path | None = None,
) -> dict[str, Any]:
    """
    Handle an OpenAI tool call.

    Convenience function that creates an adapter and handles a tool call.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool parameters
        config_path: Optional path to tools_mapping.yaml

    Returns:
        Tool execution results

    Example:
        >>> from plugins.openai_gateway.openai_sibyl_tools import handle_tool_call
        >>> result = await handle_tool_call(
        ...     tool_name="northwind_revenue_analysis",
        ...     arguments={"question": "Why is revenue down?"}
        ... )
        >>> print(result["result"])
    """
    adapter = OpenAISibylAdapter(config_path)
    return await adapter.handle_tool_call(tool_name, arguments)


__all__ = [
    "OpenAISibylAdapter",
    "ToolExecutionError",
    "ToolMappingError",
    "export_tool_definitions",
    "handle_tool_call",
]
