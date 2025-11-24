from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "entity_links", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('entity_links' or 'doc_links')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .doc_links import DocLinksImplementation
    from .entity_links import EntityLinksImplementation

    implementations = {
        "entity_links": EntityLinksImplementation,
        "doc_links": DocLinksImplementation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
