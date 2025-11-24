"""
Profile-aware stdio transport for MCP.

This implementation is intentionally minimal and defers all tool definitions to
catalog modules so the transport layer stays domain-neutral.
"""

import asyncio
import logging
import os
from collections.abc import Iterable
from typing import Any, Never

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool
except ImportError:  # pragma: no cover - optional dependency
    Server = None
    stdio_server = None
    Tool = None


logger = logging.getLogger(__name__)


class _StubServer:
    """Fallback server used when MCP dependencies are unavailable."""

    def __init__(self, name: str) -> None:
        self.name = name

    def list_tools(self) -> Any:  # type: ignore[override]
        def decorator(func) -> Any:
            return func

        return decorator

    def run(self, *args: Any, **kwargs: Any) -> Never:  # pragma: no cover - runtime guard
        msg = "mcp package not installed; stdio transport is unavailable"
        raise ImportError(msg)


server = Server("sibyl") if Server else _StubServer("sibyl")


def _build_tools_from_catalog(catalog: dict[str, dict[str, Any]]) -> list[Any]:
    if Tool is None:
        return []

    tools: list[Tool] = []
    for name, meta in catalog.items():
        tools.append(
            Tool(
                name=name,
                description=meta.get("description", ""),
                inputSchema=meta.get("parameters", {}),
            )
        )
    return tools


def _load_tools_for_profile() -> list[Any]:
    from sibyl.agents.tools import get_tool_catalog

    profile = os.getenv("SIBYL_PROFILE")
    catalog = get_tool_catalog(profile=profile)
    return _build_tools_from_catalog(catalog)


@server.list_tools()
async def list_tools() -> Iterable[Any]:
    """Expose tools for the active profile."""
    return _load_tools_for_profile()


async def _serve_stdio() -> None:  # pragma: no cover - exercised in real runtime
    if stdio_server is None or not hasattr(server, "run"):
        msg = "mcp stdio server is not available in this environment"
        raise ImportError(msg)

    async with stdio_server() as (read, write):
        await server.run(read, write)


def run() -> None:  # pragma: no cover - exercised in real runtime
    """Entry point to start the stdio transport."""
    asyncio.run(_serve_stdio())
