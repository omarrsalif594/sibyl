"""
Default JSON Repair Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import JSONRepair


def build_subtechnique(config: dict[str, Any] | None = None) -> JSONRepair:
    """
    Build and return a JSON repair implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        JSONRepair instance
    """
    return JSONRepair()


__all__ = ["JSONRepair", "build_subtechnique"]
