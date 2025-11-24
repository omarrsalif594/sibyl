"""
Default Threshold Voting Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional

from .impl import ThresholdVotingImplementation


def build_subtechnique(config: dict[str, Any] | None = None) -> ThresholdVotingImplementation:
    """
    Build and return a threshold voting implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        ThresholdVotingImplementation instance
    """
    return ThresholdVotingImplementation()


__all__ = ["ThresholdVotingImplementation", "build_subtechnique"]
