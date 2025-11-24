"""
Default Chain Of Thought Implementation

Exports build_subtechnique() function for the pluggable architecture.
"""

from typing import Any, Dict, Optional


def build_subtechnique(config: dict[str, Any] | None = None) -> Any:
    """
    Build and return a chain_of_thought implementation.

    Args:
        config: Optional configuration dictionary

    Returns:
        Implementation instance
    """
    # Import all available implementations
    import importlib.util
    from pathlib import Path

    # For now, return the first available implementation
    # TODO: Make this configurable based on config
    impl_files = list(Path(__file__).parent.glob("*.py"))
    impl_files = [f for f in impl_files if f.name not in ["__init__.py", "impl.py"]]

    if impl_files:
        # Import the first implementation
        spec = importlib.util.spec_from_file_location("impl_module", impl_files[0])
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find the first class in the module
            for item_name in dir(module):
                item = getattr(module, item_name)
                if isinstance(item, type) and item_name != "SubtechniqueImplementation":
                    return item()

    # Fallback: raise error
    msg = "No implementation found for chain_of_thought"
    raise NotImplementedError(msg)


__all__ = ["build_subtechnique"]
