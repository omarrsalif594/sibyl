"""
Default Quorum Voting Implementation

Exports build_subtechnique() function for the pluggable architecture.
Multiple implementations available: five_agent, three_agent, single_agent
"""

from typing import Any

from .five_agent import FiveAgentConsensus
from .single_agent import SingleAgentConsensus
from .three_agent import ThreeAgentConsensus


def build_subtechnique(
    config: dict[str, Any] | None = None, implementation: str = "five_agent"
) -> Any:
    """
    Build and return a quorum_voting implementation.

    Args:
        config: Optional configuration dictionary
        implementation: Which implementation to use (five_agent, three_agent, single_agent)

    Returns:
        Consensus implementation instance
    """
    implementations = {
        "five_agent": FiveAgentConsensus,
        "three_agent": ThreeAgentConsensus,
        "single_agent": SingleAgentConsensus,
    }

    if implementation not in implementations:
        msg = f"Unknown implementation: {implementation}. Available: {list(implementations.keys())}"
        raise ValueError(msg)

    return implementations[implementation]()


__all__ = [
    "FiveAgentConsensus",
    "SingleAgentConsensus",
    "ThreeAgentConsensus",
    "build_subtechnique",
]
