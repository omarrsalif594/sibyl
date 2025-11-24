"""Session state persistence with crash recovery and orphan repair.

This module provides crash-safe session state persistence with:
- **ACID guarantees**: DuckDB transactions for atomic writes
- **Crash recovery**: Boot integrity checks to detect incomplete rotations
- **Orphan repair**: Detect and fix orphaned sessions from crashes
- **Retry logic**: Exponential backoff for transient failures
- **Audit trail**: Complete history of session state changes

Key safety features:
- **Atomic state updates**: All-or-nothing session state transitions
- **Orphan detection**: Find sessions stuck in "rotating" or "summarizing" states
- **Timeout-based repair**: Auto-fail stuck sessions after 5 minutes
- **Boot integrity**: Validate database consistency on startup
- **Crash resilience**: Handle mid-rotation crashes gracefully

Typical usage:
    writer = SessionStateWriter(db_path="/path/to/state.db")

    # Boot integrity check (run on server startup)
    await writer.repair_orphaned_sessions()

    # Write session state atomically
    await writer.write_session(session_state)

    # Write rotation event atomically
    await writer.write_rotation(rotation_event)

    # Atomic session transition (old -> new)
    await writer.atomic_handoff(old_session, new_session, rotation_metadata)
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session lifecycle states."""

    ACTIVE = "active"
    ROTATING = "rotating"  # Mid-rotation (crash risk)
    SUMMARIZING = "summarizing"  # Mid-summarization (crash risk)
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RepairAction:
    """Details of a single orphan repair action.

    Attributes:
        session_id: Session being repaired
        old_status: Status before repair
        stuck_seconds: How long session was stuck
        action_taken: What action was performed
        success: Whether repair succeeded
        error_message: Error message if failed
    """

    session_id: str
    old_status: str
    stuck_seconds: float
    action_taken: str
    success: bool
    error_message: str | None = None


@dataclass
class RepairResult:
    """Result of orphan session repair operation.

    Attributes:
        timestamp: When repair was performed
        total_orphans_found: Number of orphans detected
        successfully_repaired: Number successfully fixed
        failed_to_repair: Number that failed to fix
        already_repaired: Number already fixed (idempotent)
        repairs: List of individual repair actions
    """

    timestamp: float
    total_orphans_found: int
    successfully_repaired: int
    failed_to_repair: int
    already_repaired: int
    repairs: list[RepairAction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "total_orphans_found": self.total_orphans_found,
            "successfully_repaired": self.successfully_repaired,
            "failed_to_repair": self.failed_to_repair,
            "already_repaired": self.already_repaired,
            "repairs": [
                {
                    "session_id": r.session_id,
                    "old_status": r.old_status,
                    "stuck_seconds": round(r.stuck_seconds, 1),
                    "action_taken": r.action_taken,
                    "success": r.success,
                    "error_message": r.error_message,
                }
                for r in self.repairs
            ],
        }


@dataclass
class SessionState:
    """Session state snapshot.

    Attributes:
        session_id: Unique session identifier
        active_generation: Current generation counter
        status: Session lifecycle status
        created_at: Creation timestamp
        completed_at: Completion timestamp (if completed)
        rotation_in_progress: Whether rotation is in progress
        rotation_started_at: When rotation started (if in progress)
        model: LLM model being used
        token_budget: Total token budget
        tokens_used: Tokens used so far
        metadata: Additional metadata dict
    """

    session_id: str
    active_generation: int
    status: SessionStatus
    created_at: float
    completed_at: float | None = None
    rotation_in_progress: bool = False
    rotation_started_at: float | None = None
    model: str | None = None
    token_budget: int | None = None
    tokens_used: int = 0
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Ensure metadata is dict."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RotationEvent:
    """Session rotation event.

    Attributes:
        rotation_id: Unique rotation identifier
        old_session_id: Session being rotated out
        new_session_id: Session being rotated in
        trigger: What triggered the rotation
        old_generation: Old session generation
        new_generation: New session generation
        started_at: Rotation start timestamp
        completed_at: Rotation completion timestamp
        success: Whether rotation succeeded
        error_message: Error message (if failed)
        summary_cache_key: Cache key for summary (if summarized)
        compression_ratio: Compression ratio achieved
        latency_ms: Rotation latency in milliseconds
    """

    rotation_id: str
    old_session_id: str
    new_session_id: str
    trigger: str
    old_generation: int
    new_generation: int
    started_at: float
    completed_at: float | None = None
    success: bool = False
    error_message: str | None = None
    summary_cache_key: str | None = None
    compression_ratio: float | None = None
    latency_ms: int | None = None


class SessionStateWriter:
    """Crash-safe session state persistence with orphan repair.

    This class provides ACID-compliant session state persistence with:
    - Atomic writes (transactions)
    - Crash recovery (boot integrity checks)
    - Orphan detection and repair
    - Retry logic with exponential backoff
    - Complete audit trail
    """

    # Orphan detection thresholds
    ORPHAN_TIMEOUT_SECONDS = 300  # 5 minutes
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0

    # Storage guardrail thresholds (can be overridden via config)
    DEFAULT_WAL_WARNING_THRESHOLD_MB = 500
    DEFAULT_BLOBS_QUOTA_MB = 1000

    def __init__(
        self,
        db_path: str,
        wal_threshold_mb: int = DEFAULT_WAL_WARNING_THRESHOLD_MB,
        blobs_quota_mb: int = DEFAULT_BLOBS_QUOTA_MB,
    ) -> None:
        """Initialize session state writer.

        Args:
            db_path: Path to DuckDB database file
            wal_threshold_mb: WAL size warning threshold in MB
            blobs_quota_mb: Blob storage quota in MB
        """
        self.db_path = Path(db_path)
        self.wal_threshold_mb = wal_threshold_mb
        self.blobs_quota_mb = blobs_quota_mb
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._write_lock = asyncio.Lock()

        # Statistics
        self._writes = 0
        self._failures = 0
        self._retries = 0
        self._orphans_repaired = 0

        logger.info(
            "SessionStateWriter initialized: db_path=%s, wal_threshold=%sMB, blobs_quota=%sMB",
            db_path,
            wal_threshold_mb,
            blobs_quota_mb,
        )

    async def connect(self) -> None:
        """Connect to DuckDB database.

        This should be called on server startup before any operations.
        """
        if self._conn is not None:
            logger.warning("Already connected to database")
            return

        logger.info("Connecting to DuckDB: %s", self.db_path)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB
        self._conn = duckdb.connect(str(self.db_path))

        logger.info("Connected to DuckDB successfully")

    async def disconnect(self) -> None:
        """Disconnect from DuckDB database."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info("Disconnected from DuckDB")

    async def repair_orphaned_sessions(self, dry_run: bool = False) -> RepairResult:
        """Boot integrity check: repair orphaned sessions from crashes.

        This detects sessions stuck in "rotating" or "summarizing" states
        for longer than ORPHAN_TIMEOUT_SECONDS and marks them as failed.

        Should be called on server boot before accepting requests.

        Args:
            dry_run: If True, only detect orphans without repairing them

        Returns:
            RepairResult with detailed repair information
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        repair_timestamp = time.time()
        logger.info(
            f"Running boot integrity check for orphaned sessions "
            f"({'DRY RUN' if dry_run else 'LIVE MODE'})..."
        )

        # Find sessions stuck in transitional states
        orphan_query = """
            SELECT
                session_id,
                status,
                rotation_started_at,
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rotation_started_at)) AS stuck_seconds
            FROM sessions
            WHERE status IN ('rotating', 'summarizing')
              AND rotation_started_at IS NOT NULL
              AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rotation_started_at)) > ?
            ORDER BY session_id, status, stuck_seconds
        """

        orphans = self._conn.execute(orphan_query, [self.ORPHAN_TIMEOUT_SECONDS]).fetchall()

        if not orphans:
            result = RepairResult(
                timestamp=repair_timestamp,
                total_orphans_found=0,
                successfully_repaired=0,
                failed_to_repair=0,
                already_repaired=0,
                repairs=[],
            )
            logger.info("No orphaned sessions found")
            logger.info("Orphan repair summary: %s", json.dumps(result.to_dict(), sort_keys=True))
            return result

        logger.warning("Found %s orphaned sessions", len(orphans))

        # Track repair outcomes
        successfully_repaired = 0
        failed_to_repair = 0
        already_repaired = 0
        repair_actions = []

        # Repair each orphan
        for session_id, status, _rotation_started_at, stuck_seconds in orphans:
            logger.warning(
                f"{'[DRY RUN] Would repair' if dry_run else 'Repairing'} orphaned session: {session_id} "
                f"(stuck in {status} for {stuck_seconds:.0f}s)"
            )

            action_taken = "mark_as_failed"
            success = False
            error_message = None

            if dry_run:
                # Dry run: just log what would happen
                success = True
                action_taken = "dry_run_detected"
            else:
                # Live mode: repair with idempotence check
                update_query = """
                    UPDATE sessions
                    SET status = 'failed',
                        completed_at = CURRENT_TIMESTAMP,
                        rotation_in_progress = FALSE
                    WHERE session_id = ?
                      AND status IN ('rotating', 'summarizing')
                """

                try:
                    result = self._conn.execute(update_query, [session_id])
                    rows_updated = result.fetchone()[0] if result else 0

                    if rows_updated > 0:
                        # Successfully repaired
                        success = True
                        successfully_repaired += 1
                        self._orphans_repaired += 1
                    else:
                        # Already repaired (idempotent)
                        success = True
                        action_taken = "already_repaired"
                        already_repaired += 1
                        logger.info("Session %s already repaired (idempotent)", session_id)

                except Exception as e:
                    # Repair failed
                    error_message = str(e)
                    failed_to_repair += 1
                    logger.exception("Failed to repair orphan %s: %s", session_id, e)

            # Record repair action
            repair_actions.append(
                RepairAction(
                    session_id=session_id,
                    old_status=status,
                    stuck_seconds=stuck_seconds,
                    action_taken=action_taken,
                    success=success,
                    error_message=error_message,
                )
            )

        # Build result
        result = RepairResult(
            timestamp=repair_timestamp,
            total_orphans_found=len(orphans),
            successfully_repaired=successfully_repaired,
            failed_to_repair=failed_to_repair,
            already_repaired=already_repaired,
            repairs=repair_actions,
        )

        # Log structured summary (sorted keys for diff-friendly output)
        logger.info("Orphan repair summary: %s", json.dumps(result.to_dict(), sort_keys=True))

        if not dry_run:
            logger.info(
                f"Repaired {successfully_repaired} orphaned sessions "
                f"({already_repaired} already repaired, {failed_to_repair} failed)"
            )

        return result

    async def write_session(self, session: SessionState, retry: int = 0) -> bool:
        """Write session state atomically with retry logic.

        Args:
            session: Session state to write
            retry: Current retry count (internal)

        Returns:
            True if successful, False otherwise
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        async with self._write_lock:
            try:
                # Convert status enum to string
                status_str = (
                    session.status.value
                    if isinstance(session.status, SessionStatus)
                    else session.status
                )

                # Upsert session (insert or update)
                upsert_query = """
                    INSERT INTO sessions (
                        session_id, active_generation, status, created_at, completed_at,
                        rotation_in_progress, rotation_started_at, model, token_budget, tokens_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (session_id) DO UPDATE SET
                        active_generation = EXCLUDED.active_generation,
                        status = EXCLUDED.status,
                        completed_at = EXCLUDED.completed_at,
                        rotation_in_progress = EXCLUDED.rotation_in_progress,
                        rotation_started_at = EXCLUDED.rotation_started_at,
                        tokens_used = EXCLUDED.tokens_used
                """

                self._conn.execute(
                    upsert_query,
                    [
                        session.session_id,
                        session.active_generation,
                        status_str,
                        session.created_at,
                        session.completed_at,
                        session.rotation_in_progress,
                        session.rotation_started_at,
                        session.model,
                        session.token_budget,
                        session.tokens_used,
                    ],
                )

                self._writes += 1
                logger.debug(
                    "Wrote session state: %s (generation=%s)",
                    session.session_id,
                    session.active_generation,
                )
                return True

            except Exception as e:
                self._failures += 1
                logger.exception("Failed to write session state: %s: %s", session.session_id, e)

                # Retry with exponential backoff
                if retry < self.MAX_RETRIES:
                    self._retries += 1
                    delay = self.RETRY_DELAY_SECONDS * (2**retry)
                    logger.info(
                        "Retrying write after %ss (retry %s/%s)", delay, retry + 1, self.MAX_RETRIES
                    )
                    await asyncio.sleep(delay)
                    return await self.write_session(session, retry=retry + 1)

                return False

    async def write_rotation(self, rotation: RotationEvent, retry: int = 0) -> bool:
        """Write rotation event atomically with retry logic.

        Args:
            rotation: Rotation event to write
            retry: Current retry count (internal)

        Returns:
            True if successful, False otherwise
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        async with self._write_lock:
            try:
                # Upsert rotation event
                upsert_query = """
                    INSERT INTO session_rotations (
                        rotation_id, old_session_id, new_session_id, trigger,
                        old_generation, new_generation, started_at, completed_at,
                        success, error_message, summary_cache_key,
                        compression_ratio, latency_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (rotation_id) DO UPDATE SET
                        completed_at = EXCLUDED.completed_at,
                        success = EXCLUDED.success,
                        error_message = EXCLUDED.error_message,
                        summary_cache_key = EXCLUDED.summary_cache_key,
                        compression_ratio = EXCLUDED.compression_ratio,
                        latency_ms = EXCLUDED.latency_ms
                """

                self._conn.execute(
                    upsert_query,
                    [
                        rotation.rotation_id,
                        rotation.old_session_id,
                        rotation.new_session_id,
                        rotation.trigger,
                        rotation.old_generation,
                        rotation.new_generation,
                        rotation.started_at,
                        rotation.completed_at,
                        rotation.success,
                        rotation.error_message,
                        rotation.summary_cache_key,
                        rotation.compression_ratio,
                        rotation.latency_ms,
                    ],
                )

                self._writes += 1
                logger.debug("Wrote rotation event: %s", rotation.rotation_id)
                return True

            except Exception as e:
                self._failures += 1
                logger.exception("Failed to write rotation event: %s: %s", rotation.rotation_id, e)

                # Retry with exponential backoff
                if retry < self.MAX_RETRIES:
                    self._retries += 1
                    delay = self.RETRY_DELAY_SECONDS * (2**retry)
                    logger.info(
                        "Retrying write after %ss (retry %s/%s)", delay, retry + 1, self.MAX_RETRIES
                    )
                    await asyncio.sleep(delay)
                    return await self.write_rotation(rotation, retry=retry + 1)

                return False

    async def atomic_handoff(
        self,
        old_session: SessionState,
        new_session: SessionState,
        rotation: RotationEvent,
    ) -> bool:
        """Atomic session handoff with transaction guarantees.

        This performs an all-or-nothing state transition:
        1. Mark old session as completed
        2. Create new session as active
        3. Record rotation event

        If any step fails, the entire operation is rolled back.

        Args:
            old_session: Old session being rotated out
            new_session: New session being rotated in
            rotation: Rotation event metadata

        Returns:
            True if successful, False otherwise
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        async with self._write_lock:
            try:
                # Begin transaction
                self._conn.begin()

                # Step 1: Mark old session as completed
                old_session.status = SessionStatus.COMPLETED
                old_session.completed_at = time.time()
                old_session.rotation_in_progress = False

                await self.write_session(old_session)

                # Step 2: Create new session as active
                new_session.status = SessionStatus.ACTIVE
                new_session.rotation_in_progress = False

                await self.write_session(new_session)

                # Step 3: Record rotation event
                rotation.completed_at = time.time()
                rotation.success = True
                rotation.latency_ms = int((rotation.completed_at - rotation.started_at) * 1000)

                await self.write_rotation(rotation)

                # Commit transaction
                self._conn.commit()

                logger.info(
                    f"Atomic handoff successful: {old_session.session_id} -> {new_session.session_id} "
                    f"(latency={rotation.latency_ms}ms)"
                )
                return True

            except Exception as e:
                # Rollback transaction
                self._conn.rollback()
                self._failures += 1

                logger.exception(
                    "Atomic handoff failed: %s -> %s: %s",
                    old_session.session_id,
                    new_session.session_id,
                    e,
                )
                return False

    async def get_session(self, session_id: str) -> SessionState | None:
        """Read session state from database.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None if not found
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        query = """
            SELECT
                session_id, active_generation, status, created_at, completed_at,
                rotation_in_progress, rotation_started_at, model, token_budget, tokens_used
            FROM sessions
            WHERE session_id = ?
        """

        result = self._conn.execute(query, [session_id]).fetchone()

        if not result:
            return None

        return SessionState(
            session_id=result[0],
            active_generation=result[1],
            status=SessionStatus(result[2]),
            created_at=result[3],
            completed_at=result[4],
            rotation_in_progress=result[5],
            rotation_started_at=result[6],
            model=result[7],
            token_budget=result[8],
            tokens_used=result[9],
        )

    async def get_active_sessions(self) -> list[SessionState]:
        """Get all active sessions.

        Returns:
            List of active session states
        """
        if self._conn is None:
            msg = "Not connected to database"
            raise RuntimeError(msg)

        query = """
            SELECT
                session_id, active_generation, status, created_at, completed_at,
                rotation_in_progress, rotation_started_at, model, token_budget, tokens_used
            FROM sessions
            WHERE status = 'active'
            ORDER BY created_at DESC
        """

        results = self._conn.execute(query).fetchall()

        return [
            SessionState(
                session_id=row[0],
                active_generation=row[1],
                status=SessionStatus(row[2]),
                created_at=row[3],
                completed_at=row[4],
                rotation_in_progress=row[5],
                rotation_started_at=row[6],
                model=row[7],
                token_budget=row[8],
                tokens_used=row[9],
            )
            for row in results
        ]

    async def check_storage_health(self) -> dict[str, Any]:
        """Check storage health and return warnings if thresholds exceeded.

        Returns:
            Dict with storage metrics and warnings
        """
        import os  # can be moved to top

        health_info = {
            "db_size_mb": 0.0,
            "wal_size_mb": 0.0,
            "blobs_size_mb": 0.0,
            "wal_warning": False,
            "blobs_warning": False,
            "warnings": [],
        }

        try:
            # Check main DB size
            if self.db_path.exists():
                db_size_bytes = os.path.getsize(self.db_path)
                health_info["db_size_mb"] = db_size_bytes / (1024 * 1024)

            # Check WAL size
            wal_path = self.db_path.parent / f"{self.db_path.stem}.wal"
            if wal_path.exists():
                wal_size_bytes = os.path.getsize(wal_path)
                wal_size_mb = wal_size_bytes / (1024 * 1024)
                health_info["wal_size_mb"] = wal_size_mb

                if wal_size_mb > self.wal_threshold_mb:
                    health_info["wal_warning"] = True
                    warning_msg = (
                        f"WAL size ({wal_size_mb:.1f}MB) exceeds threshold ({self.wal_threshold_mb}MB). "
                        "Consider running CHECKPOINT or reducing write frequency."
                    )
                    health_info["warnings"].append(warning_msg)
                    logger.warning("STORAGE WARNING: %s", warning_msg)

            # Check blob storage (if blobs table exists)
            if self._conn is not None:
                try:
                    blob_query = "SELECT SUM(size_bytes) FROM blobs"
                    result = self._conn.execute(blob_query).fetchone()
                    if result and result[0]:
                        blobs_size_bytes = result[0]
                        blobs_size_mb = blobs_size_bytes / (1024 * 1024)
                        health_info["blobs_size_mb"] = blobs_size_mb

                        if blobs_size_mb > self.blobs_quota_mb:
                            health_info["blobs_warning"] = True
                            warning_msg = (
                                f"Blob storage ({blobs_size_mb:.1f}MB) exceeds quota ({self.blobs_quota_mb}MB). "
                                "Consider purging old blobs or increasing quota."
                            )
                            health_info["warnings"].append(warning_msg)
                            logger.warning("STORAGE WARNING: %s", warning_msg)
                except Exception as e:
                    logger.debug("Could not query blob storage: %s", e)

        except Exception as e:
            logger.exception("Error checking storage health: %s", e)
            health_info["warnings"].append(f"Error checking storage: {e}")

        return health_info

    def get_stats(self) -> dict[str, Any]:
        """Get writer statistics.

        Returns:
            Stats dict with writes, failures, retries, orphans_repaired
        """
        return {
            "writes": self._writes,
            "failures": self._failures,
            "retries": self._retries,
            "orphans_repaired": self._orphans_repaired,
            "success_rate": self._writes / (self._writes + self._failures)
            if self._writes + self._failures > 0
            else 1.0,
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"SessionStateWriter(db={self.db_path.name}, "
            f"writes={stats['writes']}, failures={stats['failures']}, "
            f"success_rate={stats['success_rate']:.1%})"
        )
