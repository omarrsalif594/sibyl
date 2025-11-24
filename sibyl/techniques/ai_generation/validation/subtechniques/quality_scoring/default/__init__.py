"""
Default Quality Scoring Implementation

Exports build_subtechnique() function for the pluggable architecture.
Multiple implementations available: rule_based, threshold_based
"""

from typing import Any, Dict, Optional


def build_subtechnique(
    config: dict[str, Any] | None = None, implementation: str = "rule_based"
) -> Any:
    """
    Build and return a quality_scoring implementation.

    Args:
        config: Optional configuration dictionary
        implementation: Which implementation to use (rule_based, threshold_based)

    Returns:
        Implementation instance
    """
    import importlib
    from pathlib import Path

    implementations = ["rule_based", "threshold_based"]

    if implementation not in implementations:
        msg = f"Unknown implementation: {implementation}. Available: {implementations}"
        raise ValueError(msg)

    # Dynamically import the implementation module
    module = importlib.import_module(f".{implementation}", package=__package__)

    # Find the implementation class
    for item_name in dir(module):
        item = getattr(module, item_name)
        if isinstance(item, type) and item_name.endswith("Implementation"):
            return item()

    msg = f"No implementation class found in {implementation}.py"
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
