"""
Wave-based execution model for orchestration.

Executes tasks in dependency waves where each wave contains tasks with no
dependencies on each other (can run in parallel).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import yaml

from sibyl.core.contracts.graph import GraphProvider, NodeId
from sibyl.techniques.workflow_orchestration.graph import (
    GenericGraphService,
    NetworkXGraphAnalyzer,
)

logger = logging.getLogger(__name__)


class WaveBasedImplementation:
    """Wave-based parallel execution model.

    Executes tasks in dependency order, grouping independent tasks into
    "waves" that can be executed in parallel.
    """

    def __init__(self) -> None:
        self._name = "wave_based"
        self._description = "Executes tasks in parallel waves based on dependencies"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """Execute tasks using wave-based orchestration.

        Args:
            input_data: Dictionary with:
                - graph: GraphProvider with task dependencies
                - executor_fn: Callable[[NodeId, Dict], Awaitable[Any]] - executes a task
                - context: Optional shared context dict
            config: Merged configuration with:
                - max_parallel: Maximum concurrent tasks per wave (default: 10)

        Returns:
            Dictionary mapping node IDs to their results
        """
        # Extract inputs
        graph = input_data.get("graph")
        executor_fn = input_data.get("executor_fn")
        context = input_data.get("context", {})

        if not graph or not executor_fn:
            msg = "input_data must contain 'graph' and 'executor_fn'"
            raise ValueError(msg)

        # Get configuration
        max_parallel = config.get("max_parallel", 10)

        # Compute waves
        waves = self._compute_waves(graph)
        logger.info("Computed %s execution waves", len(waves))

        results = {}
        shared_context = {**context}

        # Execute each wave
        for wave_num, wave_nodes in enumerate(waves, 1):
            logger.info("Executing wave %s/%s with %s tasks", wave_num, len(waves), len(wave_nodes))

            # Execute wave tasks in parallel (with limit)
            wave_results = await self._execute_wave(
                wave_nodes, executor_fn, shared_context, results, max_parallel
            )

            # Update results and context
            results.update(wave_results)

            # Update shared context with wave results
            for _node_id, result in wave_results.items():
                if isinstance(result, dict):
                    shared_context.update(result)

            logger.info("Wave %s completed", wave_num)

        logger.info("All waves completed successfully")
        return results

    async def _execute_wave(
        self,
        nodes: list[NodeId],
        executor_fn: Callable[[NodeId, dict[str, Any]], Awaitable[Any]],
        context: dict[str, Any],
        previous_results: dict[NodeId, Any],
        max_parallel: int,
    ) -> dict[NodeId, Any]:
        """Execute all tasks in a wave.

        Args:
            nodes: List of node IDs to execute
            executor_fn: Executor function
            context: Shared context
            previous_results: Results from previous waves
            max_parallel: Maximum concurrent tasks

        Returns:
            Dictionary mapping node IDs to results
        """
        # Create tasks
        tasks = []
        for node_id in nodes:
            task_context = {
                **context,
                "node_id": node_id,
                "previous_results": previous_results,
            }
            tasks.append(self._execute_task(node_id, executor_fn, task_context))

        # Execute with semaphore to limit parallelism
        semaphore = asyncio.Semaphore(max_parallel)

        async def limited_task(task, node_id: Any) -> Any:
            async with semaphore:
                return node_id, await task

        limited_tasks = [
            limited_task(task, node_id) for task, node_id in zip(tasks, nodes, strict=False)
        ]

        # Wait for all tasks
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)

        # Process results
        wave_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error("Task failed: %s", result)
                raise result

            node_id, task_result = result
            wave_results[node_id] = task_result

        return wave_results

    async def _execute_task(
        self,
        node_id: NodeId,
        executor_fn: Callable[[NodeId, dict[str, Any]], Awaitable[Any]],
        context: dict[str, Any],
    ) -> Any:
        """Execute a single task.

        Args:
            node_id: Node ID
            executor_fn: Executor function
            context: Task context

        Returns:
            Task result
        """
        try:
            logger.debug("Executing task: %s", node_id)
            result = await executor_fn(node_id, context)
            logger.debug("Task %s completed", node_id)
            return result
        except Exception as e:
            logger.exception("Task %s failed: %s", node_id, e)
            msg = f"Task {node_id} failed: {e}"
            raise RuntimeError(msg) from e

    def _compute_waves(self, graph: GraphProvider) -> list[list[NodeId]]:
        """Compute execution waves from dependency graph.

        Each wave contains nodes that have no dependencies on each other
        and all their dependencies have been satisfied in previous waves.

        Args:
            graph: Graph provider

        Returns:
            List of waves, where each wave is a list of node IDs
        """
        if not isinstance(graph, GenericGraphService):
            msg = "WaveBased execution requires GenericGraphService"
            raise TypeError(msg)

        analyzer = NetworkXGraphAnalyzer(graph)

        # Check for cycles
        cycles = analyzer.find_cycles()
        if cycles:
            msg = f"Graph contains cycles: {cycles}"
            raise ValueError(msg)

        # Compute depths (distance from root nodes)
        depths = analyzer.compute_depths()

        # Group nodes by depth (depth = wave number)
        waves_dict: dict[int, list[NodeId]] = {}
        for node_id, depth in depths.items():
            if depth not in waves_dict:
                waves_dict[depth] = []
            waves_dict[depth].append(node_id)

        # Convert to list of waves
        max_depth = max(waves_dict.keys()) if waves_dict else 0
        return [waves_dict.get(i, []) for i in range(max_depth + 1)]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {"max_parallel": 10}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "max_parallel" in config:
            max_parallel = config["max_parallel"]
            if not isinstance(max_parallel, int) or max_parallel <= 0:
                return False
        return True
