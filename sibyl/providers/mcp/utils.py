"""Utilities for MCP communication."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """HTTP client for MCP server communication."""

    def __init__(self, endpoint: str, timeout_seconds: int = 30) -> None:
        """Initialize MCP client.

        Args:
            endpoint: MCP server endpoint URL
            timeout_seconds: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = None

    async def _get_session(self) -> Any:
        """Get or create HTTP session.

        Returns:
            aiohttp ClientSession
        """
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
                )
            except ImportError:
                msg = "aiohttp required for MCP. Install with: pip install aiohttp"
                raise ImportError(msg) from None

        return self._session

    async def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to MCP server.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (relative to endpoint)
            data: Request body data
            headers: Request headers

        Returns:
            Response JSON

        Raises:
            MCPConnectionError: If connection fails
            MCPRequestError: If request fails
            MCPTimeoutError: If request times out
        """
        from .base import MCPConnectionError, MCPRequestError, MCPTimeoutError

        session = await self._get_session()
        url = f"{self.endpoint}/{path.lstrip('/')}"

        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        try:
            async with session.request(method, url, json=data, headers=request_headers) as response:
                # Check status
                if response.status >= 500:
                    msg = f"MCP server error (status {response.status}): {await response.text()}"
                    raise MCPConnectionError(msg)
                if response.status >= 400:
                    msg = f"MCP request failed (status {response.status}): {await response.text()}"
                    raise MCPRequestError(
                        msg,
                        status_code=response.status,
                    )

                # Parse response
                return await response.json()

        except TimeoutError:
            msg = f"MCP request timed out after {self.timeout_seconds}s"
            raise MCPTimeoutError(msg) from None
        except Exception as e:
            if isinstance(e, (MCPConnectionError, MCPRequestError, MCPTimeoutError)):
                raise
            msg = f"MCP connection failed: {e}"
            raise MCPConnectionError(msg) from e

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
