"""Default implementation for SQL queries.

This implementation executes SQL queries against a configured
SQLDataProvider and returns results for pipeline processing.
"""

import logging
from typing import Any

from sibyl.runtime.providers.factories import create_sql_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class QuerySQLSubtechnique(BaseSubtechnique):
    """Subtechnique for querying SQL databases.

    Example usage in pipeline config:
        - use: data_integration.query_sql
          subtechnique: query
          variant: default
          config:
            provider: doc_metadata
            query: "SELECT id, content FROM documents WHERE category = ?"
            params: ["technical"]
    """

    def __init__(self) -> None:
        """Initialize query SQL subtechnique."""
        self._name = "query"
        self._description = "Query SQL database using SQLDataProvider"

    @property
    def name(self) -> str:
        """Get subtechnique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get subtechnique description."""
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Execute SQL query.

        Args:
            input_data: Input data (may contain params for query)
            config: Configuration including:
                - provider: Name of SQL provider
                - query: SQL query string
                - params: Optional query parameters
                - workspace: Workspace object with provider configs

        Returns:
            Dictionary with:
                - rows: List of query result rows
                - count: Number of rows returned
                - provider: Provider name

        Raises:
            ValueError: If provider not configured or invalid
            RuntimeError: If query fails
        """
        provider_name = config.get("provider")
        query = config.get("query")
        params = config.get("params", [])
        workspace = config.get("workspace")

        if not query:
            msg = "Query is required"
            raise ValueError(msg)

        logger.info("Executing SQL query on provider: %s", provider_name)

        # Validate workspace
        if not workspace:
            msg = "Workspace context required for SQL queries"
            raise ValueError(msg)

        if not hasattr(workspace, "providers") or not hasattr(workspace.providers, "sql"):
            msg = "Workspace does not have SQL providers configured"
            raise ValueError(msg)

        sql_configs = workspace.providers.sql
        if provider_name not in sql_configs:
            msg = (
                f"SQL provider '{provider_name}' not found in workspace. "
                f"Available providers: {list(sql_configs.keys())}"
            )
            raise ValueError(msg)

        # Create SQL provider
        provider_config = sql_configs[provider_name]
        sql_provider = create_sql_provider(provider_config)

        # Execute query
        try:
            cursor = sql_provider.execute(query, params)
            rows = sql_provider.fetch_all(cursor)

            logger.info("Query returned %s rows from %s", len(rows), provider_name)

            return {
                "rows": rows,
                "count": len(rows),
                "provider": provider_name,
            }

        except Exception as e:
            logger.exception("Failed to execute query on %s: %s", provider_name, e)
            msg = f"SQL query failed: {e}"
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
        if "provider" not in config:
            msg = "Configuration must include 'provider' parameter"
            raise ValueError(msg)

        if "query" not in config:
            msg = "Configuration must include 'query' parameter"
            raise ValueError(msg)

        # Validate params if provided
        if "params" in config:
            params = config["params"]
            if not isinstance(params, (list, tuple)):
                msg = "'params' must be a list or tuple"
                raise ValueError(msg)

        return True

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "provider": None,
            "query": None,
            "params": [],
        }


def build_subtechnique() -> QuerySQLSubtechnique:
    """Build and return the query SQL subtechnique instance.

    Returns:
        QuerySQLSubtechnique instance
    """
    return QuerySQLSubtechnique()
