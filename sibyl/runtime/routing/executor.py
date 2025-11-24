"""
Route Executor - Executes routing decisions.

This module provides the RouteExecutor that takes a RouteDecision and executes
it by dispatching to the appropriate target (Sibyl pipeline, remote LLM, or
local specialist).
"""

import logging
from typing import Any, Optional

from plugins.claude_code_router.router_types import RouteDecision, RouteRequest

logger = logging.getLogger(__name__)


class RouteExecutor:
    """
    Executes routing decisions by dispatching to the appropriate target.

    This executor handles:
    - sibyl_pipeline: Execute via sibyl_runner
    - remote_llm: Execute via LLM provider (future)
    - local_specialist: Execute via specialist registry
    - noop: Do nothing
    """

    def __init__(
        self,
        specialist_registry: Optional["SpecialistRegistry"] = None,
    ) -> None:
        """
        Initialize RouteExecutor.

        Args:
            specialist_registry: Optional specialist registry for local specialists
        """
        self.specialist_registry = specialist_registry

    def execute(
        self,
        decision: RouteDecision,
        request: RouteRequest,
    ) -> dict[str, Any]:
        """
        Execute a routing decision.

        Args:
            decision: The routing decision to execute
            request: The original routing request

        Returns:
            Execution result dictionary with status, data, and metadata

        Raises:
            ValueError: If target type is not supported
        """
        logger.info("Executing route decision: target=%s", decision.target)

        # Dispatch based on target type
        if decision.target == "sibyl_pipeline":
            return self._execute_sibyl_pipeline(decision, request)

        if decision.target == "remote_llm":
            return self._execute_remote_llm(decision, request)

        if decision.target == "local_specialist":
            return self._execute_local_specialist(decision, request)

        if decision.target == "noop":
            return self._execute_noop(decision, request)

        msg = f"Unsupported routing target: {decision.target}"
        raise ValueError(msg)

    def _execute_sibyl_pipeline(
        self,
        decision: RouteDecision,
        request: RouteRequest,
    ) -> dict[str, Any]:
        """
        Execute a Sibyl pipeline routing decision.

        Args:
            decision: Routing decision with workspace and pipeline info
            request: Original routing request with question

        Returns:
            Pipeline execution result
        """
        from plugins.common.sibyl_runner import run_pipeline

        if not decision.workspace:
            return {
                "status": "error",
                "error": "Sibyl pipeline target requires workspace path",
            }

        if not decision.pipeline:
            return {
                "status": "error",
                "error": "Sibyl pipeline target requires pipeline name",
            }

        logger.info(
            f"Executing Sibyl pipeline: workspace={decision.workspace}, "
            f"pipeline={decision.pipeline}"
        )

        # Merge request context with decision params
        params = decision.params or {}
        params["question"] = request.question

        # Add context if provided
        if request.context:
            params.update(request.context)

        # Execute via sibyl_runner
        try:
            return run_pipeline(
                workspace_yaml=decision.workspace,
                pipeline_name=decision.pipeline,
                params=params,
            )

        except Exception as e:
            logger.exception("Sibyl pipeline execution failed: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "target": "sibyl_pipeline",
                "workspace": decision.workspace,
                "pipeline": decision.pipeline,
            }

    def _execute_remote_llm(
        self,
        decision: RouteDecision,
        request: RouteRequest,
    ) -> dict[str, Any]:
        """
        Execute a remote LLM routing decision.

        Args:
            decision: Routing decision with LLM params
            request: Original routing request with question

        Returns:
            LLM execution result
        """
        # Future: integrate with LLM providers
        logger.warning("remote_llm target not yet implemented")

        return {
            "status": "error",
            "error": "remote_llm target not yet implemented",
            "target": "remote_llm",
        }

    def _execute_local_specialist(
        self,
        decision: RouteDecision,
        request: RouteRequest,
    ) -> dict[str, Any]:
        """
        Execute a local specialist routing decision.

        Args:
            decision: Routing decision with specialist_id
            request: Original routing request with question

        Returns:
            Specialist execution result
        """
        if not self.specialist_registry:
            return {
                "status": "error",
                "error": "No specialist registry configured",
                "target": "local_specialist",
            }

        if not decision.specialist_id:
            return {
                "status": "error",
                "error": "local_specialist target requires specialist_id",
                "target": "local_specialist",
            }

        logger.info("Executing local specialist: %s", decision.specialist_id)

        try:
            specialist = self.specialist_registry.get_specialist(decision.specialist_id)

            if not specialist:
                return {
                    "status": "error",
                    "error": f"Specialist not found: {decision.specialist_id}",
                    "target": "local_specialist",
                }

            # Execute specialist
            params = decision.params or {}
            result = specialist.generate(prompt=request.question, **params)

            return {
                "status": "success",
                "data": result,
                "target": "local_specialist",
                "specialist_id": decision.specialist_id,
            }

        except Exception as e:
            logger.exception("Specialist execution failed: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "target": "local_specialist",
                "specialist_id": decision.specialist_id,
            }

    def _execute_noop(
        self,
        decision: RouteDecision,
        request: RouteRequest,
    ) -> dict[str, Any]:
        """
        Execute a no-op routing decision.

        Args:
            decision: Routing decision
            request: Original routing request

        Returns:
            No-op result
        """
        logger.info("Executing noop route (no action taken)")

        return {
            "status": "success",
            "data": None,
            "target": "noop",
            "message": "No routing action taken",
        }
