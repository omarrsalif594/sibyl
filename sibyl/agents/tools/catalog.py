"""
Tool Catalog - Defines available tools for agents.

This module provides:
- Core framework tools (generic)
- Tool metadata and schemas
- Profile-based tool loading
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def get_core_tools() -> dict[str, Any]:
    """
    Get core framework tools (domain-neutral).

    Returns:
        Dictionary of tool name -> tool metadata
    """
    return {
        "search_knowledge_base": {
            "description": "Search the knowledge base for resources",
            "keywords": ["search", "find", "query", "lookup"],
            "parameters": {
                "query": {"type": "string", "required": True},
                "filters": {"type": "object", "required": False},
                "limit": {"type": "integer", "default": 10},
            },
            "returns": "List of matching resources",
        },
        "run_quality_checks": {
            "description": "Run quality control checks on a resource",
            "keywords": ["validate", "check", "qc", "quality"],
            "parameters": {
                "resource_id": {"type": "string", "required": True},
                "check_types": {"type": "array", "required": False},
            },
            "returns": "Quality check results",
        },
        "analyze_complexity": {
            "description": "Analyze complexity of a resource",
            "keywords": ["complexity", "analyze", "score"],
            "parameters": {"resource_id": {"type": "string", "required": True}},
            "returns": "Complexity analysis",
        },
        "get_resource_metadata": {
            "description": "Get metadata for a resource",
            "keywords": ["metadata", "info", "details"],
            "parameters": {"resource_id": {"type": "string", "required": True}},
            "returns": "Resource metadata",
        },
        "list_plugins": {
            "description": "List available plugins",
            "keywords": ["plugins", "list", "available"],
            "parameters": {},
            "returns": "List of plugins",
        },
        "traverse_graph": {
            "description": "Traverse the dependency graph for an entity",
            "keywords": ["graph", "dependencies", "traverse", "related"],
            "parameters": {
                "entity_id": {"type": "string", "required": True},
                "direction": {"type": "string", "enum": ["in", "out", "both"], "default": "both"},
                "depth": {"type": "integer", "default": 2},
            },
            "returns": "Graph traversal results",
        },
    }


def get_profile_tools(profile: str | None) -> dict[str, Any]:
    """
    Get profile-specific tools.

    This is a hook for example packages to inject their tools.
    Core framework doesn't define any profile tools.

    Args:
        profile: Profile name (e.g., "default", "analytics")

    Returns:
        Dictionary of tool name -> tool metadata
    """
    profile_normalized = (profile or os.environ.get("SIBYL_PROFILE", "")).lower()
    if not profile_normalized:
        return {}

    logger.info("Loading tools for profile: %s", profile_normalized)

    if profile_normalized == "retailflow":
        try:
            from examples.retailflow.server.main import get_retailflow_tools

            tools = get_retailflow_tools()
            logger.info("Loaded %d RetailFlow tools", len(tools))
            return tools
        except Exception as exc:  # pragma: no cover - optional example dependency
            logger.warning("RetailFlow tools unavailable: %s", exc)
            return {}

    logger.warning("No profile tools registered for profile '%s'", profile_normalized)
    return {}


def merge_tool_catalogs(
    core_tools: dict[str, Any], profile_tools: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge core and profile tools.

    Args:
        core_tools: Core framework tools
        profile_tools: Profile-specific tools

    Returns:
        Merged tool catalog
    """
    merged = core_tools.copy()

    # Profile tools can override core tools
    for tool_name, tool_meta in profile_tools.items():
        if tool_name in merged:
            logger.warning("Profile tool '%s' overrides core tool", tool_name)
        merged[tool_name] = tool_meta

    logger.info("Merged catalog: %s tools total", len(merged))
    return merged


def get_tool_catalog(profile: str | None = None) -> dict[str, Any]:
    """
    Get complete tool catalog for a profile.

    Args:
        profile: Optional profile name

    Returns:
        Complete tool catalog
    """
    core_tools = get_core_tools()

    profile_to_use = profile or os.environ.get("SIBYL_PROFILE")
    if profile_to_use:
        profile_tools = get_profile_tools(profile_to_use)
        return merge_tool_catalogs(core_tools, profile_tools)

    return core_tools


def validate_tool_call(
    tool_name: str, params: dict[str, Any], catalog: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate a tool call against the catalog.

    Args:
        tool_name: Name of tool to call
        params: Parameters for the call
        catalog: Tool catalog

    Returns:
        (is_valid, error_message)
    """
    if tool_name not in catalog:
        return False, f"Tool '{tool_name}' not found in catalog"

    tool_meta = catalog[tool_name]
    tool_params = tool_meta.get("parameters", {})

    # Check required parameters
    for param_name, param_meta in tool_params.items():
        if param_meta.get("required", False) and param_name not in params:
            return False, f"Missing required parameter: {param_name}"

    # Check parameter types (basic validation)
    for param_name, param_value in params.items():
        if param_name not in tool_params:
            logger.warning("Unknown parameter: %s", param_name)
            continue

        expected_type = tool_params[param_name].get("type")
        actual_type = type(param_value).__name__

        # Basic type checking
        type_map = {
            "string": "str",
            "integer": "int",
            "boolean": "bool",
            "object": "dict",
            "array": "list",
        }

        if expected_type and type_map.get(expected_type) != actual_type:
            return (
                False,
                f"Parameter '{param_name}' type mismatch: expected {expected_type}, got {actual_type}",
            )

    return True, None


__all__ = [
    "get_core_tools",
    "get_profile_tools",
    "get_tool_catalog",
    "merge_tool_catalogs",
    "validate_tool_call",
]
