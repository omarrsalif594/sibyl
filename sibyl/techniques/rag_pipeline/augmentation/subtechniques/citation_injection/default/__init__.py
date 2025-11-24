from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "inline_citations", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('inline_citations' or 'footnotes')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .footnotes import FootnotesImplementation
    from .inline_citations import InlineCitationsImplementation

    implementations = {
        "inline_citations": InlineCitationsImplementation,
        "footnotes": FootnotesImplementation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
