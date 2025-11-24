"""
DAG-based execution model for orchestration.

Executes tasks in topological order based on a dependency graph.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.core.contracts.graph import GraphProvider, NodeId
from sibyl.techniques.workflow_orchestration.graph import (
    GenericGraphService,
    NetworkXGraphAnalyzer,
)

logger = logging.getLogger(__name__)


class DagBasedImplementation:
    """DAG-based sequential execution model.

    Executes tasks in topological (dependency) order, one at a time.
    Tasks are executed sequentially but in an order that respects dependencies.
    """

    def __init__(self) -> None:
        self._name = "dag_based"
        self._description = "Executes tasks in topological order based on DAG"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """Execute tasks in topological order.

        Args:
            input_data: Dictionary with:
                - graph: GraphProvider with task dependencies
                - executor_fn: Callable[[NodeId, Dict], Awaitable[Any]] - executes a task
                - context: Optional shared context dict
            config: Merged configuration with:
                - stop_on_error: Whether to stop on first error (default: True)

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

        if not isinstance(graph, GenericGraphService):
            msg = "DAGBased execution requires GenericGraphService"
            raise TypeError(msg)

        # Get configuration
        stop_on_error = config.get("stop_on_error", True)

        # Analyze graph
        analyzer = NetworkXGraphAnalyzer(graph)

        # Check for cycles
        cycles = analyzer.find_cycles()
        if cycles:
            msg = f"Graph contains cycles: {cycles}"
            raise ValueError(msg)

        # Get topological order
        try:
            execution_order = analyzer.topological_sort()
        except ValueError as e:
            msg = f"Cannot determine execution order: {e}"
            raise ValueError(msg) from e

        logger.info("Executing %s tasks in topological order", len(execution_order))

        # Execute steps in order
        results = {}
        shared_context = {**context}

        for idx, node_id in enumerate(execution_order, 1):
            logger.info("Executing task %s/%s: %s", idx, len(execution_order), node_id)

            # Merge context
            execution_context = {
                **shared_context,
                "node_id": node_id,
                "task_index": idx - 1,
                "previous_results": results,
            }

            try:
                # Execute task
                result = await executor_fn(node_id, execution_context)
                results[node_id] = result

                # Update shared context with result
                if isinstance(result, dict):
                    shared_context.update(result)

                logger.info("Task %s completed successfully", node_id)

            except Exception as e:
                logger.exception("Task %s failed: %s", node_id, e)
                results[node_id] = {"error": str(e)}

                if stop_on_error:
                    msg = f"DAG execution failed at task {node_id}: {e}"
                    raise RuntimeError(msg) from e
                logger.warning("Continuing after error in task %s", node_id)

        logger.info("DAG execution completed successfully")
        return results

    def get_execution_order(self, graph: GraphProvider) -> list[NodeId]:
        """Get the order in which tasks will be executed.

        Args:
            graph: Graph provider

        Returns:
            List of node IDs in execution order
        """
        if not isinstance(graph, GenericGraphService):
            msg = "DAGBased execution requires GenericGraphService"
            raise TypeError(msg)

        analyzer = NetworkXGraphAnalyzer(graph)
        return analyzer.topological_sort()

    def get_stats(self, graph: GraphProvider) -> dict[str, Any]:
        """Get DAG statistics.

        Args:
            graph: Graph provider

        Returns:
            Dictionary with DAG statistics
        """
        if not isinstance(graph, GenericGraphService):
            msg = "DAGBased execution requires GenericGraphService"
            raise TypeError(msg)

        analyzer = NetworkXGraphAnalyzer(graph)
        stats = analyzer.get_stats()

        return {
            "task_count": stats["node_count"],
            "dependency_count": stats["edge_count"],
            "is_valid": stats["is_dag"],
            "execution_order": self.get_execution_order(graph) if stats["is_dag"] else None,
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {"stop_on_error": True}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return not ("stop_on_error" in config and not isinstance(config["stop_on_error"], bool))
