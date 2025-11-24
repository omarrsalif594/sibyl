"""
Orchestration Technique - Workflow orchestration and execution.

Provides multiple execution models, parallelism strategies, and routing approaches
through a pluggable subtechnique architecture.
"""

import logging
from pathlib import Path
from typing import Any

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability_async
from sibyl.techniques.protocols import BaseTechnique

from .subtechniques.execution_model.default.dag_based import DagBasedImplementation
from .subtechniques.execution_model.default.sequential import SequentialImplementation

# Import execution models
from .subtechniques.execution_model.default.wave_based import WaveBasedImplementation

logger = logging.getLogger(__name__)


class OrchestrationTechnique(BaseTechnique):
    """Workflow orchestration and execution technique.

    Provides multiple execution models:
    - wave_based: Parallel execution in dependency waves
    - sequential: Simple sequential execution
    - dag_based: Topological order execution

    Provides parallelism strategies:
    - semaphore: Semaphore-based concurrency limiting
    - thread_pool: Thread pool executor
    - process_pool: Process pool executor

    Provides routing strategies:
    - expert_routing: Route to specialized experts
    - round_robin: Simple round-robin distribution
    - load_balanced: Load-aware routing
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "orchestration"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, Any] = {}
        self._register_default_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def subtechniques(self) -> dict[str, Any]:
        return self._subtechniques

    def _register_default_subtechniques(self) -> None:
        """Register default execution model subtechniques."""
        # Execution models
        self.register_subtechnique(WaveBasedImplementation(), "execution_model", "wave_based")
        self.register_subtechnique(SequentialImplementation(), "execution_model", "sequential")
        self.register_subtechnique(DagBasedImplementation(), "execution_model", "dag_based")

        logger.info("Registered %s default orchestration subtechniques", len(self._subtechniques))

    def register_subtechnique(
        self, subtechnique: Any, category: str = "execution_model", implementation: str = "default"
    ) -> None:
        """Register a subtechnique implementation.

        Args:
            subtechnique: Subtechnique instance
            category: Category (execution_model, parallelism, routing)
            implementation: Implementation name (default, provider, custom)
        """
        key = f"{category}:{subtechnique.name}:{implementation}"
        self._subtechniques[key] = subtechnique
        logger.debug("Registered subtechnique: %s", key)

    async def execute(
        self,
        input_data: Any,
        subtechnique: str = "wave_based",
        category: str = "execution_model",
        implementation: str = "default",
        config: dict | None = None,
        **kwargs,
    ) -> Any:
        """Execute orchestration using specified subtechnique.

        Args:
            input_data: Input data (varies by execution model):
                - For wave_based/dag_based: Dict with graph, executor_fn, context
                - For sequential: Dict with tasks, executor_fn, context
            subtechnique: Subtechnique name (wave_based, sequential, dag_based)
            category: Category of subtechnique (execution_model, parallelism, routing)
            implementation: Implementation type (default, provider, custom)
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            Result from subtechnique execution

        Example:
            >>> from sibyl.techniques.workflow_orchestration.graph import GenericGraphService
            >>> graph = GenericGraphService()
            >>> graph.add_node("task1", "task", {})
            >>> graph.add_node("task2", "task", {})
            >>> graph.add_edge("task1", "task2", "depends_on", {})
            >>>
            >>> async def executor(node_id, context):
            ...     return {"result": f"Executed {node_id}"}
            >>>
            >>> orchestration = OrchestrationTechnique()
            >>> results = await orchestration.execute(
            ...     input_data={
            ...         "graph": graph,
            ...         "executor_fn": executor,
            ...         "context": {}
            ...     },
            ...     subtechnique="wave_based"
            ... )
        """
        # Build subtechnique key
        key = f"{category}:{subtechnique}:{implementation}"

        if key not in self._subtechniques:
            msg = f"Subtechnique not found: {key}. Available: {list(self._subtechniques.keys())}"
            raise ValueError(msg)

        # Get subtechnique
        impl = self._subtechniques[key]

        # Build configuration cascade
        global_config = config or {}
        technique_config = self._load_technique_config()
        subtechnique_config = impl.get_config()

        cascade = ConfigCascade(
            global_config=global_config,
            technique_config=technique_config,
            subtechnique_config=subtechnique_config,
        )

        # Get merged config
        merged_config = {
            k: cascade.get(k)
            for k in set(
                list(global_config.keys())
                + list(technique_config.keys())
                + list(subtechnique_config.keys())
            )
        }

        # Validate config
        if not impl.validate_config(merged_config):
            msg = f"Invalid configuration for {key}"
            raise ValueError(msg)
        logger.info("Executing orchestration with %s", key)

        async def _do_execute() -> Any:
            return await impl.execute(input_data, merged_config)

        result = await execute_with_observability_async(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=implementation,
            input_data=input_data,
            config=merged_config,
            executor=_do_execute,
            extra_log_fields={"category": category},
        )
        logger.info("Orchestration %s completed successfully", key)
        return result

    def _load_technique_config(self) -> dict[str, Any]:
        """Load technique-level configuration."""
        if self._config_path.exists():
            import yaml  # plugin registration

            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def list_subtechniques(self) -> dict[str, list]:
        """List all registered subtechniques by category.

        Returns:
            Dict mapping category to list of subtechnique names
        """
        categories = {}
        for key in self._subtechniques:
            category, name, impl = key.split(":")
            if category not in categories:
                categories[category] = []
            categories[category].append(f"{name} ({impl})")
        return categories

    def get_subtechnique_info(
        self, subtechnique: str, category: str = "execution_model"
    ) -> dict[str, Any]:
        """Get information about a subtechnique.

        Args:
            subtechnique: Subtechnique name
            category: Category name

        Returns:
            Dict with subtechnique information
        """
        # Find matching keys
        matching = [k for k in self._subtechniques if k.startswith(f"{category}:{subtechnique}:")]
        if not matching:
            return {"error": f"Subtechnique {subtechnique} not found in category {category}"}

        info = {}
        for key in matching:
            impl = self._subtechniques[key]
            _, _, impl_type = key.split(":")
            info[impl_type] = {
                "name": impl.name,
                "description": impl.description if hasattr(impl, "description") else "",
                "default_config": impl.get_config(),
            }

        return info
