"""Default implementation for vector store statistics.

This implementation retrieves statistics from a configured VectorStoreProvider.
"""

import logging
from typing import Any

from sibyl.runtime.providers.factories import create_vector_store_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class GetVectorStatsSubtechnique(BaseSubtechnique):
    """Subtechnique for getting vector store statistics.

    Example usage:
        - use: data_integration.store_vectors
          subtechnique: get_stats
          variant: default
          config:
            vector_store: docs_index
    """

    def __init__(self) -> None:
        """Initialize get stats subtechnique."""
        self._name = "get_stats"
        self._description = "Get statistics from VectorStoreProvider"

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

        Raises:
            ValueError: If configuration invalid
            RuntimeError: If operation fails
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
        return True

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {"vector_store": "docs_index"}


def build_subtechnique() -> GetVectorStatsSubtechnique:
    """Build and return the get stats subtechnique instance.

    Returns:
        GetVectorStatsSubtechnique instance
    """
    return GetVectorStatsSubtechnique()
