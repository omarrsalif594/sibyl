"""
Sibyl: Universal AI Assistant Platform

Sibyl is an adaptable MCP server with templates for any domain, providing a comprehensive
framework for building AI-powered assistants with RAG, agents, workflows, and more.

Public API modules (STABLE):
- sibyl.workspace: Workspace configuration and loading
- sibyl.runtime: Pipeline execution and provider management
- sibyl.core.protocols: Protocol interfaces for extension
- sibyl.core.contracts: Base classes for tools and validators
- sibyl.shops: High-level technique facades

For documentation, see: docs/architecture/public_api.md
"""

try:
    # Try to get version from setuptools_scm
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("sibyl-mcp")
    except PackageNotFoundError:
        # Development install or not installed via pip
        __version__ = "0.1.0"
except ImportError:
    # Fallback for older Python versions
    __version__ = "0.1.0"

from sibyl.sibyl import Sibyl

__all__ = ["Sibyl", "__version__"]
