from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "semantic_search", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('semantic_search')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .semantic_search import SemanticSearchRetrieval

    implementations = {
        "semantic_search": SemanticSearchRetrieval,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
