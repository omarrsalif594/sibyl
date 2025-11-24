"""Implementation module."""

from typing import Never


def build_subtechnique(**kwargs) -> Never:
    """
    Build and return a custom subtechnique instance.

    Args:
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance

    Note:
        This is a placeholder. Add custom implementations as needed.
    """
    msg = (
        "No custom implementations available for metadata_injection. Use 'default' variant instead."
    )
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
