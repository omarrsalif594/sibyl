from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "rrf", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('rrf', 'weighted_fusion')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .rrf import RRFFusion
    from .weighted_fusion import WeightedFusion

    implementations = {
        "rrf": RRFFusion,
        "weighted_fusion": WeightedFusion,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
