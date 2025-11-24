"""Base classes and protocols for MCP (Model Context Protocol) adapters.

MCP adapters enable communication with MCP servers that provide LLM and embedding
services over standardized protocols.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseMCPAdapter(ABC):
    """Abstract base class for MCP adapters."""

    def __init__(
        self,
        provider_name: str,
        endpoint: str,
        timeout_seconds: int = 30,
        **kwargs,
    ) -> None:
        """Initialize MCP adapter.

        Args:
            provider_name: Provider identifier
            endpoint: MCP server endpoint URL
            timeout_seconds: Request timeout in seconds
            **kwargs: Additional adapter-specific configuration
        """
        self.provider_name = provider_name
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.config = kwargs

        # Connection state
        self._connected = False
        self._client = None

    @abstractmethod
    async def connect(self) -> Any:
        """Establish connection to MCP server.

        Raises:
            ConnectionError: If connection fails
        """

    @abstractmethod
    async def disconnect(self) -> Any:
        """Close connection to MCP server."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if MCP server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """

    def is_connected(self) -> bool:
        """Check if adapter is connected.

        Returns:
            Connection status
        """
        return self._connected

    def get_provider_info(self) -> dict[str, Any]:
        """Get provider information.

        Returns:
            Dictionary with provider metadata
        """
        return {
            "provider": self.provider_name,
            "endpoint": self.endpoint,
            "connected": self._connected,
            "config": self.config,
        }


class MCPError(Exception):
    """Base exception for MCP-related errors."""


class MCPConnectionError(MCPError):
    """Exception raised when MCP connection fails."""


class MCPRequestError(MCPError):
    """Exception raised when MCP request fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize MCP request error.

        Args:
            message: Error message
            status_code: HTTP status code (if applicable)
        """
        super().__init__(message)
        self.status_code = status_code


class MCPTimeoutError(MCPError):
    """Exception raised when MCP request times out."""
