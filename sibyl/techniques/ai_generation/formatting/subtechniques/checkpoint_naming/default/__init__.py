"""
Default Checkpoint Naming Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import CheckpointNamingImplementation


def build_subtechnique(config: dict[str, Any] | None = None) -> CheckpointNamingImplementation:
    """
    Build and return a checkpoint naming implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        CheckpointNamingImplementation instance
    """
    return CheckpointNamingImplementation()


__all__ = ["CheckpointNamingImplementation", "build_subtechnique"]
