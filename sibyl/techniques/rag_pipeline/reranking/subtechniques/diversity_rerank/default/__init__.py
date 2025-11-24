from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "mmr", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('mmr', 'cluster_based')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .cluster_based import ClusterBasedReranker
    from .mmr import MMRReranker

    implementations = {
        "mmr": MMRReranker,
        "cluster_based": ClusterBasedReranker,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
