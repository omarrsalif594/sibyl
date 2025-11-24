"""
Default Qc Verdict Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import QualityControlProvider


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """
    Build and return a qc_verdict implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        QualityControlProvider instance
    """
    return QualityControlProvider()


__all__ = ["QualityControlProvider", "build_subtechnique"]
