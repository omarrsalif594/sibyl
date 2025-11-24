"""Default implementation for SQL execution.

This implementation executes SQL statements (INSERT, UPDATE, DELETE)
against a configured SQLDataProvider.
"""

import logging
from typing import Any

from sibyl.runtime.providers.factories import create_sql_provider
from sibyl.techniques.protocols import BaseSubtechnique

logger = logging.getLogger(__name__)


class ExecuteSQLSubtechnique(BaseSubtechnique):
    """Subtechnique for executing SQL statements (INSERT, UPDATE, DELETE).

    This is for write operations that don't return result sets.

    Example usage:
        - use: data_integration.query_sql
          subtechnique: execute
          variant: default
          config:
            provider: doc_metadata
            statement: "INSERT INTO logs (message) VALUES (?)"
            params: ["test message"]
    """

    def __init__(self) -> None:
        """Initialize execute SQL subtechnique."""
        self._name = "execute"
        self._description = "Execute SQL statement (INSERT, UPDATE, DELETE)"

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

        if "statement" not in config:
            msg = "Configuration must include 'statement' parameter"
            raise ValueError(msg)

        return True

    def get_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "provider": None,
            "statement": None,
            "params": [],
        }


def build_subtechnique() -> ExecuteSQLSubtechnique:
    """Build and return the execute SQL subtechnique instance.

    Returns:
        ExecuteSQLSubtechnique instance
    """
    return ExecuteSQLSubtechnique()
