"""External Handle artifacts for managing external resources and state.

This module provides typed artifacts for tracking and managing external resources
created by MCP tools, such as:
- External collections in vector databases (Qdrant, RAG Memory)
- Workflow instances in orchestration systems (Conductor)
- Conversation sessions in reasoning systems (Deep Code Reasoning)
- Time-series forecasts in prediction systems (Chronulus)

It implements GAP-STATE-001 (External State Handle).

Example:
    from sibyl.core.artifacts.external_handle import ExternalHandle, ResourceType

    # Create handle for external resource
    handle = ExternalHandle(
        provider="rag_memory",
        resource_type=ResourceType.COLLECTION,
        resource_id="mem_12345",
        metadata={"name": "customer_docs", "size": 1500}
    )

    # Delete resource when done
    await handle.delete(mcp_adapter)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of external resources that can be tracked.

    These types categorize different kinds of external state maintained by MCP providers.
    """

    COLLECTION = "collection"  # Vector/document collection
    WORKFLOW = "workflow"  # Workflow definition or execution
    SESSION = "session"  # Conversation/analysis session
    FORECAST = "forecast"  # Time-series forecast
    ENTITY = "entity"  # Knowledge graph entity
    RELATION = "relation"  # Knowledge graph relation
    DOCUMENT = "document"  # Stored document
    EMBEDDING = "embedding"  # Embedding vector
    CHECKPOINT = "checkpoint"  # State checkpoint
    OTHER = "other"  # Generic external resource


@dataclass
class ExternalHandle:
    """Artifact for tracking external resources created by MCP tools.

    This handle represents any external state or resource that needs to be tracked
    and potentially cleaned up. It provides a unified interface for managing
    resources across different MCP providers.

    Design Principles:
    - Explicit: All operations require passing MCPToolAdapter
    - Serializable: Can be JSON-serialized for persistence
    - Provider-agnostic: Works with any MCP that creates trackable resources
    - Lifecycle-aware: Tracks creation, last access, and deletion

    Attributes:
        provider: MCP provider name (e.g., "rag_memory", "conductor")
        resource_type: Type of resource (collection, workflow, session, etc.)
        resource_id: Unique resource identifier from MCP
        metadata: Additional metadata about the resource (name, size, tags, etc.)
        delete_tool: Optional tool name for resource deletion
        created_at: Timestamp when handle was created
        last_accessed_at: Timestamp of last interaction with resource
        deleted: Whether resource has been deleted

    Example:
        # Create handle for external collection
        handle = ExternalHandle(
            provider="qdrant_mcp",
            resource_type=ResourceType.COLLECTION,
            resource_id="col_abc123",
            metadata={"name": "research_docs", "vector_count": 5000},
            delete_tool="delete_collection"
        )

        # Use resource
        await handle.refresh(status_adapter)

        # Clean up when done
        await handle.delete(delete_adapter)
    """

    # Core identifiers
    provider: str
    resource_type: ResourceType
    resource_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    # Optional lifecycle management
    delete_tool: str | None = None
    refresh_tool: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)
    deleted: bool = False

    def __post_init__(self) -> None:
        """Validate handle after initialization."""
        if not self.provider:
            msg = "provider must be specified"
            raise ValueError(msg)
        if not self.resource_id:
            msg = "resource_id must be specified"
            raise ValueError(msg)

    async def delete(self, mcp_adapter: "MCPToolAdapter") -> None:
        """Delete the external resource.

        This method attempts to delete the resource by calling a deletion tool on the
        MCP provider. If no delete_tool is configured, raises an error.

        Args:
            mcp_adapter: MCP adapter instance for making tool calls

        Raises:
            ValueError: If delete_tool is not configured
            RuntimeError: If deletion fails

        Example:
            from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

            delete_adapter = MCPToolAdapter(provider, "deleteDocument")
            await handle.delete(delete_adapter)
        """
        if not self.delete_tool:
            msg = f"No delete_tool configured for {self.resource_type.value} {self.resource_id}"
            raise ValueError(msg)

        if self.deleted:
            logger.warning(
                f"Resource {self.resource_id} already marked as deleted, skipping deletion"
            )
            return

        try:
            logger.info(
                f"Deleting {self.resource_type.value} {self.resource_id} "
                f"from provider {self.provider}"
            )

            # Call deletion tool
            from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

            delete_adapter = MCPToolAdapter(mcp_adapter.provider, self.delete_tool)

            # Try different parameter names for resource ID
            try:
                await delete_adapter(resource_id=self.resource_id)
            except Exception:
                # Fallback to common alternative parameter names
                try:
                    await delete_adapter(id=self.resource_id)
                except Exception:
                    await delete_adapter(**{f"{self.resource_type.value}_id": self.resource_id})

            self.deleted = True
            logger.info("Successfully deleted resource %s", self.resource_id)

        except Exception as e:
            logger.exception("Failed to delete resource %s: %s", self.resource_id, e)
            msg = f"Failed to delete {self.resource_type.value} {self.resource_id}: {e}"
            raise RuntimeError(msg) from e

    async def refresh(self, mcp_adapter: "MCPToolAdapter") -> dict[str, Any]:
        """Refresh resource metadata from provider.

        This method fetches current metadata about the resource, updating the
        last_accessed_at timestamp.

        Args:
            mcp_adapter: MCP adapter instance for making tool calls

        Returns:
            Updated metadata dictionary

        Raises:
            ValueError: If refresh_tool is not configured
            RuntimeError: If refresh fails

        Example:
            status_adapter = MCPToolAdapter(provider, "get_collection_info")
            metadata = await handle.refresh(status_adapter)
            print(f"Collection size: {metadata.get('size')}")
        """
        if not self.refresh_tool:
            msg = f"No refresh_tool configured for {self.resource_type.value} {self.resource_id}"
            raise ValueError(msg)

        try:
            logger.debug(f"Refreshing metadata for {self.resource_type.value} {self.resource_id}")

            # Call refresh tool
            from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

            refresh_adapter = MCPToolAdapter(mcp_adapter.provider, self.refresh_tool)

            # Try different parameter names
            try:
                result = await refresh_adapter(resource_id=self.resource_id)
            except Exception:
                try:
                    result = await refresh_adapter(id=self.resource_id)
                except Exception:
                    result = await refresh_adapter(
                        **{f"{self.resource_type.value}_id": self.resource_id}
                    )

            # Update metadata and timestamp
            if isinstance(result, dict):
                self.metadata.update(result)

            self.last_accessed_at = datetime.now()

            logger.debug("Refreshed metadata for resource %s: %s", self.resource_id, self.metadata)

            return self.metadata

        except Exception as e:
            logger.exception("Failed to refresh resource %s: %s", self.resource_id, e)
            msg = f"Failed to refresh {self.resource_type.value} {self.resource_id}: {e}"
            raise RuntimeError(msg) from e

    @classmethod
    def from_mcp_response(
        cls,
        response: dict[str, Any],
        provider: str,
        resource_type: ResourceType,
        resource_id_key: str = "resource_id",
        **kwargs,
    ) -> "ExternalHandle":
        """Factory method to create handle from MCP tool response.

        Args:
            response: MCP tool response containing resource ID
            provider: MCP provider name
            resource_type: Type of resource created
            resource_id_key: Key name for resource ID in response (default: "resource_id")
            **kwargs: Additional ExternalHandle parameters

        Returns:
            New ExternalHandle instance

        Raises:
            ValueError: If response doesn't contain resource ID

        Example:
            response = {"document_id": "doc_123", "status": "created"}
            handle = ExternalHandle.from_mcp_response(
                response,
                provider="rag_memory",
                resource_type=ResourceType.DOCUMENT,
                resource_id_key="document_id",
                delete_tool="deleteDocuments"
            )
        """
        resource_id = response.get(resource_id_key)
        if not resource_id:
            # Try common alternative keys
            for alt_key in ["id", f"{resource_type.value}_id", "resource_id"]:
                resource_id = response.get(alt_key)
                if resource_id:
                    break

        if not resource_id:
            msg = (
                f"MCP response does not contain resource ID (tried keys: "
                f"{resource_id_key}, id, {resource_type.value}_id, resource_id): "
                f"{response}"
            )
            raise ValueError(msg)

        # Extract metadata from response
        metadata = {k: v for k, v in response.items() if k != resource_id_key}

        return cls(
            provider=provider,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence/debugging.

        Returns:
            Dictionary representation (JSON-serializable)
        """
        return {
            "provider": self.provider,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "metadata": self.metadata,
            "delete_tool": self.delete_tool,
            "refresh_tool": self.refresh_tool,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "deleted": self.deleted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExternalHandle":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ExternalHandle instance
        """
        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"])
        last_accessed_at = datetime.fromisoformat(data["last_accessed_at"])

        # Parse resource type
        resource_type = ResourceType(data["resource_type"])

        return cls(
            provider=data["provider"],
            resource_type=resource_type,
            resource_id=data["resource_id"],
            metadata=data.get("metadata", {}),
            delete_tool=data.get("delete_tool"),
            refresh_tool=data.get("refresh_tool"),
            created_at=created_at,
            last_accessed_at=last_accessed_at,
            deleted=data.get("deleted", False),
        )


# Custom exceptions
class ExternalResourceError(Exception):
    """Base exception for external resource errors."""


class ResourceNotFoundError(ExternalResourceError):
    """Raised when external resource cannot be found."""


class ResourceAlreadyDeletedError(ExternalResourceError):
    """Raised when attempting to interact with deleted resource."""
