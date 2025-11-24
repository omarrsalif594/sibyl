"""Session rotation manager with concurrency controls and state machine.

This module implements the core session rotation logic with:
- Per-session rotate_mutex to prevent concurrent rotations
- Generation counter for atomic session swaps (compare-and-swap)
- State machine: ACTIVE → SUMMARIZING → ROTATING → new ACTIVE
- Operation draining: wait for in-flight operations to complete
- Thread-safe with asyncio.Lock

Key guarantees:
- **Single rotation per threshold**: Only one rotation proceeds even if multiple
  tool completions cross 70% threshold
- **Atomic swap**: Generation counter ensures no tool calls bind to wrong session
- **Operation boundary**: Rotations only occur between tool calls, never mid-operation
- **No double-rotations**: rotate_mutex prevents concurrent rotation attempts

Typical usage:
    manager = SessionRotationManager(config)

    # Create session
    session_state = await manager.create_session(conversation_id="conv_123")

    # Check if rotation needed after tool call
    if await manager.should_rotate(session_state.session_id):
        # Trigger rotation
        new_session = await manager.rotate_session(session_state.session_id)
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum

from sibyl.core.server.config import RotationConfig

# Import SessionManagementTechnique for configuration
from sibyl.techniques.workflow_orchestration.session_management import SessionManagementTechnique

logger = logging.getLogger(__name__)

# Load default configuration from technique (module-level singleton)
_technique = SessionManagementTechnique()
_technique_config = _technique.load_config(_technique._config_path)
_rotation_config = (
    _technique_config.get("rotation_based", {}).get("rotation_manager", {}).get("rotation", {})
)


class SessionStatus(str, Enum):
    """Session status enum matching DuckDB schema."""

    ACTIVE = "active"
    SUMMARIZING = "summarizing"
    ROTATING = "rotating"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class RotationError(Exception):
    """Base exception for rotation errors."""


class RotationInProgressError(RotationError):
    """Raised when rotation already in progress for this session."""


class RotationTimeoutError(RotationError):
    """Raised when rotation exceeds timeout."""


class RotationAdmissionError(RotationError):
    """Raised when tool call is rejected during rotation."""


@dataclass
class RotationAdmissionResult:
    """Result of admission control check for tool operation.

    Attributes:
        allowed: Whether operation is allowed to proceed
        reason: Human-readable reason if rejected
        error_type: Machine-readable error type for metrics
        session_id: Session ID for correlation
        requested_generation: Generation requested by tool
        current_generation: Current session generation
    """

    allowed: bool
    reason: str | None = None
    error_type: str | None = None
    session_id: str | None = None
    requested_generation: int | None = None
    current_generation: int | None = None


@dataclass
class SessionState:
    """In-memory session state.

    This is the authoritative state for active sessions. It's synchronized
    with DuckDB but lives in memory for fast access.

    Attributes:
        session_id: Unique session identifier
        conversation_id: Parent conversation identifier
        session_number: Sequential number within conversation (1, 2, 3...)
        active_generation: Monotonic counter for atomic swaps
        status: Current session status
        tokens_budget: Maximum tokens for this session
        tokens_spent: Cumulative tokens used
        summarize_threshold_pct: Threshold for summarization
        rotate_threshold_pct: Threshold for rotation
        model_name: LLM model for this session
        created_at: Session creation timestamp
        parent_session_id: Previous session ID (if rotated)
        rotation_in_progress: Flag to prevent concurrent rotations
    """

    session_id: str
    conversation_id: str
    session_number: int
    active_generation: int
    status: SessionStatus
    tokens_budget: int
    tokens_spent: int
    summarize_threshold_pct: float
    rotate_threshold_pct: float
    model_name: str
    created_at: float
    parent_session_id: str | None = None
    rotation_in_progress: bool = False

    def get_utilization_pct(self) -> float:
        """Get current utilization percentage."""
        return (self.tokens_spent / self.tokens_budget) * 100.0


class SessionRotationManager:
    """Manage session rotation with concurrency controls.

    This class implements the rotation state machine and ensures:
    - Only one rotation per session at a time (rotate_mutex)
    - Atomic session swaps (generation counter)
    - Operation boundaries (drain in-flight operations)
    - Crash safety (persisted to DuckDB)

    Thread-safe with per-session locks.
    """

    def __init__(self, config: RotationConfig) -> None:
        """Initialize session rotation manager.

        Args:
            config: Rotation configuration
        """
        self.config = config

        # In-memory session registry
        self._sessions: dict[str, SessionState] = {}

        # Per-session rotation locks (prevent concurrent rotations)
        self._rotate_locks: dict[str, asyncio.Lock] = {}

        # Global registry lock (for creating/removing sessions)
        self._registry_lock = asyncio.Lock()

        # In-flight operation tracking (for draining)
        self._in_flight_operations: dict[str, int] = {}  # session_id -> count
        self._operation_locks: dict[str, asyncio.Lock] = {}

        logger.info("SessionRotationManager initialized")

    async def create_session(
        self,
        conversation_id: str,
        tokens_budget: int,
        model_name: str,
        parent_session_id: str | None = None,
        summarize_threshold_pct: float | None = None,
        rotate_threshold_pct: float | None = None,
    ) -> SessionState:
        """Create a new session.

        Args:
            conversation_id: Conversation identifier
            tokens_budget: Maximum tokens for this session
            model_name: LLM model name
            parent_session_id: Previous session ID (if rotated)
            summarize_threshold_pct: Optional override for summarize threshold
            rotate_threshold_pct: Optional override for rotate threshold

        Returns:
            SessionState for new session
        """
        async with self._registry_lock:
            session_id = f"sess_{conversation_id}_{str(uuid.uuid4())[:8]}"

            # Determine session number
            session_number = 1
            if parent_session_id:
                parent = self._sessions.get(parent_session_id)
                if parent:
                    session_number = parent.session_number + 1

            # Create session state
            session = SessionState(
                session_id=session_id,
                conversation_id=conversation_id,
                session_number=session_number,
                active_generation=1,  # Start at generation 1
                status=SessionStatus.ACTIVE,
                tokens_budget=tokens_budget,
                tokens_spent=0,
                summarize_threshold_pct=summarize_threshold_pct
                or self.config.summarize_threshold_pct,
                rotate_threshold_pct=rotate_threshold_pct or self.config.rotate_threshold_pct,
                model_name=model_name,
                created_at=time.time(),
                parent_session_id=parent_session_id,
                rotation_in_progress=False,
            )

            # Register session
            self._sessions[session_id] = session
            self._rotate_locks[session_id] = asyncio.Lock()
            self._in_flight_operations[session_id] = 0
            self._operation_locks[session_id] = asyncio.Lock()

            logger.info(
                f"Session created: {session_id} (conversation={conversation_id}, "
                f"number={session_number}, budget={tokens_budget}, model={model_name})"
            )

            return session

    async def get_session(self, session_id: str) -> SessionState | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None if not found
        """
        return self._sessions.get(session_id)

    async def should_rotate(self, session_id: str) -> bool:
        """Check if session should rotate based on utilization.

        Args:
            session_id: Session identifier

        Returns:
            True if rotation should be triggered
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Check if already rotating
        if session.rotation_in_progress or session.status != SessionStatus.ACTIVE:
            return False

        # Check threshold
        utilization = session.get_utilization_pct()
        return utilization >= session.rotate_threshold_pct

    async def rotate_session(
        self,
        session_id: str,
        trigger: str = "token_threshold",
    ) -> SessionState:
        """Rotate session to new session with compressed context.

        This is the main rotation workflow. It:
        1. Acquires rotate_mutex (prevents concurrent rotations)
        2. Transitions to ROTATING state
        3. Drains in-flight operations (wait for completion)
        4. Creates new session with incremented generation
        5. Returns new session

        Note: Context summarization and state persistence are handled by
        SessionHandoffOrchestrator (called by the caller after this returns).

        Args:
            session_id: Session to rotate
            trigger: Rotation trigger ("token_threshold", "manual", "error", etc.)

        Returns:
            New SessionState

        Raises:
            RotationInProgressError: If rotation already in progress
            RotationTimeoutError: If operation draining times out
            RotationError: If session not found or other error
        """
        # Get rotate lock for this session
        rotate_lock = self._rotate_locks.get(session_id)
        if not rotate_lock:
            msg = f"Session not found: {session_id}"
            raise RotationError(msg)

        # Try to acquire lock (non-blocking to detect concurrent attempts)
        if rotate_lock.locked():
            logger.warning("[%s] Rotation already in progress, skipping", session_id)
            msg = f"Rotation already in progress for {session_id}"
            raise RotationInProgressError(msg)

        async with rotate_lock:
            # Double-check session still exists
            old_session = self._sessions.get(session_id)
            if not old_session:
                msg = f"Session not found: {session_id}"
                raise RotationError(msg)

            # Check if already rotating (race condition check)
            if old_session.rotation_in_progress:
                logger.warning(
                    "[%s] Rotation flag already set (race condition), aborting", session_id
                )
                msg = f"Rotation already in progress for {session_id}"
                raise RotationInProgressError(msg)

            # Mark rotation in progress (compare-and-swap style)
            old_session.rotation_in_progress = True
            old_session.status = SessionStatus.ROTATING

            logger.info(
                f"[{session_id}] Rotation started (trigger={trigger}, "
                f"utilization={old_session.get_utilization_pct():.1f}%, "
                f"tokens={old_session.tokens_spent}/{old_session.tokens_budget})"
            )

            rotation_start = time.time()

            try:
                # Step 1: Drain in-flight operations
                # Use technique config for rotation timeout, fallback to instance config
                rotation_timeout = _rotation_config.get(
                    "rotation_timeout_seconds", self.config.rotation_timeout_seconds
                )
                await self._drain_operations(session_id, timeout=rotation_timeout)

                # Step 2: Create new session
                new_session = await self.create_session(
                    conversation_id=old_session.conversation_id,
                    tokens_budget=old_session.tokens_budget,
                    model_name=old_session.model_name,
                    parent_session_id=session_id,
                    summarize_threshold_pct=old_session.summarize_threshold_pct,
                    rotate_threshold_pct=old_session.rotate_threshold_pct,
                )

                # Step 3: Atomic swap - increment generation
                # This ensures any tool calls bound to old generation are rejected
                new_session.active_generation = old_session.active_generation + 1

                # Step 4: Mark old session as completed
                old_session.status = SessionStatus.COMPLETED
                old_session.rotation_in_progress = False

                rotation_duration = (time.time() - rotation_start) * 1000  # ms

                logger.info(
                    f"[{session_id}] Rotation completed in {rotation_duration:.0f}ms: "
                    f"{session_id} (gen {old_session.active_generation}) → "
                    f"{new_session.session_id} (gen {new_session.active_generation})"
                )

                return new_session

            except Exception as e:
                # Rollback on failure
                old_session.rotation_in_progress = False
                old_session.status = SessionStatus.FAILED

                logger.exception("[%s] Rotation failed: %s", session_id, e)
                msg = f"Rotation failed for {session_id}: {e}"
                raise RotationError(msg)

    async def _drain_operations(self, session_id: str, timeout: int) -> None:
        """Wait for in-flight operations to complete.

        This implements the operation boundary guarantee: rotations only
        occur between tool calls, never mid-operation.

        Args:
            session_id: Session identifier
            timeout: Maximum time to wait (seconds)

        Raises:
            RotationTimeoutError: If operations don't drain within timeout
        """
        start_time = time.time()
        operation_lock = self._operation_locks.get(session_id)

        if not operation_lock:
            return  # No operations tracked

        # Wait for in-flight count to reach 0
        while self._in_flight_operations.get(session_id, 0) > 0:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                count = self._in_flight_operations.get(session_id, 0)
                msg = (
                    f"Operation draining timed out after {timeout}s "
                    f"({count} operations still in flight)"
                )
                raise RotationTimeoutError(msg)

            # Log every N seconds (from technique config, default 5)
            log_interval = _rotation_config.get("status_log_interval_seconds", 5)
            if int(elapsed) % log_interval == 0 and elapsed > 0:
                count = self._in_flight_operations.get(session_id, 0)
                logger.info(
                    f"[{session_id}] Waiting for {count} operations to complete "
                    f"({elapsed:.1f}s elapsed)..."
                )

            # Poll interval from technique config (default 100ms)
            poll_interval_ms = _rotation_config.get("operation_poll_ms", 100)
            await asyncio.sleep(poll_interval_ms / 1000.0)

        drain_time = (time.time() - start_time) * 1000
        logger.debug("[%s] Operations drained in %sms", session_id, drain_time)

    async def begin_operation(
        self, session_id: str, active_generation: int
    ) -> RotationAdmissionResult:
        """Mark start of tool operation (for operation boundary tracking).

        This should be called at the beginning of every tool execution.
        It checks that the generation matches and increments the in-flight counter.

        Args:
            session_id: Session identifier
            active_generation: Generation at tool call entry

        Returns:
            RotationAdmissionResult with admission decision and metadata
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("[%s] Session not found. Rejecting operation.", session_id)
            return RotationAdmissionResult(
                allowed=False,
                reason=f"Session {session_id} not found",
                error_type="session_not_found",
                session_id=session_id,
                requested_generation=active_generation,
                current_generation=None,
            )

        # Check if rotation in progress
        if session.status == SessionStatus.ROTATING:
            logger.warning("[%s] Rotation in progress. Rejecting operation.", session_id)
            return RotationAdmissionResult(
                allowed=False,
                reason=f"Rotation in progress for session {session_id}",
                error_type="rotation_in_progress",
                session_id=session_id,
                requested_generation=active_generation,
                current_generation=session.active_generation,
            )

        # Check generation match (operation boundary contract)
        if session.active_generation != active_generation:
            logger.warning(
                f"[{session_id}] Generation mismatch: tool bound to gen {active_generation}, "
                f"but current gen is {session.active_generation}. Rejecting operation."
            )
            return RotationAdmissionResult(
                allowed=False,
                reason=f"Generation mismatch: requested {active_generation}, current {session.active_generation}",
                error_type="generation_mismatch",
                session_id=session_id,
                requested_generation=active_generation,
                current_generation=session.active_generation,
            )

        # Increment in-flight counter
        operation_lock = self._operation_locks.get(session_id)
        if operation_lock:
            async with operation_lock:
                self._in_flight_operations[session_id] = (
                    self._in_flight_operations.get(session_id, 0) + 1
                )

        return RotationAdmissionResult(
            allowed=True,
            session_id=session_id,
            requested_generation=active_generation,
            current_generation=session.active_generation,
        )

    async def end_operation(self, session_id: str) -> None:
        """Mark end of tool operation (for operation boundary tracking).

        This should be called at the end of every tool execution.

        Args:
            session_id: Session identifier
        """
        operation_lock = self._operation_locks.get(session_id)
        if operation_lock:
            async with operation_lock:
                count = self._in_flight_operations.get(session_id, 0)
                if count > 0:
                    self._in_flight_operations[session_id] = count - 1

    async def update_tokens(self, session_id: str, tokens_used: int) -> None:
        """Update token count for session.

        Args:
            session_id: Session identifier
            tokens_used: Tokens used in this tool call
        """
        session = self._sessions.get(session_id)
        if session:
            session.tokens_spent += tokens_used

    async def get_stats(self) -> dict:
        """Get rotation manager statistics.

        Returns:
            Dict with stats
        """
        async with self._registry_lock:
            total_sessions = len(self._sessions)
            active_sessions = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE
            )
            rotating_sessions = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.ROTATING
            )
            completed_sessions = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.COMPLETED
            )

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "rotating_sessions": rotating_sessions,
                "completed_sessions": completed_sessions,
                "rotation_config": {
                    "enabled": self.config.enabled,
                    "summarize_threshold_pct": self.config.summarize_threshold_pct,
                    "rotate_threshold_pct": self.config.rotate_threshold_pct,
                    "strategy": self.config.strategy,
                },
            }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionRotationManager(sessions={len(self._sessions)}, config={self.config.strategy})"
        )
