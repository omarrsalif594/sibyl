"""State persistence store implementations.

This module provides abstractions for persisting state handles and sessions
to various backends. DuckDB is the default backend for its simplicity and
SQL capabilities.

Example:
    from sibyl.core.persistence import DuckDBStateStore
    from sibyl.core.artifacts.session_handle import SessionHandle

    # Create store
    store = DuckDBStateStore("./data/state.duckdb")

    # Save session
    session = SessionHandle(...)
    await store.save_session(session)

    # Load session
    loaded = await store.load_session(session.session_id)
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StateStore(ABC):
    """Abstract base class for state persistence.

    Defines the interface for storing and retrieving state handles.
    Implementations should handle:
    - Session persistence with checkpoints
    - External resource handle tracking
    - Pipeline execution state snapshots
    """

    @abstractmethod
    async def save_session(self, session: "SessionHandle") -> None:
        """Save or update a session.

        Args:
            session: SessionHandle to persist
        """

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional["SessionHandle"]:
        """Load a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionHandle if found, None otherwise
        """

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier
        """

    @abstractmethod
    async def list_sessions(
        self, provider: str | None = None, status: str | None = None
    ) -> list[str]:
        """List session IDs matching criteria.

        Args:
            provider: Optional provider filter
            status: Optional status filter

        Returns:
            List of session IDs
        """

    @abstractmethod
    async def save_external_handle(self, handle: "ExternalHandle") -> None:
        """Save or update an external resource handle.

        Args:
            handle: ExternalHandle to persist
        """

    @abstractmethod
    async def load_external_handle(self, resource_id: str) -> Optional["ExternalHandle"]:
        """Load an external handle by resource ID.

        Args:
            resource_id: Resource identifier

        Returns:
            ExternalHandle if found, None otherwise
        """

    @abstractmethod
    async def delete_external_handle(self, resource_id: str) -> None:
        """Delete an external handle.

        Args:
            resource_id: Resource identifier
        """

    @abstractmethod
    async def list_external_handles(
        self, provider: str | None = None, resource_type: str | None = None
    ) -> list[str]:
        """List resource IDs matching criteria.

        Args:
            provider: Optional provider filter
            resource_type: Optional resource type filter

        Returns:
            List of resource IDs
        """


class DuckDBStateStore(StateStore):
    """DuckDB-backed state store implementation.

    Uses DuckDB for persistent storage of sessions and external handles.
    Schema:
    - sessions: session_id, provider, session_type, state (JSON), status, timestamps
    - external_handles: resource_id, provider, resource_type, metadata (JSON), timestamps
    - checkpoints: checkpoint_id, session_id, name, state (JSON), created_at

    Attributes:
        db_path: Path to DuckDB database file
        auto_checkpoint: Whether to automatically checkpoint sessions on save
    """

    def __init__(
        self, db_path: str = "./data/sibyl_state.duckdb", auto_checkpoint: bool = False
    ) -> None:
        """Initialize DuckDB state store.

        Args:
            db_path: Path to database file (created if doesn't exist)
            auto_checkpoint: Whether to auto-checkpoint on session save
        """
        self.db_path = Path(db_path)
        self.auto_checkpoint = auto_checkpoint

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database (lazy connection)
        self._conn = None

        logger.info("Initialized DuckDBStateStore at %s", self.db_path)

    def _get_connection(self) -> Any:
        """Get or create database connection."""
        if self._conn is None:
            try:
                import duckdb  # optional dependency

            except ImportError:
                msg = "duckdb is required for DuckDBStateStore. Install with: pip install duckdb"
                raise ImportError(msg) from None

            self._conn = duckdb.connect(str(self.db_path))
            self._initialize_schema()

        return self._conn

    def _initialize_schema(self) -> None:
        """Create database schema if not exists."""
        conn = self._conn

        # Sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR PRIMARY KEY,
                provider VARCHAR NOT NULL,
                session_type VARCHAR NOT NULL,
                state JSON NOT NULL,
                status VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                metadata JSON,
                INDEX idx_provider (provider),
                INDEX idx_status (status)
            )
        """)

        # Checkpoints table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id VARCHAR PRIMARY KEY,
                session_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                state JSON NOT NULL,
                created_at TIMESTAMP NOT NULL,
                metadata JSON,
                INDEX idx_session (session_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        # External handles table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS external_handles (
                resource_id VARCHAR PRIMARY KEY,
                provider VARCHAR NOT NULL,
                resource_type VARCHAR NOT NULL,
                metadata JSON,
                delete_tool VARCHAR,
                refresh_tool VARCHAR,
                created_at TIMESTAMP NOT NULL,
                last_accessed_at TIMESTAMP NOT NULL,
                deleted BOOLEAN NOT NULL DEFAULT FALSE,
                INDEX idx_provider (provider),
                INDEX idx_resource_type (resource_type),
                INDEX idx_deleted (deleted)
            )
        """)

        logger.debug("DuckDB schema initialized")

    async def save_session(self, session: "SessionHandle") -> None:
        """Save or update a session."""

        conn = self._get_connection()

        # Serialize session
        data = session.to_dict()

        # Save session record
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions
            (session_id, provider, session_type, state, status, created_at, updated_at, completed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                data["session_id"],
                data["provider"],
                data["session_type"],
                json.dumps(data["state"]),
                data["status"],
                data["created_at"],
                data["updated_at"],
                data["completed_at"],
                json.dumps(data["metadata"]),
            ],
        )

        # Save checkpoints
        for checkpoint in data["checkpoints"]:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                (checkpoint_id, session_id, name, state, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    checkpoint["id"],
                    data["session_id"],
                    checkpoint["name"],
                    json.dumps(checkpoint["state"]),
                    checkpoint["created_at"],
                    json.dumps(checkpoint["metadata"]),
                ],
            )

        logger.debug(
            "Saved session %s with %s checkpoint(s)", session.session_id, len(data["checkpoints"])
        )

    async def load_session(self, session_id: str) -> Optional["SessionHandle"]:
        """Load a session by ID."""
        from sibyl.core.artifacts.session_handle import SessionHandle

        conn = self._get_connection()

        # Load session record
        result = conn.execute(
            """
            SELECT session_id, provider, session_type, state, status,
                   created_at, updated_at, completed_at, metadata
            FROM sessions
            WHERE session_id = ?
            """,
            [session_id],
        ).fetchone()

        if not result:
            return None

        # Load checkpoints
        checkpoints = conn.execute(
            """
            SELECT checkpoint_id, name, state, created_at, metadata
            FROM checkpoints
            WHERE session_id = ?
            ORDER BY created_at
            """,
            [session_id],
        ).fetchall()

        # Reconstruct session
        session_data = {
            "session_id": result[0],
            "provider": result[1],
            "session_type": result[2],
            "state": json.loads(result[3]),
            "status": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "completed_at": result[7],
            "metadata": json.loads(result[8]) if result[8] else {},
            "checkpoints": [
                {
                    "id": cp[0],
                    "name": cp[1],
                    "state": json.loads(cp[2]),
                    "created_at": cp[3],
                    "metadata": json.loads(cp[4]) if cp[4] else {},
                }
                for cp in checkpoints
            ],
        }

        logger.debug(
            "Loaded session %s with %s checkpoint(s)", session_id, len(session_data["checkpoints"])
        )

        return SessionHandle.from_dict(session_data)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session (cascades to checkpoints)."""
        conn = self._get_connection()

        conn.execute("DELETE FROM sessions WHERE session_id = ?", [session_id])

        logger.info("Deleted session %s", session_id)

    async def list_sessions(
        self, provider: str | None = None, status: str | None = None
    ) -> list[str]:
        """List session IDs matching criteria."""
        conn = self._get_connection()

        query = "SELECT session_id FROM sessions WHERE 1=1"
        params = []

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC"

        results = conn.execute(query, params).fetchall()
        return [row[0] for row in results]

    async def save_external_handle(self, handle: "ExternalHandle") -> None:
        """Save or update an external resource handle."""

        conn = self._get_connection()

        data = handle.to_dict()

        conn.execute(
            """
            INSERT OR REPLACE INTO external_handles
            (resource_id, provider, resource_type, metadata, delete_tool, refresh_tool,
             created_at, last_accessed_at, deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                data["resource_id"],
                data["provider"],
                data["resource_type"],
                json.dumps(data["metadata"]),
                data["delete_tool"],
                data["refresh_tool"],
                data["created_at"],
                data["last_accessed_at"],
                data["deleted"],
            ],
        )

        logger.debug("Saved external handle %s", handle.resource_id)

    async def load_external_handle(self, resource_id: str) -> Optional["ExternalHandle"]:
        """Load an external handle by resource ID."""
        from sibyl.core.artifacts.external_handle import ExternalHandle

        conn = self._get_connection()

        result = conn.execute(
            """
            SELECT resource_id, provider, resource_type, metadata, delete_tool, refresh_tool,
                   created_at, last_accessed_at, deleted
            FROM external_handles
            WHERE resource_id = ?
            """,
            [resource_id],
        ).fetchone()

        if not result:
            return None

        handle_data = {
            "resource_id": result[0],
            "provider": result[1],
            "resource_type": result[2],
            "metadata": json.loads(result[3]) if result[3] else {},
            "delete_tool": result[4],
            "refresh_tool": result[5],
            "created_at": result[6],
            "last_accessed_at": result[7],
            "deleted": result[8],
        }

        logger.debug("Loaded external handle %s", resource_id)

        return ExternalHandle.from_dict(handle_data)

    async def delete_external_handle(self, resource_id: str) -> None:
        """Delete an external handle."""
        conn = self._get_connection()

        conn.execute("DELETE FROM external_handles WHERE resource_id = ?", [resource_id])

        logger.info("Deleted external handle %s", resource_id)

    async def list_external_handles(
        self, provider: str | None = None, resource_type: str | None = None
    ) -> list[str]:
        """List resource IDs matching criteria."""
        conn = self._get_connection()

        query = "SELECT resource_id FROM external_handles WHERE deleted = FALSE"
        params = []

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)

        query += " ORDER BY last_accessed_at DESC"

        results = conn.execute(query, params).fetchall()
        return [row[0] for row in results]

    async def cleanup_deleted_handles(self) -> int:
        """Remove external handles marked as deleted.

        Returns:
            Number of handles removed
        """
        conn = self._get_connection()

        result = conn.execute("DELETE FROM external_handles WHERE deleted = TRUE").fetchone()

        count = result[0] if result else 0

        logger.info("Cleaned up %s deleted external handle(s)", count)

        return count

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("Closed DuckDB connection")
