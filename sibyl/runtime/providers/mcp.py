"""MCP Provider implementations for external Model Context Protocol servers.

This module provides concrete implementations of the MCPProvider protocol
for communicating with external MCP servers via different transports.
"""

import logging
from typing import Any

import httpx

from sibyl.core.protocols.infrastructure.mcp import (
    MCPToolDefinition,
    MCPToolNotFoundError,
)

logger = logging.getLogger(__name__)


class HTTPMCPProvider:
    """HTTP-based MCP provider implementation.

    Communicates with external MCP servers via HTTP/JSON-RPC.
    """

    def __init__(
        self,
        endpoint: str,
        tools: list[str],
        timeout_s: int = 30,
        auth: dict[str, str] | None = None,
    ) -> None:
        """Initialize HTTP MCP provider.

        Args:
            endpoint: HTTP endpoint URL for the MCP server
            tools: List of tool names to expose from this provider
            timeout_s: Timeout in seconds for HTTP requests
            auth: Optional authentication configuration (e.g., {"type": "bearer", "token": "..."})
        """
        self.endpoint = endpoint
        self.tools = tools
        self.timeout_s = timeout_s
        self.auth = auth
        self._client: httpx.AsyncClient | None = None
        self._available_tools: list[MCPToolDefinition] | None = None

    def get_tools(self) -> list[MCPToolDefinition]:
        """Get list of available tools from this MCP provider.

        Returns:
            List of tool definitions

        Raises:
            MCPConnectionError: If unable to connect to MCP server
            MCPError: If MCP server returns an error
        """
        # For now, return a placeholder structure based on configured tool names
        # The actual implementation will be completed in a future version
        if self._available_tools is None:
            self._available_tools = [
                {
                    "name": tool_name,
                    "description": f"Tool {tool_name} from MCP provider at {self.endpoint}",
                    "input_schema": {"type": "object", "properties": {}},
                }
                for tool_name in self.tools
            ]
        return self._available_tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on this MCP provider synchronously.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            NotImplementedError: Sync version not implemented yet (use async)
        """
        msg = (
            "Synchronous MCP calls not yet implemented. Use call_tool_async() instead. "
            "Full MCP wire protocol implementation will be completed in a future version."
        )
        raise NotImplementedError(msg)

    async def call_tool_async(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on this MCP provider asynchronously.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as a dictionary

        Raises:
            MCPConnectionError: If unable to connect to MCP server
            MCPToolNotFoundError: If tool doesn't exist
            MCPToolError: If tool execution fails
            NotImplementedError: Wire protocol to be implemented in a future version
        """
        # Validate tool exists
        if tool_name not in self.tools:
            msg = f"Tool '{tool_name}' not found in provider. Available: {self.tools}"
            raise MCPToolNotFoundError(msg)

        # Clear NotImplementedError with actionable context
        msg = (
            f"HTTPMCPProvider.call_tool_async is not implemented yet. "
            f"Use StdIOMCPProvider or mocks only. "
            f"Full HTTP MCP wire protocol will be completed in a future version. "
            f"(Attempted to call tool '{tool_name}' at {self.endpoint})"
        )
        raise NotImplementedError(msg)

    def health_check(self) -> bool:
        """Check if MCP provider is healthy and responsive.

        Returns:
            False (provider not implemented yet)

        Note:
            This returns False because HTTPMCPProvider is not yet implemented.
            Full health check will be available in a future version.
        """
        # Return False to indicate this provider is not ready for use
        logger.debug(
            f"HTTPMCPProvider health check returning False (not implemented). "
            f"Endpoint: {self.endpoint}"
        )
        return False

    def get_endpoint(self) -> str:
        """Get the endpoint URL for this MCP provider.

        Returns:
            Endpoint URL
        """
        return self.endpoint

    def get_timeout(self) -> int:
        """Get the timeout in seconds for MCP operations.

        Returns:
            Timeout in seconds
        """
        return self.timeout_s

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout_s)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None


class StdIOMCPProvider:
    """Stdio-based MCP provider implementation.

    Communicates with external MCP servers via stdin/stdout JSON-RPC.
    To be implemented in a future version.
    """

    def __init__(
        self,
        command: str,
        tools: list[str],
        timeout_s: int = 30,
    ) -> None:
        """Initialize Stdio MCP provider.

        Args:
            command: Command to execute for the MCP server
            tools: List of tool names to expose from this provider
            timeout_s: Timeout in seconds for operations
        """
        self.command = command
        self.tools = tools
        self.timeout_s = timeout_s

    def get_tools(self) -> list[MCPToolDefinition]:
        """Get list of available tools."""
        return [
            {
                "name": tool_name,
                "description": f"Tool {tool_name} from stdio MCP provider",
                "input_schema": {"type": "object", "properties": {}},
            }
            for tool_name in self.tools
        ]

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool synchronously."""
        msg = "Stdio MCP provider not yet implemented. Will be completed in a future version."
        raise NotImplementedError(msg)

    async def call_tool_async(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool asynchronously."""
        msg = "Stdio MCP provider not yet implemented. Will be completed in a future version."
        raise NotImplementedError(msg)

    def health_check(self) -> bool:
        """Check if MCP provider is healthy.

        Returns:
            False (provider not implemented yet)

        Note:
            This is a stub provider until full implementation.
            Always returns False to indicate it's not ready for production use.
        """
        return False  # Not implemented yet

    def get_endpoint(self) -> str:
        """Get the command string for this provider."""
        return self.command

    def get_timeout(self) -> int:
        """Get the timeout in seconds."""
        return self.timeout_s
