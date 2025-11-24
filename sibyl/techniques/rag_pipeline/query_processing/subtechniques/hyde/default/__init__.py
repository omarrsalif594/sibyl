from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "disabled", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('disabled', 'simple_hyde')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .disabled import DisabledHyde
    from .simple_hyde import SimpleHyde

    implementations = {
        "disabled": DisabledHyde,
        "simple_hyde": SimpleHyde,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
