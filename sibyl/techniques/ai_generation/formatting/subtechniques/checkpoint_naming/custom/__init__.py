"""
Custom Checkpoint Naming Implementation

This is a stub for custom user implementations.
Users can implement their own checkpoint naming logic here.
"""

from typing import Any, Dict, Optional


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """
    Build custom checkpoint naming implementation.

    Currently delegates to default implementation.
    Override this function to provide custom behavior.

    Args:
        config: Optional configuration dictionary

    Returns:
        CheckpointNamingImplementation instance
    """
    # Delegate to default for now
    from checkpoint_naming.default import build_subtechnique as build_default

    return build_default(config)


__all__ = ["build_subtechnique"]
