from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "no_rewrite", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('no_rewrite', 'template', 'llm')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .llm import LLMRewrite
    from .no_rewrite import NoRewrite
    from .template import TemplateRewrite

    implementations = {
        "no_rewrite": NoRewrite,
        "template": TemplateRewrite,
        "llm": LLMRewrite,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
