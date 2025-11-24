"""
Default Weighted Voting Implementation

Exports build_subtechnique() function for the pluggable architecture.
Multiple implementations available: confidence_weighted, role_weighted
"""

from typing import Any

from .confidence_weighted import ConfidenceWeightedConsensus
from .role_weighted import RoleWeightedConsensus


def build_subtechnique(
    config: dict[str, Any] | None = None, implementation: str = "confidence_weighted"
) -> Any:
    """
    Build and return a weighted_voting implementation.

    Args:
        config: Optional configuration dictionary
        implementation: Which implementation to use (confidence_weighted, role_weighted)

    Returns:
        Consensus implementation instance
    """
    implementations = {
        "confidence_weighted": ConfidenceWeightedConsensus,
        "role_weighted": RoleWeightedConsensus,
    }

    if implementation not in implementations:
        msg = f"Unknown implementation: {implementation}. Available: {list(implementations.keys())}"
        raise ValueError(msg)

    return implementations[implementation]()


__all__ = ["ConfidenceWeightedConsensus", "RoleWeightedConsensus", "build_subtechnique"]
