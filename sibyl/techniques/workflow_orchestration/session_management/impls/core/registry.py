"""Server-side session registry with atomic operations.

This module provides centralized session management:
- Session creation and lifecycle
- Budget tracker management
- Rotation coordination
- Background summarization triggers
- Atomic session operations

The registry is the integration point for all session components:
- RotationManager
- HandoffOrchestrator
- BackgroundSummarizer
- SessionBudgetTracker
- SummaryCache

Typical usage:
    registry = SessionRegistry(
        config=rotation_config,
        context_manager=context_mgr,
        state_writer=state_writer
    )

    # Create session
    session_id = await registry.create_session(
        conversation_id="conv_123",
        model_name="claude-sonnet-4-5"
    )

    # Session automatically tracks tokens, triggers rotation, etc.
"""

import asyncio
import logging
from typing import Any

from sibyl.core.server.config import RotationConfig

from .background_summarization import BackgroundSummarizer
from .budget_tracker import SessionBudgetTracker, compute_adaptive_thresholds
from .handoff_orchestrator import SessionHandoffOrchestrator
from .rotation_manager import SessionRotationManager, SessionState
from .summary_cache import SummaryCache, get_summary_cache

logger = logging.getLogger(__name__)


class SessionRegistry:
    """Central registry for session management with atomic operations.

    This class coordinates all session-related operations:
    - Session creation/deletion
    - Budget tracking
    - Rotation triggering
    - Background summarization
    - Cache management

    Thread-safe with asyncio.Lock.
    """

    def __init__(
        self,
        config: RotationConfig,
        context_manager: Any | None = None,
        state_writer: Any | None = None,
        summary_cache: SummaryCache | None = None,
    ) -> None:
        """Initialize session registry.

        Args:
            config: Rotation configuration
            context_manager: Context manager for LLM summarization
            state_writer: State writer for DuckDB persistence
            summary_cache: Summary cache (or use global default)
        """
        self.config = config
        self.context_manager = context_manager
        self.state_writer = state_writer

        # Core components
        self.rotation_manager = SessionRotationManager(config)
        self.summary_cache = summary_cache or get_summary_cache()
        self.summarizer = BackgroundSummarizer(
            context_manager=context_manager,
            summary_cache=self.summary_cache,
            config=config,
        )
        self.handoff_orchestrator = SessionHandoffOrchestrator(
            rotation_manager=self.rotation_manager,
            config=config,
            context_manager=context_manager,
            state_writer=state_writer,
        )

        # Budget trackers (one per session)
        self.budget_trackers: dict[str, SessionBudgetTracker] = {}

        # Registry lock (for atomic operations)
        self._registry_lock = asyncio.Lock()

        logger.info("SessionRegistry initialized")

    async def create_session(
        self,
        conversation_id: str,
        model_name: str = "claude-sonnet-4-5-20250929",
        tokens_budget: int | None = None,
        parent_session_id: str | None = None,
    ) -> str:
        """Create new session with budget tracker.

        Args:
            conversation_id: Conversation identifier
            model_name: LLM model name
            tokens_budget: Optional token budget (defaults to model context window)
            parent_session_id: Parent session if rotated

        Returns:
            Session ID
        """
        async with self._registry_lock:
            # Determine token budget (from model context window)
            if tokens_budget is None:
                # Get model context window
                from sibyl.core.workflow_orchestration.orchestration.budget import MODEL_LADDER

                model_tier = next((m for m in MODEL_LADDER if m.model == model_name), None)
                tokens_budget = model_tier.max_tokens if model_tier else 200000

            # Compute thresholds
            summarize_pct, rotate_pct = compute_adaptive_thresholds(
                model_name=model_name,
                default_summarize=self.config.summarize_threshold_pct,
                default_rotate=self.config.rotate_threshold_pct,
                user_overrides=self.config.user_overrides,
                model_adaptive=self.config.model_adaptive,
            )

            # Create session in rotation manager
            session = await self.rotation_manager.create_session(
                conversation_id=conversation_id,
                tokens_budget=tokens_budget,
                model_name=model_name,
                parent_session_id=parent_session_id,
                summarize_threshold_pct=summarize_pct,
                rotate_threshold_pct=rotate_pct,
            )

            # Create budget tracker
            budget_tracker = SessionBudgetTracker(
                session_id=session.session_id,
                tokens_budget=tokens_budget,
                summarize_threshold_pct=summarize_pct,
                rotate_threshold_pct=rotate_pct,
                model_name=model_name,
                model_adaptive=self.config.model_adaptive,
                user_overrides=self.config.user_overrides,
            )

            self.budget_trackers[session.session_id] = budget_tracker

            logger.info(
                f"Session created: {session.session_id} (conversation={conversation_id}, "
                f"budget={tokens_budget}, model={model_name})"
            )

            return session.session_id

    async def trigger_rotation(
        self,
        session_id: str,
        trigger: str = "token_threshold",
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """Trigger session rotation (called by tool decorator at 70% threshold).

        This coordinates the full rotation workflow:
        1. Rotate session (creates new session)
        2. Execute handoff (summarize + persist)
        3. Update budget tracker
        4. Invalidate cache

        Args:
            session_id: Session to rotate
            trigger: Rotation trigger
            context: Optional context for summarization

        Returns:
            New session ID or None if failed
        """
        if not self.config.enabled:
            logger.warning("Rotation disabled, skipping for session %s", session_id)
            return None

        try:
            # Get old session
            old_session = await self.rotation_manager.get_session(session_id)
            if not old_session:
                logger.error("Session %s not found", session_id)
                return None

            # Rotate session (creates new session, drains operations)
            new_session = await self.rotation_manager.rotate_session(
                session_id=session_id, trigger=trigger
            )

            # Execute handoff (summarize + persist)
            handoff_result = await self.handoff_orchestrator.execute_handoff(
                old_session=old_session,
                new_session=new_session,
                trigger=trigger,
                context=context,
            )

            if not handoff_result.success:
                logger.error("Handoff failed: %s", handoff_result.failure_reason)
                return None

            # Create budget tracker for new session
            budget_tracker = SessionBudgetTracker(
                session_id=new_session.session_id,
                tokens_budget=new_session.tokens_budget,
                summarize_threshold_pct=new_session.summarize_threshold_pct,
                rotate_threshold_pct=new_session.rotate_threshold_pct,
                model_name=new_session.model_name,
                model_adaptive=self.config.model_adaptive,
                user_overrides=self.config.user_overrides,
            )

            self.budget_trackers[new_session.session_id] = budget_tracker

            # Invalidate cache for old session
            await self.summary_cache.invalidate(session_id)

            logger.info(
                f"Rotation completed: {session_id} → {new_session.session_id} "
                f"(trigger={trigger}, strategy={handoff_result.summarization_strategy})"
            )

            return new_session.session_id

        except Exception as e:
            logger.exception("Rotation failed for session %s: %s", session_id, e)
            return None

    async def trigger_summarization(
        self,
        session_id: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Trigger background summarization (called at 60% threshold).

        Args:
            session_id: Session identifier
            context: Optional context to summarize
        """
        session = await self.rotation_manager.get_session(session_id)
        if not session:
            logger.warning("Session %s not found, skipping summarization", session_id)
            return

        budget_tracker = self.budget_trackers.get(session_id)
        if not budget_tracker:
            logger.warning("Budget tracker for %s not found", session_id)
            return

        # Trigger background summarization (non-blocking)
        await self.summarizer.trigger_summarization(
            session_id=session_id,
            context=context or {},
            turn_id=budget_tracker.turn_counter,
            summarize_threshold=session.summarize_threshold_pct,
            rotate_threshold=session.rotate_threshold_pct,
        )

    async def get_session(self, session_id: str) -> SessionState | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionState or None
        """
        return await self.rotation_manager.get_session(session_id)

    def get_budget_tracker(self, session_id: str) -> SessionBudgetTracker | None:
        """Get budget tracker for session.

        Args:
            session_id: Session identifier

        Returns:
            SessionBudgetTracker or None
        """
        return self.budget_trackers.get(session_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dict with comprehensive stats
        """
        rotation_stats = await self.rotation_manager.get_stats()
        summarizer_stats = self.summarizer.get_stats()
        cache_stats = self.summary_cache.get_stats()
        handoff_stats = self.handoff_orchestrator.get_stats()

        return {
            "sessions": {
                "total": rotation_stats["total_sessions"],
                "active": rotation_stats["active_sessions"],
                "rotating": rotation_stats["rotating_sessions"],
                "completed": rotation_stats["completed_sessions"],
            },
            "rotation": {
                "enabled": self.config.enabled,
                "summarize_threshold": self.config.summarize_threshold_pct,
                "rotate_threshold": self.config.rotate_threshold_pct,
                "strategy": self.config.strategy,
            },
            "summarization": summarizer_stats,
            "cache": cache_stats,
            "handoff": handoff_stats,
            "budget_trackers": len(self.budget_trackers),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionRegistry(sessions={len(self.budget_trackers)}, "
            f"rotation_enabled={self.config.enabled})"
        )


# Global registry instance (singleton)
_global_registry: SessionRegistry | None = None


def initialize_registry(
    config: RotationConfig,
    context_manager: Any | None = None,
    state_writer: Any | None = None,
) -> SessionRegistry:
    """Initialize global registry (called at server startup).

    Args:
        config: Rotation configuration
        context_manager: Context manager
        state_writer: State writer

    Returns:
        SessionRegistry instance
    """
    global _global_registry

    _global_registry = SessionRegistry(
        config=config, context_manager=context_manager, state_writer=state_writer
    )

    logger.info("Global session registry initialized")

    return _global_registry


def get_global_registry() -> SessionRegistry | None:
    """Get global registry instance.

    Returns:
        SessionRegistry or None if not initialized
    """
    return _global_registry
