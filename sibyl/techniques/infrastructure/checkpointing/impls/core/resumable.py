"""Resumable operation decorator and utilities.

This module provides:
- @resumable decorator for automatic checkpointing
- resume_from_checkpoint() function to restore state
- Utilities for checkpoint-based iteration

Example:
    from sibyl.mcp_server.infrastructure.checkpointing import (
        resumable,
        get_checkpoint_store,
    )

    @resumable(
        checkpoint_interval=5,  # Checkpoint every 5 items
        store=get_checkpoint_store(),
    )
    async def batch_compile(models: List[str], operation_id: str = None):
        '''Compile multiple models with automatic checkpointing.'''
        results = []
        for model in models:
            result = await compile_model(model)
            results.append(result)
            # Checkpoint saved automatically every 5 models
        return results

    # If operation fails, resume from last checkpoint
    results = await batch_compile(
        models=["model_a", "model_b", ...],
        operation_id="batch-123",  # Same ID resumes from checkpoint
    )
"""

import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

from sibyl.mcp_server.infrastructure.checkpointing.json_store import (
    JSONCheckpointStore,
)
from sibyl.mcp_server.infrastructure.checkpointing.protocol import (
    CheckpointStore,
    OperationCheckpoint,
    ResumableOperationState,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Global checkpoint store
_global_store: CheckpointStore | None = None


def get_checkpoint_store() -> CheckpointStore:
    """Get global checkpoint store instance.

    Returns:
        Global CheckpointStore instance
    """
    global _global_store
    if _global_store is None:
        _global_store = JSONCheckpointStore()
    return _global_store


def set_checkpoint_store(store: CheckpointStore) -> None:
    """Set global checkpoint store.

    Args:
        store: CheckpointStore implementation
    """
    global _global_store
    _global_store = store


def resumable(
    checkpoint_interval: int = 10,
    store: CheckpointStore | None = None,
    operation_name: str | None = None,
):
    """Decorator for resumable operations with automatic checkpointing.

    The decorated function must:
    - Accept operation_id as a parameter (optional, auto-generated if None)
    - Return a result that can be checkpointed
    - Be an async function

    The decorator will:
    - Check for existing checkpoints on start
    - Save checkpoints periodically during execution
    - Clean up checkpoints on successful completion

    Args:
        checkpoint_interval: Number of items between checkpoints
        store: CheckpointStore to use (default: global store)
        operation_name: Operation name (default: function name)

    Returns:
        Decorated function

    Example:
        @resumable(checkpoint_interval=5)
        async def process_items(items: List[str], operation_id: str = None):
            for item in items:
                result = await process(item)
            return results
    """

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        # Use function name if operation_name not provided
        op_name = operation_name or func.__name__
        checkpoint_store = store or get_checkpoint_store()

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extract operation_id from kwargs
            operation_id = kwargs.get("operation_id")

            if operation_id:
                # Try to resume from checkpoint
                last_checkpoint = checkpoint_store.load_latest_checkpoint(operation_id)

                if last_checkpoint:
                    logger.info(
                        "Resuming operation %s from checkpoint %s",
                        operation_id,
                        last_checkpoint.checkpoint_id,
                    )
                    # Store checkpoint in kwargs for function to use
                    kwargs["resume_checkpoint"] = last_checkpoint
                else:
                    logger.info("Starting new operation %s", operation_id)
            else:
                # Generate operation_id
                from uuid import uuid4

                operation_id = f"{op_name}_{uuid4().hex[:8]}"
                kwargs["operation_id"] = operation_id
                logger.info("Starting new operation %s", operation_id)

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Clean up checkpoints on success
                if operation_id:
                    deleted = checkpoint_store.delete_all_checkpoints(operation_id)
                    logger.info(
                        f"Operation {operation_id} completed successfully. "
                        f"Deleted {deleted} checkpoints."
                    )

                return result

            except Exception as e:
                logger.exception(
                    f"Operation {operation_id} failed: {e}. Checkpoints preserved for resume."
                )
                raise

        return wrapper

    return decorator


def resume_from_checkpoint(
    checkpoint: OperationCheckpoint,
) -> ResumableOperationState:
    """Resume operation from checkpoint.

    Args:
        checkpoint: Checkpoint to resume from

    Returns:
        ResumableOperationState with restored state
    """
    state = ResumableOperationState.from_checkpoint(checkpoint)

    logger.info(
        f"Resumed operation {checkpoint.operation_id} from checkpoint {checkpoint.checkpoint_id}. "
        f"Completed: {len(state.completed_items)}, Pending: {len(state.pending_items)}, "
        f"Failed: {len(state.failed_items)}"
    )

    return state


def save_checkpoint(
    state: ResumableOperationState,
    checkpoint_id: str | None = None,
    store: CheckpointStore | None = None,
) -> None:
    """Save checkpoint for resumable operation.

    Args:
        state: Current operation state
        checkpoint_id: Optional checkpoint ID (auto-generated if None)
        store: CheckpointStore to use (default: global store)
    """
    checkpoint_store = store or get_checkpoint_store()

    checkpoint = state.to_checkpoint(checkpoint_id)
    checkpoint_store.save_checkpoint(checkpoint)

    state.last_checkpoint_at = checkpoint.created_at
    state.current_checkpoint = checkpoint.checkpoint_id

    logger.debug(
        "Saved checkpoint %s for operation %s", checkpoint.checkpoint_id, state.operation_id
    )


async def process_with_checkpointing(
    items: list[str],
    process_func: Callable[[str], Coroutine[Any, Any, dict]],
    operation_id: str,
    operation_name: str,
    checkpoint_interval: int = 10,
    resume_checkpoint: OperationCheckpoint | None = None,
    store: CheckpointStore | None = None,
) -> tuple[list[dict], ResumableOperationState]:
    """Process items with automatic checkpointing.

    Utility function for batch operations with checkpoint support.

    Args:
        items: List of items to process
        process_func: Async function to process each item
        operation_id: Unique operation ID
        operation_name: Operation name
        checkpoint_interval: Items between checkpoints
        resume_checkpoint: Optional checkpoint to resume from
        store: CheckpointStore to use

    Returns:
        Tuple of (results, final_state)

    Example:
        async def compile_model(model_name: str) -> dict:
            return {"model": model_name, "status": "success"}

        results, state = await process_with_checkpointing(
            items=["model_a", "model_b", "model_c"],
            process_func=compile_model,
            operation_id="batch-123",
            operation_name="compile",
        )
    """
    checkpoint_store = store or get_checkpoint_store()

    # Initialize or resume state
    if resume_checkpoint:
        state = resume_from_checkpoint(resume_checkpoint)
        # Filter out already completed items
        remaining_items = [item for item in items if item not in state.completed_items]
    else:
        state = ResumableOperationState(
            operation_id=operation_id,
            operation_name=operation_name,
            pending_items=items.copy(),
        )
        remaining_items = items

    logger.info("Processing %s items for operation %s", len(remaining_items), operation_id)

    results = []

    for item in remaining_items:
        try:
            result = await process_func(item)
            results.append(result)
            state.mark_completed(item)

            # Checkpoint if interval reached
            if state.should_checkpoint(checkpoint_interval):
                save_checkpoint(state, store=checkpoint_store)

        except Exception as e:
            state.mark_failed(item, e)
            logger.exception("Failed to process %s: %s", item, e)

            # Save checkpoint on failure
            save_checkpoint(state, store=checkpoint_store)

            # Continue processing other items (don't stop on single failure)

    # Save final checkpoint
    save_checkpoint(state, checkpoint_id="final", store=checkpoint_store)

    logger.info(
        f"Completed processing for operation {operation_id}. "
        f"Completed: {len(state.completed_items)}, Failed: {len(state.failed_items)}"
    )

    return results, state


def get_resumable_items(
    all_items: list[str],
    checkpoint: OperationCheckpoint | None,
) -> list[str]:
    """Get list of items to process, excluding already completed.

    Args:
        all_items: Full list of items
        checkpoint: Optional checkpoint to resume from

    Returns:
        List of items to process
    """
    if not checkpoint:
        return all_items

    completed = checkpoint.state.get("completed_items", [])
    remaining = [item for item in all_items if item not in completed]

    logger.info("Resume: %s completed, %s remaining", len(completed), len(remaining))

    return remaining
