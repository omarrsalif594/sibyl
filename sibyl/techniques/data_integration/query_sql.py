"""Query SQL technique for data integration.

This technique queries SQL databases using SQLDataProvider and returns
results for use in pipelines.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.runtime.providers.factories import create_sql_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class QuerySQLSubtechnique(BaseSubtechnique):
    """Subtechnique for querying SQL databases.

    This implementation executes SQL queries against a configured
    SQLDataProvider and returns results for pipeline processing.

    Example usage in pipeline config:
        - use: data.query_sql
          config:
            provider: doc_metadata
            query: "SELECT id, content FROM documents WHERE category = ?"
            params: ["technical"]
    """

    def __init__(self) -> None:
        """Initialize query SQL subtechnique."""
        self._name = "query_sql"
        self._description = "Query SQL database using SQLDataProvider"
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

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

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


class ExecuteSQLSubtechnique(BaseSubtechnique):
    """Subtechnique for executing SQL statements (INSERT, UPDATE, DELETE).

    This is for write operations that don't return result sets.
    """

    def __init__(self) -> None:
        """Initialize execute SQL subtechnique."""
        self._name = "execute_sql"
        self._description = "Execute SQL statement (INSERT, UPDATE, DELETE)"
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Execute SQL statement.

        Args:
            input_data: Input data (may contain params)
            config: Configuration with provider, statement, params

        Returns:
            Dictionary with:
                - rows_affected: Number of rows affected
                - success: Boolean indicating success

        Raises:
            ValueError: If configuration invalid
            RuntimeError: If execution fails
        """
        provider_name = config.get("provider")
        statement = config.get("statement")
        params = config.get("params", [])
        workspace = config.get("workspace")

        if not statement:
            msg = "Statement is required"
            raise ValueError(msg)

        logger.info("Executing SQL statement on provider: %s", provider_name)

        # Validate workspace
        if not workspace:
            msg = "Workspace context required"
            raise ValueError(msg)

        sql_configs = workspace.providers.sql
        if provider_name not in sql_configs:
            msg = f"SQL provider '{provider_name}' not found"
            raise ValueError(msg)

        # Create SQL provider
        provider_config = sql_configs[provider_name]
        sql_provider = create_sql_provider(provider_config)

        # Execute statement
        try:
            cursor = sql_provider.execute(statement, params)
            rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0

            logger.info("Statement executed, %s rows affected", rows_affected)

            return {
                "rows_affected": rows_affected,
                "success": True,
            }

        except Exception as e:
            logger.exception("Failed to execute statement on %s: %s", provider_name, e)
            msg = f"SQL execution failed: {e}"
            raise RuntimeError(msg) from e

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate configuration."""
        if "provider" not in config:
            msg = "Configuration must include 'provider' parameter"
            raise ValueError(msg)

        if "statement" not in config:
            msg = "Configuration must include 'statement' parameter"
            raise ValueError(msg)

    def get_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "provider": None,
            "statement": None,
            "params": [],
        }


class QuerySQLTechnique:
    """Technique orchestrator for SQL operations.

    This class manages subtechniques for querying and executing
    SQL statements against configured databases.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize query SQL technique.

        Args:
            config_path: Optional path to technique config file
        """
        self._name = "query_sql"
        self._description = "Query and execute SQL statements"
        self._subtechniques: dict[str, BaseSubtechnique] = {}

        # Register subtechniques
        self.register_subtechnique(QuerySQLSubtechnique())
        self.register_subtechnique(ExecuteSQLSubtechnique())

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
        subtechnique: str = "query_sql",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute SQL operation.

        Args:
            input_data: Input data
            subtechnique: Subtechnique name (default: "query_sql")
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
