"""
Provider-specific Checkpoint Naming Implementation

This is a stub for provider-specific implementations.
Providers can override the default checkpoint naming behavior here.
"""

from typing import Any, Dict, Optional


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """
    Build provider-specific checkpoint naming implementation.

    Currently delegates to default implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        CheckpointNamingImplementation instance
    """
    # Delegate to default for now
    from checkpoint_naming.default import build_subtechnique as build_default

    return build_default(config)


__all__ = ["build_subtechnique"]
