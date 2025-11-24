"""Load documents technique for data integration.

This technique loads documents from a DocumentSourceProvider and prepares them
for processing in a RAG pipeline.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.runtime.providers.factories import create_document_source
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class LoadDocumentsSubtechnique(BaseSubtechnique):
    """Subtechnique for loading documents from a configured source.

    This implementation loads documents from a DocumentSourceProvider
    and returns them in a format suitable for chunking and embedding.

    Example usage in pipeline config:
        - use: data.load_documents
          config:
            source: docs_local  # Reference to document source in workspace
            limit: 100
            modified_after: "2024-01-01"
    """

    def __init__(self) -> None:
        """Initialize load documents subtechnique."""
        self._name = "load_documents"
        self._description = "Load documents from DocumentSourceProvider"
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        """Get subtechnique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get subtechnique description."""
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Execute document loading.

        Args:
            input_data: Input data (workspace context or previous step output)
            config: Configuration including:
                - source: Name of document source provider
                - limit: Optional max number of documents
                - modified_after: Optional datetime filter
                - workspace: Workspace object with provider configs

        Returns:
            Dictionary with:
                - documents: List of loaded documents
                - count: Number of documents loaded
                - source: Source name

        Raises:
            ValueError: If source not configured or invalid
            RuntimeError: If loading fails
        """
        source_name = config.get("source", "docs_local")
        limit = config.get("limit")
        modified_after = config.get("modified_after")
        workspace = config.get("workspace")

        logger.info("Loading documents from source: %s", source_name)

        # Get source configuration from workspace
        if not workspace:
            msg = "Workspace context required for document loading"
            raise ValueError(msg)

        if not hasattr(workspace, "providers") or not hasattr(
            workspace.providers, "document_sources"
        ):
            msg = "Workspace does not have document_sources configured"
            raise ValueError(msg)

        source_configs = workspace.providers.document_sources
        if source_name not in source_configs:
            msg = (
                f"Document source '{source_name}' not found in workspace. "
                f"Available sources: {list(source_configs.keys())}"
            )
            raise ValueError(msg)

        # Create document source provider
        source_config = source_configs[source_name]
        source = create_document_source(source_config)

        # Build filters
        filters = {}
        if limit:
            filters["limit"] = limit
        if modified_after:
            filters["modified_after"] = modified_after

        # Load documents
        try:
            documents = []
            for doc in source.iterate_documents(**filters):
                documents.append(
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "uri": doc.uri,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    }
                )

            logger.info("Loaded %s documents from %s", len(documents), source_name)

            return {
                "documents": documents,
                "count": len(documents),
                "source": source_name,
            }

        except Exception as e:
            logger.exception("Failed to load documents from %s: %s", source_name, e)
            msg = f"Document loading failed: {e}"
            raise RuntimeError(msg) from e

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if "source" not in config:
            msg = "Configuration must include 'source' parameter"
            raise ValueError(msg)

        # Validate limit if provided
        if "limit" in config:
            limit = config["limit"]
            if not isinstance(limit, int) or limit <= 0:
                msg = "'limit' must be a positive integer"
                raise ValueError(msg)

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "source": "docs_local",
            "limit": None,
            "modified_after": None,
        }


class LoadDocumentsTechnique:
    """Technique orchestrator for document loading.

    This class manages the load_documents subtechnique and provides
    the interface for the Sibyl technique registry.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize load documents technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "load_documents"
        self._description = "Load documents from data providers"
        self._subtechniques: dict[str, BaseSubtechnique] = {}

        # Register default subtechnique
        self.register_subtechnique(LoadDocumentsSubtechnique())

    @property
    def name(self) -> str:
        """Get technique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get technique description."""
        return self._description

    @property
    def subtechniques(self) -> dict[str, BaseSubtechnique]:
        """Get registered subtechniques."""
        return self._subtechniques

    def register_subtechnique(self, subtechnique: BaseSubtechnique) -> None:
        """Register a subtechnique.

        Args:
            subtechnique: Subtechnique to register
        """
        self._subtechniques[subtechnique.name] = subtechnique
        logger.debug("Registered subtechnique: %s", subtechnique.name)

    def execute(
        self,
        input_data: Any,
        subtechnique: str = "load_documents",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute document loading.

        Args:
            input_data: Input data
            subtechnique: Subtechnique name (default: "load_documents")
            config: Configuration overrides
            **kwargs: Additional arguments

        Returns:
            Loaded documents result

        Raises:
            ValueError: If subtechnique not found
            RuntimeError: If execution fails
        """
        if subtechnique not in self._subtechniques:
            msg = (
                f"Subtechnique '{subtechnique}' not found. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        impl = self._subtechniques[subtechnique]

        # Merge configuration
        merged_config = impl.get_config().copy()
        if config:
            merged_config.update(config)

        # Add kwargs to config
        merged_config.update(kwargs)

        # Validate configuration
        impl.validate_config(merged_config)

        # Execute
        try:
            return impl.execute(input_data, merged_config)
        except Exception as e:
            logger.exception("Failed to execute %s: %s", subtechnique, e)
            msg = f"Execution failed: {e}"
            raise RuntimeError(msg) from e
