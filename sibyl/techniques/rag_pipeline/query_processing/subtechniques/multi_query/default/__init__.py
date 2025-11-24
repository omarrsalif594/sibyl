from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "single", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('single', 'perspective_variation')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .perspective_variation import PerspectiveVariation
    from .single import SingleQuery

    implementations = {
        "single": SingleQuery,
        "perspective_variation": PerspectiveVariation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
