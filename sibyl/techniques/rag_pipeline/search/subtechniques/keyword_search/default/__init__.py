from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "bm25", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('bm25', 'tf_idf')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .bm25 import BM25Search
    from .tf_idf import TFIDFSearch

    implementations = {
        "bm25": BM25Search,
        "tf_idf": TFIDFSearch,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
