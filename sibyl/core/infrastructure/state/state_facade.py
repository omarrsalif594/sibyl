"""
State facade providing unified interface to state components.

Coordinates DuckDBClient, StateReader, StateWriter, StateMigrator, and BlobManager.
This is the new recommended interface for state operations.
"""

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from .blob_manager import BlobManager
from .duckdb_client import DuckDBClient
from .state_migrator import StateMigrator
from .state_reader import StateReader
from .writer_queue import StateWriter

logger = logging.getLogger(__name__)


class StateFacade:
    """
    Unified interface to state components.

    Single Responsibility: Component coordination

    Architecture:
    - DuckDBClient: Connection management
    - StateReader: Read operations
    - StateWriter: Write operations (async queue)
    - StateMigrator: Schema/integrity management
    - BlobManager: Large object storage

    Usage:
        # Initialize
        facade = StateFacade(db_path)
        await facade.initialize()

        # Read operations
        conv = facade.get_conversation("conv-123")
        stats = facade.get_stats()

        # Write operations
        await facade.create_conversation(id="conv-456", ...)
        await facade.update_conversation("conv-456", status="completed")

        # Cleanup
        await facade.shutdown()
    """

    EXPECTED_SCHEMA_VERSION = 2

    def __init__(
        self,
        db_path: Path,
        blob_storage_root: Path | None = None,
    ) -> None:
        """
        Initialize state facade.

        Args:
            db_path: Path to DuckDB database file
            blob_storage_root: Root directory for blob storage (defaults to db_path.parent / "blobs")
        """
        self.db_path = Path(db_path)
        self.blob_storage_root = blob_storage_root or (self.db_path.parent / "blobs")

        # Components (initialized in initialize())
        self.client: DuckDBClient | None = None
        self.reader: StateReader | None = None
        self.writer: StateWriter | None = None
        self.migrator: StateMigrator | None = None
        self.blob_manager: BlobManager | None = None

        self._initialized = False

        logger.info("StateFacade created: %s", db_path)

    async def initialize(self) -> None:
        """
        Boot sequence with integrity check and crash recovery.

        Steps:
        1. Create database if it doesn't exist
        2. Run integrity check
        3. Validate schema version
        4. Initialize components (client, reader, writer, migrator, blob_manager)
        5. Start writer queue
        6. Run crash recovery

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            logger.warning("StateFacade already initialized")
            return

        logger.info("Initializing StateFacade...")

        try:
            # 1. Check if database exists, create if not
            if not self.db_path.exists():
                logger.info("Database does not exist, creating...")
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                from .migrations import create_initial_schema

                create_initial_schema(self.db_path)

            # 2. Initialize components
            self.client = DuckDBClient(self.db_path, read_only=False)
            self.migrator = StateMigrator(
                self.client, expected_version=self.EXPECTED_SCHEMA_VERSION, db_path=self.db_path
            )
            self.blob_manager = BlobManager(self.blob_storage_root)

            # 3. Run full validation (integrity + schema + tables)
            validation = self.migrator.full_validation()
        except Exception as e:
            logger.exception("✗ StateFacade initialization failed: %s", e)
            # Cleanup partial initialization
            if self.writer:
                await self.writer.stop()
            raise
        else:
            if not validation.passed:
                msg = f"Validation failed: {validation.message}"
                raise RuntimeError(msg)

            try:
                # 4. Initialize reader (with blob manager)
                self.reader = StateReader(self.client, self.blob_manager)

                # 5. Initialize and start writer queue
                self.writer = StateWriter(self.db_path)
                await self.writer.start()

                # 6. Run crash recovery
                await self._crash_recovery()

                self._initialized = True
                logger.info("✓ StateFacade initialized successfully")

            except Exception as e:
                logger.exception("✗ StateFacade initialization failed: %s", e)
                # Cleanup partial initialization
                if self.writer:
                    await self.writer.stop()
                raise

    async def shutdown(self) -> None:
        """
        Shutdown facade gracefully.

        Stops writer queue and closes connections.
        """
        if not self._initialized:
            logger.warning("StateFacade not initialized, nothing to shutdown")
            return

        logger.info("Shutting down StateFacade...")

        try:
            # Stop writer queue (flushes pending writes)
            if self.writer:
                await self.writer.stop()
                self.writer = None

            # Close client connections
            if self.client:
                self.client.close()
                self.client = None

            self._initialized = False
            logger.info("✓ StateFacade shut down successfully")

        except Exception as e:
            logger.exception("Error during shutdown: %s", e)

    async def _crash_recovery(self) -> None:
        """
        Recover from unclean shutdown.

        Marks interrupted conversations as 'crashed'.
        """
        logger.info("Running crash recovery...")

        await self.writer.write(
            """
            UPDATE conversations
            SET status = 'crashed'
            WHERE status = 'running' AND finished_at IS NULL
            """,
            (),
        )

        logger.info("✓ Crash recovery complete")

    # =========================================================================
    # Conversation Management (delegated)
    # =========================================================================

    async def create_conversation(
        self,
        id: str,
        workflow_type: str,
        token_budget: int,
        context_hash: str,
        config_version: str,
        **kwargs,
    ) -> None:
        """Create a new conversation (delegates to writer)."""
        await self.writer.write(
            """
            INSERT INTO conversations (
                id, workflow_type, started_at, status,
                token_budget, token_spent, cost_usd,
                context_hash, config_version, created_by, tags
            ) VALUES (?, ?, CURRENT_TIMESTAMP, 'running', ?, 0, 0.0, ?, ?, ?, ?)
            """,
            (
                id,
                workflow_type,
                token_budget,
                context_hash,
                config_version,
                kwargs.get("created_by"),
                kwargs.get("tags"),
            ),
        )

        logger.info("Created conversation: %s (workflow=%s)", id, workflow_type)

    async def update_conversation(self, id: str, status: str | None = None, **kwargs) -> None:
        """Update conversation (delegates to writer)."""
        # Build UPDATE query with only validated column names
        # This prevents SQL injection by whitelisting allowed columns
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if "token_spent" in kwargs:
            updates.append("token_spent = ?")
            params.append(kwargs["token_spent"])

        if "cost_usd" in kwargs:
            updates.append("cost_usd = ?")
            params.append(kwargs["cost_usd"])

        if status in ("completed", "failed", "cancelled"):
            updates.append("finished_at = CURRENT_TIMESTAMP")

        if not updates:
            return

        params.append(id)

        # Safe: updates list contains only validated column names from above
        await self.writer.write(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )

    def get_conversation(self, id: str) -> dict[str, Any] | None:
        """Get conversation by ID (delegates to reader)."""
        return self.reader.get_conversation(id)

    def list_conversations(self, **filters) -> list[dict[str, Any]]:
        """List conversations (delegates to reader)."""
        return self.reader.list_conversations(**filters)

    def count_conversations(self, **filters) -> int:
        """Count conversations (delegates to reader)."""
        return self.reader.count_conversations(**filters)

    # =========================================================================
    # Checkpoint Management (delegated)
    # =========================================================================

    async def create_checkpoint(
        self,
        id: str,
        conversation_id: str,
        phase: str,
        phase_number: int,
        context_hash: str,
        **kwargs,
    ) -> None:
        """Create phase checkpoint (delegates to writer)."""
        await self.writer.write(
            """
            INSERT INTO phase_checkpoints (
                id, conversation_id, phase, phase_number,
                status, context_hash, context_summary,
                started_at, worker_count
            ) VALUES (?, ?, ?, ?, 'running', ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (
                id,
                conversation_id,
                phase,
                phase_number,
                context_hash,
                kwargs.get("context_summary"),
                kwargs.get("worker_count", 0),
            ),
        )

    async def update_checkpoint(self, id: str, status: str, **kwargs) -> None:
        """Update checkpoint (delegates to writer)."""
        # Build UPDATE query with only validated column names
        # This prevents SQL injection by whitelisting allowed columns
        updates = ["status = ?"]
        params = [status]

        if "duration_ms" in kwargs:
            updates.append("duration_ms = ?")
            params.append(kwargs["duration_ms"])

        if "failures" in kwargs:
            updates.append("failures = ?")
            params.append(kwargs["failures"])

        if "error" in kwargs:
            updates.append("error = ?")
            params.append(kwargs["error"])

        if status in ("completed", "failed"):
            updates.append("finished_at = CURRENT_TIMESTAMP")

        params.append(id)

        # Safe: updates list contains only validated column names from above
        await self.writer.write(
            f"UPDATE phase_checkpoints SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )

    def get_checkpoint(self, id: str) -> dict[str, Any] | None:
        """Get checkpoint by ID (delegates to reader)."""
        return self.reader.get_checkpoint(id)

    def list_checkpoints(self, conversation_id: str) -> list[dict[str, Any]]:
        """List checkpoints (delegates to reader)."""
        return self.reader.list_checkpoints(conversation_id)

    # =========================================================================
    # Subagent Call Management (delegated)
    # =========================================================================

    async def upsert_subagent_call(
        self,
        call_key: str,
        conversation_id: str,
        phase: str,
        agent_type: str,
        model_name: str,
        prompt_content: str,
        **kwargs,
    ) -> str:
        """Upsert subagent call (delegates to writer + blob_manager)."""
        # Store prompt as blob
        prompt_ref, _ = self.blob_manager.store(prompt_content, "prompt")

        # Generate UUID if not provided
        call_id = kwargs.get("id", str(uuid4()))

        # Store response as blob if provided
        response_ref = None
        if "response_content" in kwargs:
            response_ref, _ = self.blob_manager.store(kwargs["response_content"], "response")

        # Upsert (INSERT OR REPLACE)
        await self.writer.write(
            """
            INSERT OR REPLACE INTO subagent_calls (
                call_key, id, conversation_id, phase, agent_type,
                model_name, temperature, top_p, system_prompt, seed,
                provider_fingerprint, prompt_ref, response_ref,
                tokens_in_reserved, tokens_in_actual, tokens_out_actual, cost_usd,
                queued_at, started_at, finished_at,
                queue_wait_ms, provider_latency_ms, total_duration_ms,
                retry_of, retry_count, finish_reason, error,
                correlation_id, span_id
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                call_key,
                call_id,
                conversation_id,
                phase,
                agent_type,
                model_name,
                kwargs.get("temperature"),
                kwargs.get("top_p"),
                kwargs.get("system_prompt"),
                kwargs.get("seed"),
                kwargs.get("provider_fingerprint"),
                prompt_ref,
                response_ref,
                kwargs.get("tokens_in_reserved"),
                kwargs.get("tokens_in_actual"),
                kwargs.get("tokens_out_actual"),
                kwargs.get("cost_usd"),
                kwargs.get("started_at"),
                kwargs.get("finished_at"),
                kwargs.get("queue_wait_ms"),
                kwargs.get("provider_latency_ms"),
                kwargs.get("total_duration_ms"),
                kwargs.get("retry_of"),
                kwargs.get("retry_count"),
                kwargs.get("finish_reason"),
                kwargs.get("error"),
                kwargs.get("correlation_id"),
                kwargs.get("span_id"),
            ),
        )

        return call_id

    def get_call(self, id: str) -> dict[str, Any] | None:
        """Get subagent call by ID (delegates to reader)."""
        return self.reader.get_call(id)

    def query_subagent_calls(
        self, conversation_id: str, phase: str | None = None
    ) -> list[dict[str, Any]]:
        """Query subagent calls (delegates to reader)."""
        return self.reader.query_subagent_calls(conversation_id, phase)

    # =========================================================================
    # Blob Operations (delegated)
    # =========================================================================

    def store_blob(self, content: str, kind: str, **metadata) -> tuple[str, dict[str, Any]]:
        """Store blob (delegates to blob_manager)."""
        return self.blob_manager.store(content, kind, **metadata)

    def load_blob(self, ref: str) -> str:
        """Load blob (delegates to reader -> blob_manager)."""
        return self.reader.load_blob(ref)

    def load_blob_preview(self, ref: str) -> str:
        """Load blob preview (delegates to reader -> blob_manager)."""
        return self.reader.load_blob_preview(ref)

    # =========================================================================
    # Statistics (delegated)
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get statistics (delegates to reader)."""
        return self.reader.get_stats()

    def get_token_usage(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Get token usage (delegates to reader)."""
        return self.reader.get_token_usage(start_date, end_date)

    # =========================================================================
    # Schema Management (delegated)
    # =========================================================================

    def check_integrity(self) -> Any:
        """Check database integrity (delegates to migrator)."""
        return self.migrator.check_integrity()

    def get_schema_status(self) -> Any:
        """Get schema status (delegates to migrator)."""
        return self.migrator.get_schema_status()

    def validate_schema(self) -> Any:
        """Validate schema version (delegates to migrator)."""
        return self.migrator.validate_schema()

    # =========================================================================
    # Context Managers
    # =========================================================================

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()
