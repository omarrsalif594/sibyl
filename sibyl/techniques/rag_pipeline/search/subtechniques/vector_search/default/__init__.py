from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "faiss", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('faiss', 'pgvector', 'duckdb')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .duckdb import DuckDBVectorSearch
    from .faiss import FAISSVectorSearch
    from .pgvector import PGVectorSearch

    implementations = {
        "faiss": FAISSVectorSearch,
        "pgvector": PGVectorSearch,
        "duckdb": DuckDBVectorSearch,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
