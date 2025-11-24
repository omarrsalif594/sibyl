"""Entrypoint helpers for running Sibyl core services."""

import logging

from sibyl.core.server.mcp_server import run_stdio

logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover - convenience entrypoint
    try:
        run_stdio()
    except ImportError as exc:
        logger.exception("Cannot start MCP stdio server: %s", exc)


if __name__ == "__main__":
    main()
