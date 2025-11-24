"""Default implementation for vector storage.

This implementation takes embedded documents (with vector representations)
and stores them in a configured VectorStoreProvider.
"""

import logging
from typing import Any

from sibyl.runtime.providers.factories import create_vector_store_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class StoreVectorsSubtechnique(BaseSubtechnique):
    """Subtechnique for storing vectors in a vector database.

    Example usage in pipeline config:
        - use: data_integration.store_vectors
          subtechnique: storer
          variant: default
          config:
            vector_store: docs_index
            batch_size: 100
    """

    def __init__(self) -> None:
        """Initialize store vectors subtechnique."""
        self._name = "storer"
        self._description = "Store embeddings in VectorStoreProvider"

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

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

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

        return True

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "vector_store": "docs_index",
            "batch_size": 100,
        }


def build_subtechnique() -> StoreVectorsSubtechnique:
    """Build and return the store vectors subtechnique instance.

    Returns:
        StoreVectorsSubtechnique instance
    """
    return StoreVectorsSubtechnique()
