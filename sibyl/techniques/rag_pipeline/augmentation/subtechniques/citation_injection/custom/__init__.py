"""Implementation module."""

from typing import Never


def build_subtechnique(implementation_name: str = "default", **kwargs) -> Never:
    """
    Build and return a custom subtechnique instance.

    Args:
        implementation_name: Which custom implementation to build
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance

    Raises:
        NotImplementedError: Custom implementations must be added by user
    """
    msg = (
        "Custom implementations must be added by the user. "
        "See custom/README.md for instructions on how to add your own implementation."
    )
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
