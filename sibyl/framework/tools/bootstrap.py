"""
Tool bootstrap - Deterministic tool registration.

This module imports all tool modules to ensure they register themselves
in the tool registry. This is critical for:
1. Tool catalog generation
2. Consistent tool availability across environments
3. Dependency tracking
4. Testing (ensure all tools are loaded before tests run)

Usage (NEW - recommended):
    from sibyl.framework.container import DIContainer
    container = DIContainer()
    registry = container.get_tool_registry()  # Automatically bootstraps
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def bootstrap_all_tools(registry: Optional["ToolRegistry"] = None) -> dict[str, any]:
    """
    Import all tool modules to register them in the tool registry.

    This function deterministically imports every tool module, ensuring:
    - All tools are registered regardless of runtime code paths
    - Tool catalog generation sees all tools
    - Tests can enumerate all tools
    - No lazy-loading surprises

    Args:
        registry: Optional ToolRegistry instance. If not provided, uses
                  the global registry.

    Returns:
        Dictionary with registration statistics
    """
    logger.info("Bootstrapping all MCP tools...")

    # Use provided registry or fall back to global
    if registry is None:
        from sibyl.framework.container import create_core_container

        registry = create_core_container().get_tool_registry()

    # Get initial state
    initial_stats = registry.get_stats()
    logger.debug("Initial state: %s tools registered", initial_stats["total_tools"])

    # ===================================================================
    # FAST THINKER TOOLS (16 total)
    # ===================================================================

    # NOTE: example_lineage_tool.py disabled - replaced by complete lineage_tools.py
    # try:
    #     from agents.fast_thinker.tools import example_lineage_tool
    #     logger.debug("✓ Loaded: fast_thinker example_lineage_tool")
    # except ImportError as e:
    #     logger.warning("✗ Failed to load fast_thinker example_lineage_tool: %s", e)

    # TODO: Uncomment as tools are implemented

    # Lineage Tools (7 tools)
    try:
        from agents.fast_thinker.tools import lineage_tools  # optional dependency

        logger.debug("✓ Loaded: fast_thinker lineage_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load fast_thinker lineage_tools: %s", e)

    # Metadata Tools (5 tools)
    try:
        from agents.fast_thinker.tools import metadata_tools  # optional dependency

        logger.debug("✓ Loaded: fast_thinker metadata_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load fast_thinker metadata_tools: %s", e)

    # Search Tools (4 tools)
    try:
        from agents.fast_thinker.tools import search_tools  # optional dependency

        logger.debug("✓ Loaded: fast_thinker search_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load fast_thinker search_tools: %s", e)

    # ===================================================================
    # DEEP THINKER TOOLS (18 total)
    # ===================================================================

    # Analysis Tools (7 tools)
    try:
        from agents.deep_thinker.tools import analysis_tools  # optional dependency

        logger.debug("✓ Loaded: deep_thinker analysis_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load deep_thinker analysis_tools: %s", e)

    # Pattern Tools (3 tools)
    try:
        from agents.deep_thinker.tools import pattern_tools  # optional dependency

        logger.debug("✓ Loaded: deep_thinker pattern_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load deep_thinker pattern_tools: %s", e)

    # Code Search Tools (1 tool)
    try:
        from agents.deep_thinker.tools import code_search_tools  # optional dependency

        logger.debug("✓ Loaded: deep_thinker code_search_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load deep_thinker code_search_tools: %s", e)

    # Intelligence Tools (7 tools)
    try:
        from agents.deep_thinker.tools import intelligence_tools  # optional dependency

        logger.debug("✓ Loaded: deep_thinker intelligence_tools")
    except ImportError as e:
        logger.warning("✗ Failed to load deep_thinker intelligence_tools: %s", e)

    # Get final state
    final_stats = registry.get_stats()
    newly_registered = final_stats["total_tools"] - initial_stats["total_tools"]

    logger.info("✓ Bootstrap complete: %s new tools registered", newly_registered)
    logger.info("  Total tools: %s", final_stats["total_tools"])
    logger.info("  Categories: %s", ", ".join(final_stats["categories"]))

    return {
        "initial_count": initial_stats["total_tools"],
        "final_count": final_stats["total_tools"],
        "newly_registered": newly_registered,
        "categories": final_stats["categories"],
        "tools_by_category": final_stats["tools_by_category"],
    }


if __name__ == "__main__":
    # Allow running as script for testing
    logging.basicConfig(level=logging.DEBUG)
    stats = bootstrap_all_tools()
