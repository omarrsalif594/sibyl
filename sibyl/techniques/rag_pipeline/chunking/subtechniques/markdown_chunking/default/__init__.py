from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "chunker_text", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('chunker_text')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .chunker_text import MarkdownChunker

    implementations = {
        "chunker_text": MarkdownChunker,
        "markdown": MarkdownChunker,  # Alias
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
