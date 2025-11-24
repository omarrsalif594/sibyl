"""Typed session context for agent pool integration.

This module provides a typed SessionContext that bridges the gap between:
- Session management (SessionRegistry, BudgetTracker, RotationManager)
- Agent pools (AgentPool instances for fast/deep thinking)
- MCP tools (tool decorators with generation binding)

Key features:
- **Typed interface**: Strong typing for session metadata
- **Agent-friendly API**: Easy access to session state for agents
- **Budget tracking**: Automatic token accounting per operation
- **Rotation awareness**: Knows if rotation is pending or in progress
- **Context envelope**: Integrates with ContextEnvelope for summarization

Typical usage:
    # Create session context
    ctx = SessionContext.create(
        session_id="sess_abc",
        active_generation=1,
        model="claude-sonnet-4-5",
        token_budget=100000
    )

    # Pass to agent pool
    result = await agent_pool.spawn({
        "tool": "search_entities",
        "arguments": {"query": "related items"},
        "session_context": ctx,
    })

    # Update token usage
    await ctx.record_token_usage(
        prompt_tokens=1000,
        completion_tokens=500,
        operation="search_entities"
    )

    # Check if rotation needed
    if await ctx.should_rotate():
        await ctx.trigger_rotation()
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from sibyl.core.server.config import RotationConfig
from sibyl.techniques.workflow_orchestration.orchestration.impls.core.context import ContextEnvelope

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Typed session context for agent pool integration.

    This is the primary interface for agents to access session state
    and trigger session operations like rotation.

    Attributes:
        session_id: Unique session identifier
        active_generation: Current generation counter
        turn_id: Current turn number
        model: LLM model being used
        token_budget: Total token budget for session
        tokens_used: Tokens used so far
        metadata: Additional session metadata
        config: Rotation configuration
        budget_tracker: Optional budget tracker instance
        registry: Optional session registry instance
        context_envelope: Optional context envelope for summarization
    """

    # Core identifiers
    session_id: str
    active_generation: int
    turn_id: int

    # Token budget
    model: str
    token_budget: int
    tokens_used: int = 0

    # Session state
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Configuration (optional, for rotation integration)
    config: RotationConfig | None = None
    budget_tracker: Any | None = None  # SessionBudgetTracker
    registry: Any | None = None  # SessionRegistry
    context_envelope: ContextEnvelope | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        active_generation: int = 1,
        model: str = "claude-sonnet-4-5",
        token_budget: int = 100000,
        turn_id: int = 0,
        config: RotationConfig | None = None,
    ) -> "SessionContext":
        """Factory method to create a new session context.

        Args:
            session_id: Unique session identifier
            active_generation: Starting generation (default 1)
            model: LLM model (default claude-sonnet-4-5)
            token_budget: Total token budget (default 100k)
            turn_id: Starting turn ID (default 0)
            config: Optional rotation configuration

        Returns:
            SessionContext instance
        """
        return cls(
            session_id=session_id,
            active_generation=active_generation,
            turn_id=turn_id,
            model=model,
            token_budget=token_budget,
            config=config,
        )

    def get_utilization_pct(self) -> float:
        """Get current token utilization percentage.

        Returns:
            Percentage (0-100)
        """
        if self.token_budget == 0:
            return 0.0

        return (self.tokens_used / self.token_budget) * 100.0

    async def record_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        operation: str,
    ) -> None:
        """Record token usage for an operation.

        This updates the session's token usage and budget tracker (if configured).

        Args:
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            operation: Operation name (for tracking)
        """
        total_tokens = prompt_tokens + completion_tokens
        self.tokens_used += total_tokens

        logger.debug(
            f"Session {self.session_id}: Used {total_tokens} tokens "
            f"({operation}) - {self.get_utilization_pct():.1f}% utilization"
        )

        # Update budget tracker if configured
        if self.budget_tracker:
            await self.budget_tracker.record_turn(
                turn_id=self.turn_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                operation=operation,
            )

    async def should_rotate(self) -> bool:
        """Check if session should rotate based on token budget.

        Returns:
            True if rotation threshold exceeded, False otherwise
        """
        if not self.budget_tracker or not self.config:
            # No rotation configured, use simple threshold
            utilization = self.get_utilization_pct()
            return utilization >= 70.0  # Default threshold

        # Use budget tracker's threshold check
        from .budget_tracker import RotationAction

        action = await self.budget_tracker.check_threshold()
        return action == RotationAction.ROTATE_NOW

    async def should_summarize(self) -> bool:
        """Check if session should trigger background summarization.

        Returns:
            True if summarization threshold exceeded, False otherwise
        """
        if not self.budget_tracker or not self.config:
            # No rotation configured, use simple threshold
            utilization = self.get_utilization_pct()
            return utilization >= 60.0  # Default threshold

        # Use budget tracker's threshold check
        from .budget_tracker import RotationAction

        action = await self.budget_tracker.check_threshold()
        return action in [RotationAction.SUMMARIZE_CONTEXT, RotationAction.ROTATE_NOW]

    async def trigger_rotation(
        self, trigger: str = "token_threshold"
    ) -> Optional["SessionContext"]:
        """Trigger session rotation.

        This creates a new session and performs atomic handoff.

        Args:
            trigger: What triggered the rotation (for tracking)

        Returns:
            New SessionContext or None if rotation failed
        """
        if not self.registry:
            logger.warning("Session %s: Cannot rotate without registry", self.session_id)
            return None

        logger.info("Session %s: Triggering rotation (trigger=%s)", self.session_id, trigger)

        try:
            # Trigger rotation via registry
            new_session_state = await self.registry.trigger_rotation(
                session_id=self.session_id,
                trigger=trigger,
                context=self.context_envelope.to_dict() if self.context_envelope else {},
            )

            # Create new SessionContext from new session state
            new_ctx = SessionContext(
                session_id=new_session_state.session_id,
                active_generation=new_session_state.active_generation,
                turn_id=0,  # Reset turn for new session
                model=new_session_state.model or self.model,
                token_budget=new_session_state.token_budget or self.token_budget,
                tokens_used=new_session_state.tokens_used,
                created_at=new_session_state.created_at,
                config=self.config,
                registry=self.registry,
            )

            logger.info(
                f"Rotation complete: {self.session_id} -> {new_ctx.session_id} "
                f"(generation {self.active_generation} -> {new_ctx.active_generation})"
            )

            return new_ctx

        except Exception as e:
            logger.exception("Session %s: Rotation failed: %s", self.session_id, e)
            return None

    async def trigger_summarization(self) -> None:
        """Trigger background summarization (non-blocking).

        This spawns a background task to summarize the current context.
        The summary will be cached and ready when rotation triggers.
        """
        if not self.registry or not self.context_envelope:
            logger.warning("Session %s: Cannot summarize without registry/context", self.session_id)
            return

        logger.debug("Session %s: Triggering background summarization", self.session_id)

        try:
            # Get summarizer from registry
            summarizer = self.registry.summarizer

            # Trigger background summarization
            await summarizer.trigger_summarization(
                session_id=self.session_id,
                context=self.context_envelope.to_dict(),
                turn_id=self.turn_id,
                summarize_threshold=self.config.summarize_threshold_pct if self.config else 60.0,
                rotate_threshold=self.config.rotate_threshold_pct if self.config else 70.0,
            )

        except Exception as e:
            logger.exception("Session %s: Background summarization failed: %s", self.session_id, e)

    def increment_turn(self) -> None:
        """Increment turn counter.

        Should be called after each user/agent interaction.
        """
        self.turn_id += 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage/transmission.

        Returns:
            Dict representation
        """
        return {
            "session_id": self.session_id,
            "active_generation": self.active_generation,
            "turn_id": self.turn_id,
            "model": self.model,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "utilization_pct": self.get_utilization_pct(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionContext(session_id={self.session_id}, "
            f"generation={self.active_generation}, turn={self.turn_id}, "
            f"utilization={self.get_utilization_pct():.1f}%)"
        )


class SessionContextManager:
    """Manager for creating and tracking session contexts.

    This provides centralized management of session contexts for
    integration with agent pools and MCP tools.
    """

    def __init__(
        self,
        config: RotationConfig | None = None,
        registry: Any | None = None,
    ) -> None:
        """Initialize session context manager.

        Args:
            config: Rotation configuration
            registry: Session registry for rotation integration
        """
        self.config = config
        self.registry = registry
        self._contexts: dict[str, SessionContext] = {}

        logger.info("SessionContextManager initialized")

    async def create_session(
        self,
        session_id: str,
        model: str = "claude-sonnet-4-5",
        token_budget: int = 100000,
    ) -> SessionContext:
        """Create a new session context.

        Args:
            session_id: Unique session identifier
            model: LLM model
            token_budget: Total token budget

        Returns:
            SessionContext instance
        """
        ctx = SessionContext.create(
            session_id=session_id,
            model=model,
            token_budget=token_budget,
            config=self.config,
        )

        # Attach registry if configured
        if self.registry:
            ctx.registry = self.registry
            ctx.budget_tracker = self.registry.budget_trackers.get(session_id)

        self._contexts[session_id] = ctx

        logger.info("Created session context: %s", session_id)
        return ctx

    async def get_session(self, session_id: str) -> SessionContext | None:
        """Get existing session context.

        Args:
            session_id: Session identifier

        Returns:
            SessionContext or None if not found
        """
        return self._contexts.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        """Remove session context.

        Args:
            session_id: Session identifier
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info("Removed session context: %s", session_id)

    def get_all_sessions(self) -> list[SessionContext]:
        """Get all active session contexts.

        Returns:
            List of SessionContext instances
        """
        return list(self._contexts.values())

    def get_stats(self) -> dict[str, Any]:
        """Get context manager statistics.

        Returns:
            Stats dict with active_sessions, total_tokens_used, avg_utilization
        """
        active_sessions = len(self._contexts)
        total_tokens = sum(ctx.tokens_used for ctx in self._contexts.values())
        avg_utilization = (
            sum(ctx.get_utilization_pct() for ctx in self._contexts.values()) / active_sessions
            if active_sessions > 0
            else 0.0
        )

        return {
            "active_sessions": active_sessions,
            "total_tokens_used": total_tokens,
            "avg_utilization_pct": avg_utilization,
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return f"SessionContextManager(active_sessions={stats['active_sessions']}, avg_util={stats['avg_utilization_pct']:.1f}%)"
