#!/usr/bin/env python3
"""
Validate MCP Server Installation.

Tests that all critical modules can be imported and basic functionality works.
"""

import importlib
import sys

# Critical modules that must be importable
CRITICAL_MODULES = [
    "mcp_server",
    "mcp_server.server.mcp_server",
    "mcp_server.infrastructure.quorum",
    "mcp_server.infrastructure.orchestration",
    "mcp_server.infrastructure.checkpointing",
    "mcp_server.infrastructure.hooks",
    "mcp_server.infrastructure.learning",
    "mcp_server.resources.hybrid_search",
    "mcp_server.extensibility.tool_base",
    "mcp_server.application.use_cases",
]

# Third-party dependencies
REQUIRED_DEPENDENCIES = [
    "pydantic",
    "mcp",
    "networkx",
    "starlette",
    "uvicorn",
    "sqlfluff",
    "radon",
]


def check_module(module_name: str) -> tuple[bool, str]:
    """
    Check if a module can be imported.

    Args:
        module_name: Name of the module to import

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main() -> int:
    """
    Run validation checks.

    Returns:
        Exit code (0 for success, 1 for failure)
    """

    all_passed = True

    # Check critical modules
    for module in CRITICAL_MODULES:
        success, error = check_module(module)
        if success:
            pass
        else:
            all_passed = False

    # Check dependencies
    for dependency in REQUIRED_DEPENDENCIES:
        success, _error = check_module(dependency)
        if success:
            pass
        else:
            all_passed = False

    # Summary
    if all_passed:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
