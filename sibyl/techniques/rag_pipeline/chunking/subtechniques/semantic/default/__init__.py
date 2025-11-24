from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "semantic_chunker", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('semantic_chunker')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .semantic_chunker import SemanticChunking

    implementations = {
        "semantic_chunker": SemanticChunking,
        "semantic": SemanticChunking,  # Alias for compatibility
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
