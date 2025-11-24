"""Implementation module."""

from typing import Never


def build_subtechnique(implementation_name: str = "default", **kwargs) -> Never:
    """
    Build and return a provider-specific subtechnique instance.

    Args:
        implementation_name: Which provider implementation to build
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance

    Raises:
        NotImplementedError: Provider implementations not yet available
    """
    msg = (
        "Provider-specific implementations for citation_injection are not yet available. "
        "Use the default implementation instead."
    )
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
