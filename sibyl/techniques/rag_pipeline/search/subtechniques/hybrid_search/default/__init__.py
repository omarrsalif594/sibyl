from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "rrf", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('rrf', 'weighted')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .rrf import RRFSearch
    from .weighted import WeightedSearch

    implementations = {
        "rrf": RRFSearch,
        "weighted": WeightedSearch,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
