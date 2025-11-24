"""Generic workflow graph - domain-agnostic workflow orchestration.

This module provides generic workflow primitives using the graph framework.

Use terminology: step, task, workflow - NOT model, compile, test.

Example usage:
    # Define workflow steps
    steps = [
        WorkflowStep(
            id="check_stock",
            dependencies=[],
            executor=check_stock_fn,
            context={"threshold": 50}
        ),
        WorkflowStep(
            id="generate_order",
            dependencies=["check_stock"],
            executor=generate_order_fn,
            context={}
        ),
    ]

    # Create workflow graph
    workflow = WorkflowGraph(steps)

    # Execute
    results = await workflow.execute()
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sibyl.techniques.workflow_orchestration.orchestration.graph import (
    GenericGraphService,
    NetworkXGraphAnalyzer,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Generic workflow step - represents a single task in a workflow.

    Attributes:
        id: Unique step identifier
        dependencies: List of step IDs this step depends on
        executor: Async function to execute this step
        context: Additional context for execution
        metadata: Step metadata
    """

    id: str
    dependencies: list[str]
    executor: Callable[[dict[str, Any]], Awaitable[Any]]
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowGraph:
    """Generic workflow graph using graph primitives.

    This class orchestrates workflow execution using the generic graph framework.
    It's completely domain-agnostic.
    """

    def __init__(self, steps: list[WorkflowStep]) -> None:
        """Initialize workflow graph.

        Args:
            steps: List of WorkflowStep objects
        """
        self.steps = {step.id: step for step in steps}
        self._graph = self._build_graph(steps)
        self._analyzer = NetworkXGraphAnalyzer(self._graph)
        logger.info("Initialized WorkflowGraph with %s steps", len(steps))

    def _build_graph(self, steps: list[WorkflowStep]) -> GenericGraphService:
        """Build dependency graph from steps.

        Args:
            steps: List of WorkflowStep objects

        Returns:
            GenericGraphService with workflow dependencies
        """
        graph = GenericGraphService()

        # Add nodes
        for step in steps:
            graph.add_node(step.id, "workflow_step", step.metadata)

        # Add edges (dependencies)
        for step in steps:
            for dep in step.dependencies:
                graph.add_edge(dep, step.id, "depends_on", {})

        return graph

    async def execute(self, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute workflow in dependency order.

        Args:
            initial_context: Initial context for workflow execution

        Returns:
            Dictionary mapping step IDs to their results
        """
        initial_context = initial_context or {}

        # Check for cycles
        cycles = self._analyzer.find_cycles()
        if cycles:
            msg = f"Workflow contains cycles: {cycles}"
            raise ValueError(msg)

        # Get topological order
        try:
            execution_order = self._analyzer.topological_sort()
        except ValueError as e:
            msg = f"Cannot determine execution order: {e}"
            raise ValueError(msg) from e

        logger.info("Executing workflow with %s steps", len(execution_order))

        # Execute steps in order
        results = {}
        shared_context = {**initial_context}

        for step_id in execution_order:
            step = self.steps[step_id]

            logger.debug("Executing step: %s", step_id)

            # Merge step context with shared context
            execution_context = {
                **shared_context,
                **step.context,
                "step_id": step_id,
                "previous_results": results,
            }

            try:
                # Execute step
                result = await step.executor(execution_context)
                results[step_id] = result

                # Update shared context with result
                if isinstance(result, dict):
                    shared_context.update(result)

                logger.info("Step %s completed successfully", step_id)
            except Exception as e:
                logger.exception("Step %s failed: %s", step_id, e)
                results[step_id] = {"error": str(e)}
                msg = f"Workflow failed at step {step_id}: {e}"
                raise RuntimeError(msg) from e

        logger.info("Workflow execution completed successfully")
        return results

    def get_execution_order(self) -> list[str]:
        """Get the order in which steps will be executed.

        Returns:
            List of step IDs in execution order
        """
        return self._analyzer.topological_sort()

    def get_stats(self) -> dict[str, Any]:
        """Get workflow statistics.

        Returns:
            Dictionary with workflow statistics
        """
        stats = self._analyzer.get_stats()
        return {
            "step_count": stats["node_count"],
            "dependency_count": stats["edge_count"],
            "is_valid": stats["is_dag"],
            "execution_order": self.get_execution_order() if stats["is_dag"] else None,
        }


# Export public API
__all__ = [
    "WorkflowGraph",
    "WorkflowStep",
]
