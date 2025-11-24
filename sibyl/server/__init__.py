"""MCP Server Core - Protocol Implementation.

This package contains the core MCP protocol implementation:
- mcp_server.py: Main MCP server entry point
- stdio_transport.py: stdio transport for Claude Code
- http_transport.py: HTTP transport for VS Code extension
- rest_api.py: REST API server (FastAPI)
- shared_state.py: Thread-safe state management
- config.py: Server configuration

The server layer handles:
- MCP protocol lifecycle (initialization, tools, resources)
- Transport layer (stdio, HTTP)
- Request routing to agents and tools
- State management across requests
"""

__all__ = [
    # Will be populated after file moves
]
