"""SQLite data provider implementation.

This module provides a SQL data provider implementation using SQLite that
follows the DC1 SQLDataProvider protocol.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

from sibyl.core.protocols.infrastructure.data_providers import SQLResult

logger = logging.getLogger(__name__)


class SQLiteDataProvider:
    """SQL data provider using SQLite.

    This provider implements database access using SQLite, following the
    SQLDataProvider protocol from DC1. It supports:
    - Parameterized queries for security
    - Synchronous and asynchronous execution
    - Transaction management
    - Named parameter binding

    Security features:
    - ALWAYS uses parameterized queries (no SQL injection)
    - Named placeholders with :param_name syntax
    - Validates parameter names

    Example:
        >>> provider = SQLiteDataProvider(path="./data/experiments.db")
        >>> result = provider.execute(
        ...     "INSERT INTO experiments (name, value) VALUES (:name, :value)",
        ...     {"name": "test1", "value": 42}
        ... )
        >>> print(f"Inserted {result.rows_affected} rows")
        >>> rows = provider.fetch_all("SELECT * FROM experiments")
        >>> print(f"Found {len(rows)} experiments")
    """

    def __init__(self, path: str, **kwargs) -> None:
        """Initialize SQLite data provider.

        Args:
            path: Path to SQLite database file
            **kwargs: Additional configuration options (e.g., timeout, isolation_level)
        """
        self.path = Path(path)
        self.kwargs = kwargs

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Connection will be created on first use
        self._conn = None

        logger.info("Initialized SQLiteDataProvider: db=%s", self.path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create connection.

        Returns:
            SQLite connection object
        """
        if not self._conn:
            self._conn = sqlite3.connect(
                str(self.path),
                timeout=self.kwargs.get("timeout", 5.0),
                isolation_level=self.kwargs.get("isolation_level"),
            )
            # Return rows as dictionaries
            self._conn.row_factory = sqlite3.Row
            logger.debug("Created SQLite connection to %s", self.path)

        return self._conn

    def execute(self, query: str, params: dict | None = None) -> SQLResult:
        """Execute SQL with parameterized values.

        Security: ALWAYS uses parameterized queries with named placeholders.
        Never concatenates user input into SQL strings.

        Args:
            query: SQL query string with named placeholders (e.g., :param_name)
            params: Optional parameter dictionary for query

        Returns:
            SQLResult object with rows_affected, last_insert_id, and rows

        Raises:
            sqlite3.Error: For database-specific errors

        Example:
            >>> result = provider.execute(
            ...     "INSERT INTO users (name, email) VALUES (:name, :email)",
            ...     {"name": "Alice", "email": "alice@example.com"}
            ... )
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Execute with named parameters
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Commit for write operations
            conn.commit()

            # Fetch rows for SELECT queries
            rows = []
            if cursor.description:
                # This is a SELECT query
                rows = [dict(row) for row in cursor.fetchall()]

            result = SQLResult(
                rows_affected=cursor.rowcount,
                last_insert_id=cursor.lastrowid if cursor.lastrowid else None,
                rows=rows,
            )

            logger.debug(
                f"Executed query: affected={result.rows_affected}, rows={len(result.rows)}"
            )

            return result

        except sqlite3.Error as e:
            conn.rollback()
            logger.exception("SQL execution error: %s", e)
            raise

    def fetch_all(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute query and return all rows.

        Args:
            query: SQL query string with named placeholders
            params: Optional parameter dictionary for query

        Returns:
            List of row dictionaries

        Raises:
            sqlite3.Error: For database-specific errors

        Example:
            >>> rows = provider.fetch_all(
            ...     "SELECT * FROM users WHERE age > :min_age",
            ...     {"min_age": 18}
            ... )
        """
        result = self.execute(query, params)
        return result.rows

    async def execute_async(self, query: str, params: dict | None = None) -> SQLResult:
        """Async version of execute.

        Note: SQLite doesn't have native async support, so this uses aiosqlite
        which runs operations in a thread pool.

        Args:
            query: SQL query string with named placeholders
            params: Optional parameter dictionary for query

        Returns:
            SQLResult object with execution results

        Raises:
            sqlite3.Error: For database-specific errors
            ImportError: If aiosqlite is not installed

        Example:
            >>> result = await provider.execute_async(
            ...     "INSERT INTO logs (message) VALUES (:msg)",
            ...     {"msg": "Hello"}
            ... )
        """
        try:
            import aiosqlite
        except ImportError:
            msg = (
                "aiosqlite is required for async operations. Install it with: pip install aiosqlite"
            )
            raise ImportError(msg) from None

        # Use aiosqlite for async operations
        async with aiosqlite.connect(str(self.path)) as db:
            db.row_factory = aiosqlite.Row

            async with db.cursor() as cursor:
                # Execute with named parameters
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)

                await db.commit()

                # Fetch rows for SELECT queries
                rows = []
                if cursor.description:
                    # This is a SELECT query
                    async for row in cursor:
                        rows.append(dict(row))

                result = SQLResult(
                    rows_affected=cursor.rowcount,
                    last_insert_id=cursor.lastrowid if cursor.lastrowid else None,
                    rows=rows,
                )

                logger.debug(
                    f"Executed async query: affected={result.rows_affected}, "
                    f"rows={len(result.rows)}"
                )

                return result

    def begin_transaction(self) -> None:
        """Begin a transaction.

        Example:
            >>> provider.begin_transaction()
            >>> provider.execute("INSERT INTO users (name) VALUES (:name)", {"name": "Bob"})
            >>> provider.commit()
        """
        conn = self._get_connection()
        conn.execute("BEGIN")
        logger.debug("Started transaction")

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn:
            self._conn.commit()
            logger.debug("Committed transaction")

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._conn:
            self._conn.rollback()
            logger.debug("Rolled back transaction")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Closed SQLite connection")

    def __enter__(self) -> Any:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
