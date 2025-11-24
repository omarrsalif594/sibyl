"""Base Resource abstraction for Sibyl templates.

This module provides the foundation for template-specific resources.
Resources represent entities that tools operate on (files, models, configs, etc.).

Example:
    ```python
    from sibyl.core.contracts.resource_base import SibylResource

    class PythonFile(SibylResource):
        resource_type = "python_file"

        def __init__(self, file_path: str, content: str):
            super().__init__(resource_id=file_path)
            self.file_path = file_path
            self.content = content

        def to_dict(self) -> dict:
            return {
                "resource_id": self.resource_id,
                "resource_type": self.resource_type,
                "file_path": self.file_path,
                "content": self.content,
                "metadata": self.metadata
            }

        @classmethod
        def from_dict(cls, data: dict) -> "PythonFile":
            return cls(
                file_path=data["file_path"],
                content=data["content"]
            )
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ResourceMetadata:
    """Metadata about a resource.

    Attributes:
        created_at: When resource was created
        updated_at: When resource was last updated
        author: Who created/owns the resource
        tags: List of tags for categorization
        properties: Arbitrary key-value properties
    """

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


class SibylResource(ABC):
    """Base class for all Sibyl resources.

    Resources are domain entities that tools manipulate.
    Templates define concrete resource types (e.g., PythonFile, TerraformModule).

    Attributes:
        resource_id: Unique identifier for this resource
        resource_type: Type identifier (e.g., "python_file", "terraform_module")
        metadata: Resource metadata
    """

    resource_type: str = ""  # Subclasses must set this

    def __init__(self, resource_id: str, metadata: ResourceMetadata | None = None) -> None:
        """Initialize resource.

        Args:
            resource_id: Unique identifier
            metadata: Optional metadata
        """
        self.resource_id = resource_id
        self.metadata = metadata or ResourceMetadata()

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert resource to dictionary representation.

        Returns:
            Dict with resource data
        """
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "SibylResource":
        """Create resource from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Resource instance
        """
        ...

    def get_resource_id(self) -> str:
        """Get resource identifier.

        Returns:
            Resource ID
        """
        return self.resource_id

    def get_resource_type(self) -> str:
        """Get resource type.

        Returns:
            Resource type identifier
        """
        return self.resource_type

    def update_metadata(self, **kwargs: Any) -> None:
        """Update resource metadata.

        Args:
            **kwargs: Metadata fields to update
        """
        self.metadata.updated_at = datetime.utcnow()

        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
            else:
                self.metadata.properties[key] = value

    def add_tag(self, tag: str) -> None:
        """Add tag to resource.

        Args:
            tag: Tag to add
        """
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if resource has tag.

        Args:
            tag: Tag to check

        Returns:
            True if resource has tag
        """
        return tag in self.metadata.tags


class ResourceManager:
    """Manager for resource instances.

    Templates use this to register and retrieve resources.
    """

    def __init__(self) -> None:
        self._resources: dict[str, SibylResource] = {}

    def register(self, resource: SibylResource) -> None:
        """Register a resource.

        Args:
            resource: Resource instance
        """
        self._resources[resource.resource_id] = resource

    def get(self, resource_id: str) -> SibylResource | None:
        """Get resource by ID.

        Args:
            resource_id: Resource identifier

        Returns:
            Resource instance or None
        """
        return self._resources.get(resource_id)

    def get_by_type(self, resource_type: str) -> list[SibylResource]:
        """Get all resources of a type.

        Args:
            resource_type: Resource type to filter by

        Returns:
            List of matching resources
        """
        return [r for r in self._resources.values() if r.resource_type == resource_type]

    def get_all(self) -> list[SibylResource]:
        """Get all registered resources.

        Returns:
            List of all resources
        """
        return list(self._resources.values())

    def remove(self, resource_id: str) -> bool:
        """Remove resource by ID.

        Args:
            resource_id: Resource identifier

        Returns:
            True if removed, False if not found
        """
        if resource_id in self._resources:
            del self._resources[resource_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered resources."""
        self._resources.clear()
