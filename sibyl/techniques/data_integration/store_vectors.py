"""Store vectors technique for data integration.

This technique stores document embeddings in a VectorStoreProvider.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.runtime.providers.factories import create_vector_store_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class StoreVectorsSubtechnique(BaseSubtechnique):
    """Subtechnique for storing vectors in a vector database.

    This implementation takes embedded documents (with vector representations)
    and stores them in a configured VectorStoreProvider.

    Example usage in pipeline config:
        - use: data.store_vectors
          config:
            vector_store: docs_index  # Reference to vector store in workspace
            batch_size: 100
    """

    def __init__(self) -> None:
        """Initialize store vectors subtechnique."""
        self._name = "store_vectors"
        self._description = "Store embeddings in VectorStoreProvider"
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
        """Execute vector storage.

        Args:
            input_data: Input data containing documents with embeddings.
                Expected format:
                {
                    "documents": [
                        {
                            "id": str,
                            "content": str,
                            "embedding": List[float],
                            "metadata": dict
                        },
                        ...
                    ]
                }
            config: Configuration including:
                - vector_store: Name of vector store provider
                - batch_size: Batch size for upsert operations
                - workspace: Workspace object with provider configs

        Returns:
            Dictionary with:
                - stored_count: Number of vectors stored
                - vector_store: Store name
                - success: Boolean indicating success

        Raises:
            ValueError: If vector_store not configured or invalid
            RuntimeError: If storage fails
        """
        store_name = config.get("vector_store", "docs_index")
        batch_size = config.get("batch_size", 100)
        workspace = config.get("workspace")

        logger.info("Storing vectors in: %s", store_name)

        # Validate workspace
        if not workspace:
            msg = "Workspace context required for vector storage"
            raise ValueError(msg)

        if not hasattr(workspace, "providers") or not hasattr(workspace.providers, "vector_store"):
            msg = "Workspace does not have vector_store configured"
            raise ValueError(msg)

        store_configs = workspace.providers.vector_store
        if store_name not in store_configs:
            msg = (
                f"Vector store '{store_name}' not found in workspace. "
                f"Available stores: {list(store_configs.keys())}"
            )
            raise ValueError(msg)

        # Create vector store provider
        store_config = store_configs[store_name]
        vector_store = create_vector_store_provider(store_config)

        # Extract documents from input
        if isinstance(input_data, dict) and "documents" in input_data:
            documents = input_data["documents"]
        elif isinstance(input_data, list):
            documents = input_data
        else:
            msg = "Input data must be a dict with 'documents' key or a list of documents"
            raise ValueError(msg)

        if not documents:
            logger.warning("No documents to store")
            return {"stored_count": 0, "vector_store": store_name, "success": True}

        # Validate documents have embeddings
        for doc in documents[:1]:  # Check first document
            if "embedding" not in doc:
                msg = (
                    "Documents must have 'embedding' field. "
                    "Ensure embedder runs before store_vectors."
                )
                raise ValueError(msg)

        # Store vectors in batches
        try:
            stored_count = 0
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]

                # Prepare vectors for upsert
                vectors = []
                for doc in batch:
                    vectors.append(
                        {
                            "id": doc["id"],
                            "embedding": doc["embedding"],
                            "metadata": {
                                "content": doc.get("content", "")[:1000],  # Truncate
                                "title": doc.get("metadata", {}).get("title", ""),
                                "uri": doc.get("uri", ""),
                                **doc.get("metadata", {}),
                            },
                        }
                    )

                # Upsert batch
                vector_store.upsert(vectors)
                stored_count += len(vectors)

                logger.debug("Stored batch %s: %s vectors", i // batch_size + 1, len(vectors))

            logger.info("Successfully stored %s vectors in %s", stored_count, store_name)

            return {
                "stored_count": stored_count,
                "vector_store": store_name,
                "success": True,
            }

        except Exception as e:
            logger.exception("Failed to store vectors in %s: %s", store_name, e)
            msg = f"Vector storage failed: {e}"
            raise RuntimeError(msg) from e

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if "vector_store" not in config:
            msg = "Configuration must include 'vector_store' parameter"
            raise ValueError(msg)

        # Validate batch_size if provided
        if "batch_size" in config:
            batch_size = config["batch_size"]
            if not isinstance(batch_size, int) or batch_size <= 0:
                msg = "'batch_size' must be a positive integer"
                raise ValueError(msg)

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "vector_store": "docs_index",
            "batch_size": 100,
        }


class GetVectorStatsSubtechnique(BaseSubtechnique):
    """Subtechnique for getting vector store statistics."""

    def __init__(self) -> None:
        """Initialize get stats subtechnique."""
        self._name = "get_stats"
        self._description = "Get statistics from VectorStoreProvider"
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Get vector store statistics.

        Args:
            input_data: Input data (unused)
            config: Configuration with vector_store name and workspace

        Returns:
            Statistics from vector store
        """
        store_name = config.get("vector_store", "docs_index")
        workspace = config.get("workspace")

        if not workspace:
            msg = "Workspace context required"
            raise ValueError(msg)

        store_configs = workspace.providers.vector_store
        if store_name not in store_configs:
            msg = f"Vector store '{store_name}' not found"
            raise ValueError(msg)

        store_config = store_configs[store_name]
        vector_store = create_vector_store_provider(store_config)

        try:
            stats = vector_store.get_stats()
            logger.info("Retrieved stats from %s: %s", store_name, stats)
            return stats
        except Exception as e:
            logger.exception("Failed to get stats from %s: %s", store_name, e)
            msg = f"Failed to get stats: {e}"
            raise RuntimeError(msg) from e

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration."""
        if "vector_store" not in config:
            msg = "Configuration must include 'vector_store' parameter"
            raise ValueError(msg)

    def get_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {"vector_store": "docs_index"}


class StoreVectorsTechnique:
    """Technique orchestrator for vector storage.

    This class manages subtechniques for storing and managing vectors
    in vector databases.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize store vectors technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "store_vectors"
        self._description = "Store and manage vectors in vector databases"
        self._subtechniques: dict[str, BaseSubtechnique] = {}

        # Register subtechniques
        self.register_subtechnique(StoreVectorsSubtechnique())
        self.register_subtechnique(GetVectorStatsSubtechnique())

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
        subtechnique: str = "store_vectors",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute vector storage operation.

        Args:
            input_data: Input data
            subtechnique: Subtechnique name (default: "store_vectors")
            config: Configuration overrides
            **kwargs: Additional arguments

        Returns:
            Operation result

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
