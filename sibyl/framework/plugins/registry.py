"""
Plugin registry for managing code processing plugins.

This module provides a central registry where plugins can be registered
and retrieved by code type. It supports:
- Multiple validators per code type
- Single chunker and scorer per code type

Note: This is a framework-level service for plugin management, not a protocol.
"""

from sibyl.core.protocols.rag_pipeline.code_processing import (
    CodeChunker,
    CodeType,
    CodeValidator,
    ComplexityScorer,
)


class PluginRegistry:
    """
    Central registry for code processing plugins.

    Plugins are registered by code type and can be retrieved for processing.
    """

    def __init__(self) -> None:
        self._chunkers: dict[CodeType, CodeChunker] = {}
        self._validators: dict[CodeType, list[CodeValidator]] = {}
        self._scorers: dict[CodeType, ComplexityScorer] = {}

    def register_chunker(self, code_type: CodeType, chunker: CodeChunker) -> None:
        """
        Register a chunker for a code type.

        Args:
            code_type: The code type this chunker handles
            chunker: The chunker implementation
        """
        if not chunker.supports(code_type):
            msg = f"Chunker {chunker.__class__.__name__} does not support {code_type}"
            raise ValueError(msg)
        self._chunkers[code_type] = chunker

    def register_validator(self, code_type: CodeType, validator: CodeValidator) -> None:
        """
        Register a validator for a code type.

        Multiple validators can be registered for the same code type.

        Args:
            code_type: The code type this validator handles
            validator: The validator implementation
        """
        if not validator.supports(code_type):
            msg = f"Validator {validator.__class__.__name__} does not support {code_type}"
            raise ValueError(msg)
        self._validators.setdefault(code_type, []).append(validator)

    def register_scorer(self, code_type: CodeType, scorer: ComplexityScorer) -> None:
        """
        Register a complexity scorer for a code type.

        Args:
            code_type: The code type this scorer handles
            scorer: The scorer implementation
        """
        if not scorer.supports(code_type):
            msg = f"Scorer {scorer.__class__.__name__} does not support {code_type}"
            raise ValueError(msg)
        self._scorers[code_type] = scorer

    def get_chunker(self, code_type: CodeType) -> CodeChunker | None:
        """
        Get the chunker for a code type.

        Args:
            code_type: The code type to get chunker for

        Returns:
            The registered chunker, or None if not found
        """
        return self._chunkers.get(code_type)

    def get_validators(self, code_type: CodeType) -> list[CodeValidator]:
        """
        Get all validators for a code type.

        Args:
            code_type: The code type to get validators for

        Returns:
            List of registered validators (empty if none registered)
        """
        return self._validators.get(code_type, [])

    def get_scorer(self, code_type: CodeType) -> ComplexityScorer | None:
        """
        Get the complexity scorer for a code type.

        Args:
            code_type: The code type to get scorer for

        Returns:
            The registered scorer, or None if not found
        """
        return self._scorers.get(code_type)

    def list_supported_types(self) -> dict[str, list[CodeType]]:
        """
        List all code types supported by registered plugins.

        Returns:
            Dictionary with keys "chunkers", "validators", "scorers"
            and values as lists of supported CodeTypes
        """
        return {
            "chunkers": list(self._chunkers.keys()),
            "validators": list(self._validators.keys()),
            "scorers": list(self._scorers.keys()),
        }


# Global registry instance (singleton pattern)
_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get the global plugin registry instance.

    Returns:
        The singleton PluginRegistry
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


__all__ = [
    "PluginRegistry",
    "get_plugin_registry",
]
