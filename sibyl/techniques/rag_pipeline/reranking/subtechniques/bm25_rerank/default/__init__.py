from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "bm25_scorer", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('bm25_scorer',)
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .bm25_scorer import BM25Scorer

    implementations = {
        "bm25_scorer": BM25Scorer,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
