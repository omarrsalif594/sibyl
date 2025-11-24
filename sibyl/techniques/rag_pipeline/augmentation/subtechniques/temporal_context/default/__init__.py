from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "timestamp", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('timestamp' or 'recency')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .recency import RecencyImplementation
    from .timestamp import TimestampImplementation

    implementations = {
        "timestamp": TimestampImplementation,
        "recency": RecencyImplementation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
