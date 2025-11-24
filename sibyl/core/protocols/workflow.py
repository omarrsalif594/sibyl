"""
Workflow protocol interfaces.

This module contains the protocol abstractions for the workflow system.
These are the interfaces that both framework and techniques depend on.

Layering:
    core/protocols/workflow.py (this file) - Protocol definitions
    ├─> framework/workflow/* - Concrete implementations
    └─> techniques/*/workflows/* - Domain-specific workflows

Key protocols:
- IWorkflow: Base workflow interface
- IWorkflowEngine: Workflow execution engine interface
- IWorkflowStep: Workflow step interface
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IWorkflow(Protocol):
    """Protocol for workflow interface.

    Workflows define a sequence of steps to accomplish a task.
    """

    @property
    def name(self) -> str:
        """Unique workflow identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    async def define_steps(self) -> list[Any]:
        """Define the workflow steps.

        Returns:
            List of workflow steps
        """
        ...

    async def pre_workflow(self) -> None:
        """Hook called before workflow execution.

        Use this for setup, validation, etc.
        """
        ...

    async def post_workflow(self, result: Any) -> Any:
        """Hook called after workflow execution.

        Args:
            result: Workflow result

        Returns:
            Modified result
        """
        ...


@runtime_checkable
class IWorkflowEngine(Protocol):
    """Protocol for workflow engine.

    The workflow engine executes workflows and manages their lifecycle.
    """

    def register(self, workflow: IWorkflow) -> None:
        """Register a workflow.

        Args:
            workflow: Workflow instance to register
        """
        ...

    def get(self, name: str) -> IWorkflow | None:
        """Get workflow by name.

        Args:
            name: Workflow name

        Returns:
            Workflow instance or None
        """
        ...

    def get_all(self) -> list[IWorkflow]:
        """Get all registered workflows.

        Returns:
            List of workflows
        """
        ...

    async def execute(self, workflow_name: str, initial_inputs: dict[str, Any]) -> Any:
        """Execute a workflow.

        Args:
            workflow_name: Name of workflow to execute
            initial_inputs: Initial inputs to workflow

        Returns:
            Workflow result
        """
        ...


__all__ = [
    "IWorkflow",
    "IWorkflowEngine",
]
