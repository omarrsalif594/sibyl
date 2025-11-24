"""Implementation module."""

from typing import Never


def build_subtechnique(implementation_name: str = "default", **kwargs) -> Never:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    msg = "Custom implementations are not yet available."
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
