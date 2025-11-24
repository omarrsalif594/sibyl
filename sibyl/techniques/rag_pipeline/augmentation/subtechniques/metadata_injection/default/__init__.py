from typing import Any

"""Implementation module."""


def build_subtechnique(implementation_name: str = "schema_metadata", **kwargs) -> Any:
    """
    Build and return a subtechnique instance.

    Args:
        implementation_name: Which implementation to build ('schema_metadata' or 'source_metadata')
        **kwargs: Optional configuration

    Returns:
        BaseSubtechnique: Configured subtechnique instance
    """
    from .schema_metadata import SchemaMetadataImplementation
    from .source_metadata import SourceMetadataImplementation

    implementations = {
        "schema_metadata": SchemaMetadataImplementation,
        "source_metadata": SourceMetadataImplementation,
    }

    if implementation_name not in implementations:
        msg = (
            f"Unknown implementation: {implementation_name}. "
            f"Available: {list(implementations.keys())}"
        )
        raise ValueError(msg)

    return implementations[implementation_name]()


__all__ = ["build_subtechnique"]
