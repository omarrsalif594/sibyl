"""
Provider-specific Threshold Voting Implementation

This is a stub for provider-specific implementations.
"""

from typing import Any, Dict, Optional


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """Build provider-specific threshold voting implementation."""
    from sibyl.techniques.ai_generation.voting.subtechniques.threshold_voting.default import (
        build_subtechnique as build_default,
    )

    return build_default(config)


__all__ = ["build_subtechnique"]
