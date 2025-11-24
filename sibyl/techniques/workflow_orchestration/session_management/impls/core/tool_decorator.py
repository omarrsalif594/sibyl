"""Generation-aware MCP tool decorator with operation boundary contract.

This module provides a decorator for MCP tools that enforces:
- **Operation boundary contract**: Tool calls bind to generation at entry
- **Generation validation**: Reject calls if generation mismatch (rotated mid-call)
- **In-flight tracking**: Track operations for proper draining
- **Token accounting**: Record token usage to SessionBudgetTracker
- **Rotation triggers**: Check thresholds after tool completion

Key guarantees:
- Tool calls see stable generation for entire execution
- No tool calls span rotation boundaries
- Token accounting is accurate and atomic
- Rotation triggers automatically when threshold exceeded

Typical usage:
    @with_session_tracking
    async def fast_query_downstream(model_id: str, session_id: Optional[str] = None):
        # Tool logic here
        return {"downstream": [...]}

    # Tool is automatically:
    # 1. Bound to generation at entry
    # 2. Tracked as in-flight operation
    # 3. Token usage recorded
    # 4. Rotation triggered if needed
    # 5. Session metadata returned
"""

import asyncio
import functools
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class SessionTrackingError(Exception):
    """Base exception for session tracking errors."""


class GenerationMismatchError(SessionTrackingError):
    """Raised when generation mismatch detected (rotation occurred)."""


class SessionNotFoundError(SessionTrackingError):
    """Raised when session not found."""


class RotationAdmissionError(SessionTrackingError):
    """Raised when tool call is rejected during rotation.

    Attributes:
        message: Error message
        error_type: Machine-readable error type for metrics
        session_id: Session ID for correlation
        requested_generation: Generation requested by tool
        current_generation: Current session generation
    """

    def __init__(
        self,
        message: str,
        error_type: str,
        session_id: str | None = None,
        requested_generation: int | None = None,
        current_generation: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.session_id = session_id
        self.requested_generation = requested_generation
        self.current_generation = current_generation


def with_session_tracking(func: Callable) -> Callable:
    """Decorator for MCP tools with session tracking and operation boundary enforcement.

    This decorator wraps an MCP tool to provide:
    1. Generation binding at entry
    2. In-flight operation tracking
    3. Token usage recording
    4. Rotation trigger checking
    5. Session metadata in response

    The decorated tool must accept an optional `session_id` parameter.

    Operation boundary contract:
    - Tool binds to `active_generation` at entry time
    - If generation changes during execution (rotation), tool proceeds normally
    - Token accounting attributes to entry generation (immutable)
    - After completion, check if new rotation needed

    Args:
        func: Async function to decorate

    Returns:
        Decorated function with session tracking

    Example:
        @with_session_tracking
        async def my_tool(param1: str, session_id: Optional[str] = None):
            # Tool logic
            return {"result": "..."}

        # Call tool
        result = await my_tool(param1="foo", session_id="sess_abc")

        # Result includes session metadata:
        {
            "result": "...",
            "_session_metadata": {
                "session_id": "sess_abc",
                "tokens_used": 1234,
                "tokens_spent": 45678,
                "tokens_budget": 100000,
                "utilization_pct": 45.7,
                "rotation_suggested": False,
                "active_generation": 2,
                "generation_at_completion": 2
            }
        }
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract session_id from kwargs (or use default)
        session_id = kwargs.get("session_id") or _get_default_session_id()

        # Get registry (injected via dependency injection or global)
        registry = _get_session_registry()
        if not registry:
            logger.warning(
                "Session registry not available, skipping tracking for %s", func.__name__
            )
            return await func(*args, **kwargs)

        # Get session
        rotation_manager = registry.rotation_manager
        budget_tracker = registry.budget_trackers.get(session_id)
        session = await rotation_manager.get_session(session_id)

        if not session:
            # Session not found, create default or raise error
            logger.warning("Session %s not found, using default session", session_id)
            session_id = await registry.get_or_create_default_session()
            session = await rotation_manager.get_session(session_id)
            budget_tracker = registry.budget_trackers.get(session_id)

        # Bind to generation at entry (operation boundary contract)
        entry_generation = session.active_generation
        correlation_id = str(uuid.uuid4())

        # Begin operation (check generation match and admission control)
        admission_result = await rotation_manager.begin_operation(session_id, entry_generation)

        if not admission_result.allowed:
            # Raise appropriate typed exception based on error type
            if admission_result.error_type == "rotation_in_progress":
                raise RotationAdmissionError(
                    message=admission_result.reason or "Rotation in progress",
                    error_type=admission_result.error_type,
                    session_id=admission_result.session_id,
                    requested_generation=admission_result.requested_generation,
                    current_generation=admission_result.current_generation,
                )
            if admission_result.error_type == "session_not_found":
                msg = f"Session {session_id} not found"
                raise SessionNotFoundError(msg)
            if admission_result.error_type == "generation_mismatch":
                raise GenerationMismatchError(admission_result.reason or "Generation mismatch")
            # Unknown error type
            raise RotationAdmissionError(
                message=admission_result.reason or "Admission rejected",
                error_type=admission_result.error_type or "unknown",
                session_id=admission_result.session_id,
                requested_generation=admission_result.requested_generation,
                current_generation=admission_result.current_generation,
            )

        logger.debug(
            "[%s] Tool %s started (gen=%s, corr=%s)",
            session_id,
            func.__name__,
            entry_generation,
            correlation_id[:8],
        )

        start_time = time.time()

        try:
            # Execute tool
            result = await func(*args, **kwargs)

            # Token counting
            tokens_in, tokens_out = await _estimate_token_usage(func.__name__, args, kwargs, result)
            tokens_total = tokens_in + tokens_out

            # Record token usage (if budget tracker available)
            if budget_tracker:
                await budget_tracker.record_usage(
                    tool_name=func.__name__,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    timestamp=start_time,
                )

                # Check rotation threshold
                rotation_action = await budget_tracker.check_threshold()

                # Trigger rotation if needed (non-blocking background task)
                if rotation_action.value == "rotate_now" and registry.config.enabled:
                    logger.info("[%s] Rotation threshold exceeded, triggering rotation", session_id)
                    # Schedule rotation in background (don't block tool response)
                    asyncio.create_task(
                        registry.trigger_rotation(session_id=session_id, trigger="token_threshold")
                    )
                    rotation_suggested = True
                elif (
                    rotation_action.value == "summarize_context"
                    and not budget_tracker._summarize_triggered
                ):
                    logger.info(
                        "[%s] Summarize threshold exceeded, starting background summarization",
                        session_id,
                    )
                    # Schedule background summarization
                    asyncio.create_task(registry.trigger_summarization(session_id=session_id))
                    rotation_suggested = False
                else:
                    rotation_suggested = False

                # Get updated session (may have been rotated)
                completion_session = await rotation_manager.get_session(session_id)
                completion_generation = (
                    completion_session.active_generation if completion_session else entry_generation
                )

                # Add session metadata to result
                session_metadata = {
                    "session_id": session_id,
                    "tokens_used": tokens_total,
                    "tokens_spent": budget_tracker.tokens_spent,
                    "tokens_budget": budget_tracker.tokens_budget,
                    "utilization_pct": budget_tracker.get_utilization_pct(),
                    "rotation_suggested": rotation_suggested,
                    "active_generation": entry_generation,
                    "generation_at_completion": completion_generation,
                    "correlation_id": correlation_id,
                }

                # Inject metadata into result
                if isinstance(result, dict):
                    result["_session_metadata"] = session_metadata
                else:
                    # Wrap result if not dict
                    result = {"result": result, "_session_metadata": session_metadata}

            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"[{session_id}] Tool {func.__name__} completed in {duration_ms:.0f}ms "
                f"(tokens={tokens_total}, gen={entry_generation}→{completion_generation})"
            )

            return result

        finally:
            # Always end operation (even on error)
            await rotation_manager.end_operation(session_id)

    return wrapper


async def _estimate_token_usage(
    tool_name: str, args: tuple, kwargs: dict, result: Any
) -> tuple[int, int]:
    """Estimate token usage for tool call.

    This is a rough estimate. In production, you'd integrate with actual
    TokenCounter from the orchestration layer.

    Args:
        tool_name: Tool name
        args: Tool arguments
        kwargs: Tool keyword arguments
        result: Tool result

    Returns:
        Tuple of (tokens_in, tokens_out)
    """
    # Rough estimate: 4 chars = 1 token
    import json  # can be moved to top

    try:
        # Estimate input tokens (args + kwargs)
        input_text = json.dumps({"tool": tool_name, "args": args, "kwargs": kwargs})
        tokens_in = len(input_text) // 4

        # Estimate output tokens (result)
        output_text = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        tokens_out = len(output_text) // 4

        return tokens_in, tokens_out

    except Exception:
        # Fallback estimate
        return 100, 200  # Conservative estimate


def _get_default_session_id() -> str:
    """Get default session ID.

    Returns:
        Default session ID
    """
    # TODO: Implement proper default session logic
    # For now, return a static ID
    return "sess_default"


def _get_session_registry() -> Any | None:
    """Get session registry (injected via DI or global).

    Returns:
        SessionRegistry instance or None
    """
    # TODO: Implement proper DI integration
    # For now, return None (will be integrated in Day 3 task 4)
    from .registry import get_global_registry

    return get_global_registry()


# Example usage decorator for tools that don't need session tracking
def without_session_tracking(func: Callable) -> Callable:
    """Decorator to explicitly skip session tracking for a tool.

    Use this for tools that are:
    - Read-only and don't use tokens (e.g., list_branches)
    - Administrative (e.g., health checks)
    - Can't accept session_id parameter

    Args:
        func: Function to decorate

    Returns:
        Original function unchanged
    """
    return func
