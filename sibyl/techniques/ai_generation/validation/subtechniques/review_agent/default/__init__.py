"""
Default Review Agent Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import ReviewAgent


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """
    Build and return a review_agent implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        ReviewAgent instance
    """
    return ReviewAgent()


__all__ = ["ReviewAgent", "build_subtechnique"]
