"""HTTP server launcher for Sibyl pipeline API.

This module provides the HTTP server startup functionality for running
Sibyl pipelines via REST API.

Example:
    # Start server with workspace
    python -m sibyl.server.http_server --workspace config/workspaces/example.yaml --port 8000

    # Or use CLI entry point
    sibyl http serve --workspace config/workspaces/example.yaml --port 8000

    # Or use environment variable (useful for Docker/K8s)
    export SIBYL_WORKSPACE_FILE=config/workspaces/example.yaml
    python -m sibyl.server.http_server --port 8000
"""

import argparse
import logging
import os
import sys

import uvicorn

from sibyl.server.rest_api import app, init_workspace
from sibyl.workspace import WorkspaceLoadError

logger = logging.getLogger(__name__)


def start_server(
    workspace_path: str,
    host: str = "0.0.0.0",  # S104: intentional for server flexibility
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Start the HTTP server with workspace configuration.

    Args:
        workspace_path: Path to workspace YAML file
        host: Host address to bind to (default: 0.0.0.0, binds all interfaces)
        port: Port to listen on (default: 8000)
        reload: Enable auto-reload for development (default: False)
        log_level: Logging level (default: info)

    Raises:
        WorkspaceLoadError: If workspace cannot be loaded
    """
    try:
        # Initialize workspace
        logger.info("Initializing workspace from: %s", workspace_path)
        init_workspace(workspace_path)
        logger.info("Workspace initialized successfully")

        # Start uvicorn server
        logger.info("Starting HTTP server on %s:%s", host, port)
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
        )

    except WorkspaceLoadError as e:
        logger.exception("Failed to load workspace: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Server startup failed: %s", e)
        sys.exit(1)


def main() -> None:
    """CLI entry point for HTTP server.

    Supports command-line arguments:
    --workspace: Path to workspace YAML file (optional if SIBYL_WORKSPACE_FILE is set)
    --host: Host address to bind to (default: 0.0.0.0)
    --port: Port to listen on (default: 8000)
    --reload: Enable auto-reload for development
    --log-level: Logging level (default: info)

    Workspace can be specified via:
    1. --workspace CLI flag (highest priority)
    2. SIBYL_WORKSPACE_FILE environment variable
    """
    parser = argparse.ArgumentParser(
        description="Sibyl HTTP API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with CLI flag
  sibyl http serve --workspace config/workspaces/example.yaml

  # Start server with environment variable
  export SIBYL_WORKSPACE_FILE=config/workspaces/example.yaml
  sibyl http serve

  # Custom port
  sibyl http serve --workspace example.yaml --port 8080

  # Development mode with auto-reload
  sibyl http serve --workspace example.yaml --reload

  # Multiple HTTP servers (Docker/Kubernetes)
  Container 1: SIBYL_WORKSPACE_FILE=workspace_a.yaml python -m sibyl.server.http_server --port 8000
  Container 2: SIBYL_WORKSPACE_FILE=workspace_b.yaml python -m sibyl.server.http_server --port 8001
        """,
    )

    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        default=None,
        help="Path to workspace YAML configuration file (overrides SIBYL_WORKSPACE_FILE env var)",
    )

    # S104: 0.0.0.0 default is intentional for flexibility
    # Users can override with --host 127.0.0.1 for local-only access
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0, use 127.0.0.1 for local only)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
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
    start_server(
        workspace_path=workspace_path,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
