"""Implementation module."""

from typing import Never


def build_subtechnique(**kwargs) -> Never:
    """
    Build and return a provider-specific subtechnique instance.

    Args:
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance

    Note:
        This is a placeholder. Add provider-specific implementations as needed.
    """
    msg = (
        "No provider implementations available for metadata_injection. "
        "Use 'default' or 'custom' variant instead."
    )
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
