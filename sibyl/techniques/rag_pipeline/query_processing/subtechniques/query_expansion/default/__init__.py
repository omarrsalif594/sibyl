from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "no_expansion", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('no_expansion', 'synonym', 'embedding')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .embedding import EmbeddingExpansion
    from .no_expansion import NoExpansion
    from .synonym import SynonymExpansion

    implementations = {
        "no_expansion": NoExpansion,
        "synonym": SynonymExpansion,
        "embedding": EmbeddingExpansion,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
