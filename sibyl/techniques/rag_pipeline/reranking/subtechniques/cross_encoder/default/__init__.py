from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "no_rerank", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('no_rerank', 'sentence_transformer')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .no_rerank import NoRerank
    from .sentence_transformer import SentenceTransformerReranker

    implementations = {
        "no_rerank": NoRerank,
        "sentence_transformer": SentenceTransformerReranker,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
