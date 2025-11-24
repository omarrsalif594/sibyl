"""
Sequential execution model for orchestration.

Executes tasks one at a time in a fixed order.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SequentialImplementation:
    """Sequential execution model.

    Executes tasks one at a time in the provided order. No parallelism.
    """

    def __init__(self) -> None:
        self._name = "sequential"
        self._description = "Executes tasks sequentially in order"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """Execute tasks sequentially.

        Args:
            input_data: Dictionary with:
                - tasks: List of task IDs or ordered list
                - executor_fn: Callable[[task_id, Dict], Awaitable[Any]] - executes a task
                - context: Optional shared context dict
            config: Merged configuration

        Returns:
            Dictionary mapping task IDs to their results or list of results
        """
        # Extract inputs
        tasks = input_data.get("tasks")
        executor_fn = input_data.get("executor_fn")
        context = input_data.get("context", {})

        if not tasks or not executor_fn:
            msg = "input_data must contain 'tasks' and 'executor_fn'"
            raise ValueError(msg)

        logger.info("Starting sequential execution of %s tasks", len(tasks))

        results = {}
        shared_context = {**context}

        # Execute tasks one by one
        for idx, task_id in enumerate(tasks, 1):
            logger.info("Executing task %s/%s: %s", idx, len(tasks), task_id)

            # Prepare task context
            task_context = {
                **shared_context,
                "task_id": task_id,
                "task_index": idx - 1,
                "previous_results": results,
            }

            try:
                # Execute task
                result = await executor_fn(task_id, task_context)
                results[task_id] = result

                # Update shared context with result
                if isinstance(result, dict):
                    shared_context.update(result)

                logger.debug("Task %s completed successfully", task_id)

            except Exception as e:
                logger.exception("Task %s failed: %s", task_id, e)
                results[task_id] = {"error": str(e)}

                # Check if we should stop on error
                if config.get("stop_on_error", True):
                    msg = f"Sequential execution failed at task {task_id}: {e}"
                    raise RuntimeError(msg) from e
                logger.warning("Continuing after error in task %s", task_id)

        logger.info("Sequential execution completed successfully")
        return results

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {"stop_on_error": True}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return not ("stop_on_error" in config and not isinstance(config["stop_on_error"], bool))
