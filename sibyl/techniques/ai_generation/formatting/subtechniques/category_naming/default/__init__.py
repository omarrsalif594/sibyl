"""
Default Category Naming Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import CategoryNamingImplementation


def build_subtechnique(config: dict[str, Any] | None = None) -> CategoryNamingImplementation:
    """
    Build and return a category naming implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        CategoryNamingImplementation instance
    """
    return CategoryNamingImplementation()


__all__ = ["CategoryNamingImplementation", "build_subtechnique"]
