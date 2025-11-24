"""Augmentation technique protocols and shared types.

This module defines the protocol interfaces and data structures for augmentation operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class AugmentedContent:
    """Result from an augmentation operation."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    augmentation_method: str = ""
    original_content: str = ""


@runtime_checkable
class CitationInjector(Protocol):
    """Protocol for citation injection implementations."""

    @property
    def name(self) -> str:
        """Injector name for identification."""
        ...

    def inject(self, content: str, sources: list[dict[str, Any]], config: dict[str, Any]) -> str:
        """Inject citations into content.

        Args:
            content: Content to augment
            sources: Source documents with metadata
            config: Configuration options

        Returns:
            Content with injected citations
        """
        ...


@runtime_checkable
class MetadataInjector(Protocol):
    """Protocol for metadata injection implementations."""

    @property
    def name(self) -> str:
        """Injector name for identification."""
        ...

    def inject(self, content: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Inject metadata into content.

        Args:
            content: Content to augment
            config: Configuration options

        Returns:
            Content with injected metadata
        """
        ...


@runtime_checkable
class EntityLinker(Protocol):
    """Protocol for entity linking implementations."""

    @property
    def name(self) -> str:
        """Linker name for identification."""
        ...

    async def link_entities(self, content: str, config: dict[str, Any]) -> dict[str, Any]:
        """Link entities in content.

        Args:
            content: Content to process
            config: Configuration options

        Returns:
            Content with linked entities
        """
        ...


@runtime_checkable
class CrossReferencer(Protocol):
    """Protocol for cross-reference implementations."""

    @property
    def name(self) -> str:
        """Referencer name for identification."""
        ...

    def add_references(
        self, content: str, references: list[dict[str, Any]], config: dict[str, Any]
    ) -> str:
        """Add cross-references to content.

        Args:
            content: Content to augment
            references: Reference documents
            config: Configuration options

        Returns:
            Content with cross-references
        """
        ...


@runtime_checkable
class TemporalContextAdder(Protocol):
    """Protocol for temporal context implementations."""

    @property
    def name(self) -> str:
        """Context adder name for identification."""
        ...

    def add_context(self, content: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Add temporal context to content.

        Args:
            content: Content to augment
            config: Configuration options

        Returns:
            Content with temporal context
        """
        ...
