"""
MCP Provider protocol interfaces for external Model Context Protocol servers.

These protocols define the contracts for MCP provider implementations.
Application services depend only on these interfaces, not concrete implementations.
"""

from typing import Any, Protocol, TypedDict, runtime_checkable


class MCPToolDefinition(TypedDict, total=False):
    """Definition of an MCP tool."""

    name: str  # Tool name
    description: str  # Tool description
    input_schema: dict[str, Any]  # JSON schema for tool inputs


@runtime_checkable
class MCPProvider(Protocol):
    """Abstract interface for external MCP providers.

    This protocol defines the contract for communicating with external
    Model Context Protocol servers (e.g., via HTTP or stdio).
    """

    def get_tools(self) -> list[MCPToolDefinition]:
        """Get list of available tools from this MCP provider.

        Returns:
            List of tool definitions with name, description, and input schema

        Raises:
            MCPConnectionError: If unable to connect to MCP server
            MCPError: If MCP server returns an error
        """
        ...

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on this MCP provider.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary

        Returns:
            Tool result as a dictionary

        Raises:
            MCPConnectionError: If unable to connect to MCP server
            MCPToolNotFoundError: If tool doesn't exist
            MCPToolError: If tool execution fails
            MCPError: Generic MCP error
            TimeoutError: If request exceeds timeout
        """
        ...

    async def call_tool_async(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Async version of call_tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary

        Returns:
            Tool result as a dictionary

        Raises:
            Same as call_tool()
        """
        ...

    def health_check(self) -> bool:
        """Check if MCP provider is healthy and responsive.

        Returns:
            True if provider is healthy, False otherwise
        """
        ...

    def get_endpoint(self) -> str:
        """Get the endpoint/connection string for this MCP provider.

        Returns:
            Endpoint URL or command string
        """
        ...

    def get_timeout(self) -> int:
        """Get the timeout in seconds for MCP operations.

        Returns:
            Timeout in seconds
        """
        ...


class MCPError(Exception):
    """Base exception for MCP errors."""


class MCPConnectionError(MCPError):
    """Exception raised when unable to connect to MCP server."""


class MCPToolNotFoundError(MCPError):
    """Exception raised when requested tool doesn't exist."""


class MCPToolError(MCPError):
    """Exception raised when tool execution fails."""
