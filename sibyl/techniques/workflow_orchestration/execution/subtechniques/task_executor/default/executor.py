"""
Executor Agent - Executes planned tasks using tools.

This agent:
- Takes execution plans from PlannerAgent
- Executes tools in sequence
- Runs QC checks via plugins
- Handles errors and retries
- No domain-specific logic
"""

import logging
from typing import Any

from sibyl.agents.base.agent import BaseAgent
from sibyl.agents.types import AgentRequestPayload, AgentResponsePayload

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """
    Generic execution agent that runs planned tasks.

    Uses plugin system for all domain-specific logic (QC, validation, etc.)
    """

    def __init__(self, tool_executor: Any, plugin_registry: Any = None, **kwargs) -> None:
        """
        Initialize executor agent.

        Args:
            tool_executor: Tool execution service
            plugin_registry: Plugin registry for QC/validation
            **kwargs: Base agent parameters
        """
        super().__init__(agent_id="executor", **kwargs)
        self.tool_executor = tool_executor
        self.plugin_registry = plugin_registry
        logger.info("Executor agent initialized")

    async def execute(self, request: AgentRequestPayload) -> AgentResponsePayload:
        """
        Execute a plan.

        Args:
            request: {
                "plan": [list of steps from planner],
                "run_qc": whether to run quality checks,
                "context": execution context
            }

        Returns:
            {
                "results": [results for each step],
                "qc_results": quality check results,
                "status": "success" | "partial" | "failed",
                "errors": any errors encountered
            }
        """
        plan = request.get("plan", [])
        run_qc = request.get("run_qc", True)
        context = request.get("context", {})

        logger.info("Executing plan with %s steps", len(plan))

        results = []
        errors = []

        # Execute each step
        for step in plan:
            try:
                result = await self._execute_step(step, context)
                results.append({"step": step.get("step", 0), "status": "success", "result": result})

                # Run QC if requested
                if run_qc and result.get("resource_id"):
                    qc_result = await self._run_qc_checks(result["resource_id"])
                    result["qc"] = qc_result

            except Exception as e:
                logger.exception("Step %s failed: %s", step.get("step"), e)
                errors.append({"step": step.get("step", 0), "error": str(e)})
                results.append({"step": step.get("step", 0), "status": "failed", "error": str(e)})

        # Determine overall status
        status = self._determine_status(results)

        return {
            "results": results,
            "status": status,
            "errors": errors,
            "steps_completed": len([r for r in results if r["status"] == "success"]),
            "steps_total": len(plan),
        }

    async def _execute_step(self, step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a single step.

        Args:
            step: Step definition
            context: Execution context

        Returns:
            Step result
        """
        tool_name = step.get("tool")
        params = step.get("params", {})

        if not tool_name:
            msg = "Step missing tool name"
            raise ValueError(msg)

        logger.debug("Executing tool: %s", tool_name)

        # Execute tool via tool executor
        return await self.tool_executor.execute(tool_name=tool_name, params=params, context=context)

    async def _run_qc_checks(self, resource_id: str) -> dict[str, Any]:
        """
        Run quality control checks via plugins.

        Args:
            resource_id: Resource to check

        Returns:
            QC results
        """
        if not self.plugin_registry:
            return {"status": "skipped", "reason": "no_plugins"}

        try:
            # Get validators from plugin registry
            validators = self.plugin_registry.get_validators()

            results = []
            for validator in validators:
                try:
                    result = await validator.validate(resource_id)
                    results.append({"validator": validator.__class__.__name__, "result": result})
                except Exception as e:
                    logger.exception("Validator %s failed: %s", validator, e)
                    results.append({"validator": validator.__class__.__name__, "error": str(e)})

            return {
                "status": "completed",
                "checks": results,
                "passed": all(r.get("result", {}).get("valid", False) for r in results),
            }

        except Exception as e:
            logger.exception("QC checks failed: %s", e)
            return {"status": "error", "error": str(e)}

    def _determine_status(self, results: list[dict[str, Any]]) -> str:
        """
        Determine overall execution status.

        Args:
            results: List of step results

        Returns:
            Status string
        """
        if not results:
            return "failed"

        success_count = len([r for r in results if r["status"] == "success"])

        if success_count == len(results):
            return "success"
        if success_count > 0:
            return "partial"
        return "failed"
