"""
Sibyl framework plugin system.

This module provides the plugin architecture for extending Sibyl with
domain-specific functionality:

- registry: Central registry for managing plugins
- Bootstrap functions for initializing plugins based on profiles

Example:
    # Initialize plugins for a domain
    from sibyl.framework.plugins import register_builtin_plugins

    register_builtin_plugins(profile="ExampleDomain")
"""

import logging
import os
from typing import Optional

from sibyl.core.protocols.rag_pipeline.code_processing import (
    Chunk,
    CodeChunker,
    CodeType,
    CodeValidator,
    ComplexityScorer,
)
from sibyl.framework.plugins.registry import PluginRegistry, get_plugin_registry

logger = logging.getLogger(__name__)


def register_core_plugins() -> None:
    """
    Register all core plugins with the global registry.

    This function should be called during application initialization
    to make core plugins available for use.

    The core plugins are imported from their canonical locations in techniques/.
    """
    registry = get_plugin_registry()

    # Import core plugin implementations (these are in techniques now)
    from sibyl.techniques.infrastructure.scoring.subtechniques.complexity_scoring.default.scorer_basic import (
        BasicComplexityScorer,
    )
    from sibyl.techniques.rag_pipeline.chunking.subtechniques.markdown_chunking.default.chunker_text import (
        TextChunker,
    )
    from sibyl.techniques.rag_pipeline.chunking.subtechniques.sql_chunking.default.chunker_simple_sql import (
        SimpleSQLChunker,
    )
    from sibyl.techniques.rag_pipeline.validation.subtechniques.structural.default.validator_basic import (
        BasicValidator,
    )

    # Text chunker for TEXT and MARKDOWN
    text_chunker = TextChunker()
    registry.register_chunker(CodeType.TEXT, text_chunker)
    registry.register_chunker(CodeType.MARKDOWN, text_chunker)

    # Simple SQL chunker (basic statement splitting)
    sql_chunker = SimpleSQLChunker()
    registry.register_chunker(CodeType.SQL, sql_chunker)

    # Basic validator for TEXT, MARKDOWN, and SQL
    basic_validator = BasicValidator()
    registry.register_validator(CodeType.TEXT, basic_validator)
    registry.register_validator(CodeType.MARKDOWN, basic_validator)
    registry.register_validator(CodeType.SQL, basic_validator)

    # Basic complexity scorer
    basic_scorer = BasicComplexityScorer()
    registry.register_scorer(CodeType.TEXT, basic_scorer)
    registry.register_scorer(CodeType.MARKDOWN, basic_scorer)
    registry.register_scorer(CodeType.SQL, basic_scorer)


def register_builtin_plugins(profile: str | None = None) -> None:
    """
    Register built-in plugins based on the specified profile.

    This function should be called during application initialization to
    set up the plugin system. It always registers core plugins, and
    optionally registers domain-specific plugins based on the profile.

    Profiles:
    - None (default): Core plugins only
    - "ExampleDomain": Core + example plugins

    Args:
        profile: Optional profile name to determine which plugins to load.
                Can also be set via SIBYL_PROFILE environment variable.

    Example:
        # Load core + example plugins
        register_builtin_plugins(profile="ExampleDomain")

        # Or use environment variable
        os.environ["SIBYL_PROFILE"] = "ExampleDomain"
        register_builtin_plugins()
    """
    # Check environment variable if profile not provided
    if profile is None:
        profile = os.environ.get("SIBYL_PROFILE")

    logger.info("Registering plugins for profile: %s", profile or "core")

    # Always register core plugins
    register_core_plugins()
    logger.info("Core plugins registered")

    # Register profile-specific plugins
    if profile == "ExampleDomain":
        # For now, we don't have ExampleDomain-specific plugins
        # This would be where domain-specific plugins get registered
        logger.info("No ExampleDomain-specific plugins available")
    elif profile is not None:
        logger.warning("Unknown profile '%s', only core plugins loaded", profile)

    # Log registered plugins
    registry = get_plugin_registry()
    supported = registry.list_supported_types()
    logger.info("Plugin registration complete. Supported types: %s", supported)


def get_profile() -> str | None:
    """
    Get the current plugin profile.

    Returns:
        The profile name from SIBYL_PROFILE environment variable, or None
    """
    return os.environ.get("SIBYL_PROFILE")


__all__ = [
    "Chunk",
    "CodeChunker",
    # Protocols (re-exported for convenience)
    "CodeType",
    "CodeValidator",
    "ComplexityScorer",
    # Registry
    "PluginRegistry",
    "get_plugin_registry",
    "get_profile",
    "register_builtin_plugins",
    # Bootstrap
    "register_core_plugins",
]
