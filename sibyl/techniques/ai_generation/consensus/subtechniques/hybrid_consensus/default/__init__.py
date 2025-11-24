"""
Default Hybrid Consensus Implementation

Exports build_subtechnique() function for the pluggable architecture.
Multiple implementations available: voting_heuristic_mix
"""

from typing import Any

from .voting_heuristic_mix import VotingHeuristicMixConsensus


def build_subtechnique(
    config: dict[str, Any] | None = None, implementation: str = "voting_heuristic_mix"
) -> Any:
    """
    Build and return a hybrid_consensus implementation.

    Args:
        config: Optional configuration dictionary
        implementation: Which implementation to use (voting_heuristic_mix)

    Returns:
        Consensus implementation instance
    """
    implementations = {
        "voting_heuristic_mix": VotingHeuristicMixConsensus,
    }

    if implementation not in implementations:
        msg = f"Unknown implementation: {implementation}. Available: {list(implementations.keys())}"
        raise ValueError(msg)

    return implementations[implementation]()


__all__ = ["VotingHeuristicMixConsensus", "build_subtechnique"]
