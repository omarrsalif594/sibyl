from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "no_decomp", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('no_decomp', 'recursive')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .no_decomp import NoDecomp
    from .recursive import RecursiveDecomp

    implementations = {
        "no_decomp": NoDecomp,
        "recursive": RecursiveDecomp,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
