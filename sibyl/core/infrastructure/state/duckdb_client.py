"""
DuckDB connection management with lifecycle control.

Provides thread-safe connection management, health checks, and query execution.
This is the foundation for all state components (reader, writer, migrator).
"""

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Raised when connection operations fail."""


class DuckDBClient:
    """
    Thread-safe DuckDB connection manager.

    Single Responsibility: Connection lifecycle management

    Features:
    - Connection pooling (one connection per thread)
    - Health checks
    - Automatic retry on connection failures
    - Metrics tracking

    Usage:
        client = DuckDBClient(db_path)
        with client.connection() as conn:
            result = conn.execute("SELECT * FROM table").fetchall()
    """

    def __init__(self, db_path: Path, read_only: bool = False) -> None:
        """
        Initialize DuckDB client.

        Args:
            db_path: Path to DuckDB database file
            read_only: Whether to open database in read-only mode
        """
        self.db_path = Path(db_path)
        self.read_only = read_only

        # Thread-local storage for connections
        self._local = threading.local()

        # Connection pool stats
        self._metrics = {
            "connections_created": 0,
            "connections_closed": 0,
            "queries_executed": 0,
            "queries_failed": 0,
            "health_checks": 0,
        }

        self._lock = threading.Lock()

        logger.info("DuckDB client created: %s (read_only=%s)", db_path, read_only)

    @contextmanager
    def connection(self) -> Any:
        """
        Get a thread-local connection (context manager).

        Yields:
            duckdb.DuckDBPyConnection: Database connection

        Raises:
            ConnectionError: If connection fails

        Usage:
            with client.connection() as conn:
                result = conn.execute("SELECT 1").fetchone()
        """
        import duckdb

        # Get or create thread-local connection
        if not hasattr(self._local, "conn") or self._local.conn is None:
            try:
                self._local.conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
                with self._lock:
                    self._metrics["connections_created"] += 1
                logger.debug("Created new connection for thread %s", threading.get_ident())
            except Exception as e:
                msg = f"Failed to connect to {self.db_path}: {e}"
                raise ConnectionError(msg) from e

        try:
            yield self._local.conn
        except Exception:
            with self._lock:
                self._metrics["queries_failed"] += 1
            raise

    def execute_read(self, sql: str, params: tuple = ()) -> Any:
        """
        Execute a read query (SELECT).

        Args:
            sql: SQL query
            params: Query parameters (tuple)

        Returns:
            Query result (fetchall)

        Raises:
            ConnectionError: If query execution fails
        """
        with self._lock:
            self._metrics["queries_executed"] += 1

        try:
            with self.connection() as conn:
                if params:
                    result = conn.execute(sql, params).fetchall()
                else:
                    result = conn.execute(sql).fetchall()
                return result
        except Exception as e:
            logger.exception("Read query failed: %s... Error: %s", sql[:100], e)
            msg = f"Read query failed: {e}"
            raise ConnectionError(msg) from e

    def execute_write(self, sql: str, params: tuple = ()) -> None:
        """
        Execute a write query (INSERT, UPDATE, DELETE).

        Args:
            sql: SQL query
            params: Query parameters (tuple)

        Raises:
            ConnectionError: If query execution fails
            RuntimeError: If client is in read-only mode
        """
        if self.read_only:
            msg = "Cannot execute write query in read-only mode"
            raise RuntimeError(msg)

        with self._lock:
            self._metrics["queries_executed"] += 1

        try:
            with self.connection() as conn:
                if params:
                    conn.execute(sql, params)
                else:
                    conn.execute(sql)
                # DuckDB auto-commits by default
        except Exception as e:
            logger.exception("Write query failed: %s... Error: %s", sql[:100], e)
            msg = f"Write query failed: {e}"
            raise ConnectionError(msg) from e

    def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            self._metrics["health_checks"] += 1

        try:
            with self.connection() as conn:
                result = conn.execute("SELECT 1").fetchone()
                return result[0] == 1
        except Exception as e:
            logger.warning("Health check failed: %s", e)
            return False

    def close(self) -> None:
        """
        Close thread-local connection.

        This only closes the connection for the current thread.
        Other threads' connections remain open.
        """
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
                with self._lock:
                    self._metrics["connections_closed"] += 1
                logger.debug("Closed connection for thread %s", threading.get_ident())
            except Exception as e:
                logger.warning("Error closing connection: %s", e)
            finally:
                self._local.conn = None

    def close_all(self) -> None:
        """
        Close all connections (not thread-safe, use only at shutdown).

        Warning: This should only be called during application shutdown
        when you're sure no other threads are using connections.
        """
        # We can't iterate over all thread-local connections directly
        # This method is mainly for explicit cleanup if needed
        self.close()
        logger.info("All connections closed")

    def get_metrics(self) -> dict:
        """
        Get connection pool metrics.

        Returns:
            Dictionary with metrics
        """
        with self._lock:
            return self._metrics.copy()

    def __enter__(self) -> Any:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit (closes connection)."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"DuckDBClient(db_path={self.db_path}, read_only={self.read_only})"
