from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "spacy", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('spacy' or 'llm')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .llm import LlmImplementation
    from .spacy import SpacyImplementation

    implementations = {
        "spacy": SpacyImplementation,
        "llm": LlmImplementation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
