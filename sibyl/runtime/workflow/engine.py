"""Workflow execution engine.

This module provides the runtime implementation for executing workflows.
The workflow abstractions (SibylWorkflow, WorkflowStep, etc.) are defined
in sibyl.runtime.workflow.base.
"""

from datetime import datetime
from typing import Any

from sibyl.runtime.workflow.base import (
    SibylWorkflow,
    WorkflowResult,
    WorkflowStatus,
)


class WorkflowEngine:
    """Executes workflows.

    This is used by the MCP server to run workflows.
    """

    def __init__(self, tool_executor: Any) -> None:
        """Initialize workflow engine.

        Args:
            tool_executor: Tool executor instance
        """
        self.tool_executor = tool_executor
        self._workflows: dict[str, SibylWorkflow] = {}

    def register(self, workflow: SibylWorkflow) -> None:
        """Register a workflow.

        Args:
            workflow: Workflow instance
        """
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> SibylWorkflow | None:
        """Get workflow by name.

        Args:
            name: Workflow name

        Returns:
            Workflow instance or None
        """
        return self._workflows.get(name)

    def get_all(self) -> list[SibylWorkflow]:
        """Get all registered workflows.

        Returns:
            List of workflows
        """
        return list(self._workflows.values())

    async def execute(self, workflow_name: str, initial_inputs: dict[str, Any]) -> WorkflowResult:
        """Execute a workflow.

        Args:
            workflow_name: Name of workflow to run
            initial_inputs: Initial inputs to workflow

        Returns:
            WorkflowResult with status and results
        """
        workflow = self.get(workflow_name)
        if not workflow:
            return WorkflowResult(
                workflow_name=workflow_name,
                status=WorkflowStatus.FAILED,
                steps_completed=0,
                steps_total=0,
                error=f"Workflow not found: {workflow_name}",
            )

        # Execute workflow
        await workflow.pre_workflow()

        steps = await workflow.define_steps()
        result = WorkflowResult(
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            steps_completed=0,
            steps_total=len(steps),
        )

        try:
            for i, step in enumerate(steps):
                # Check condition
                if step.condition and not step.condition(result.results):
                    continue

                # Execute step
                tool_inputs = step.inputs.copy()

                # Get inputs from previous step if specified
                if step.inputs_from and step.inputs_from in result.results:
                    tool_inputs.update(result.results[step.inputs_from])

                # Execute tool
                step_result = await self.tool_executor.execute(step.tool, **tool_inputs)

                result.results[step.name] = step_result
                result.steps_completed = i + 1

                # Handle failure
                if not step_result.get("success", False):
                    if step.on_failure:
                        # Continue to failure step
                        continue
                    result.status = WorkflowStatus.FAILED
                    result.error = step_result.get("error", "Step failed")
                    break

            # Mark as completed if we finished all steps
            if result.steps_completed == len(steps):
                result.status = WorkflowStatus.COMPLETED

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)

        result.completed_at = datetime.utcnow()

        # Post-workflow hook
        return await workflow.post_workflow(result)


__all__ = ["WorkflowEngine"]
