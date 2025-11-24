"""Generic wave orchestrator - executes tasks in dependency waves.

This module provides generic wave-based execution with NO domain assumptions.
Tasks are executed in "waves" where each wave contains tasks with no dependencies
on each other (can run in parallel).

Example usage:
    async def task_a(context):
        return {"result": "A"}

    async def task_b(context):
        return {"result": "B"}

    async def task_c(context):
        # Depends on A and B
        return {"result": "C"}

    orchestrator = WaveOrchestrator()
    results = await orchestrator.run(
        graph=workflow_graph,
        executor_fn=lambda step_id, ctx: steps[step_id].executor(ctx),
        context={}
    )
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sibyl.core.contracts.graph import GraphProvider, NodeId
from sibyl.observability import execute_with_observability_async
from sibyl.techniques.workflow_orchestration.orchestration.impls.graph import NetworkXGraphAnalyzer

logger = logging.getLogger(__name__)


class WaveOrchestrator:
    """Generic wave-based task orchestrator.

    Executes tasks in dependency order, grouping independent tasks into
    "waves" that can be executed in parallel.
    """

    def __init__(self, max_parallel: int = 10) -> None:
        """Initialize wave orchestrator.

        Args:
            max_parallel: Maximum number of tasks to run in parallel per wave
        """
        self.max_parallel = max_parallel
        logger.info("Initialized WaveOrchestrator (max_parallel=%s)", max_parallel)

    async def run(
        self,
        graph: GraphProvider,
        executor_fn: Callable[[NodeId, dict[str, Any]], Awaitable[Any]],
        context: dict[str, Any],
    ) -> dict[NodeId, Any]:
        """Execute tasks in dependency waves.

        Args:
            graph: Graph provider with task dependencies
            executor_fn: Function to execute a task (takes node_id and context)
            context: Shared context for all tasks

        Returns:
            Dictionary mapping node IDs to their results
        """
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
                wave_nodes, executor_fn, shared_context, results
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
    ) -> dict[NodeId, Any]:
        """Execute all tasks in a wave.

        Args:
            nodes: List of node IDs to execute
            executor_fn: Executor function
            context: Shared context
            previous_results: Results from previous waves

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
        semaphore = asyncio.Semaphore(self.max_parallel)

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

        async def _execute() -> Any:
            return await executor_fn(node_id, context)

        try:
            logger.debug("Executing task: %s", node_id)
            result = await execute_with_observability_async(
                technique_name="wave_orchestrator",
                subtechnique="wave_task",
                implementation=str(node_id),
                input_data=context,
                config={"node_id": node_id},
                executor=_execute,
                extra_log_fields={"wave_context": True},
            )
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
        from sibyl.techniques.workflow_orchestration.orchestration.impls.graph import (
            GenericGraphService,
        )

        if not isinstance(graph, GenericGraphService):
            msg = "WaveOrchestrator requires GenericGraphService"
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


# Export public API
__all__ = [
    "WaveOrchestrator",
]
