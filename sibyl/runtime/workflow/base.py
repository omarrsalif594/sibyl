from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class WorkflowStatus(str, Enum):
    """Execution status for a workflow."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowStep:
    """Single step in a workflow definition."""

    name: str
    tool_name: str
    inputs: dict[str, Any]
    condition: Callable[[dict[str, Any]], bool] | None = None
    inputs_from: str | None = None
    on_failure: str | None = None

    def __post_init__(self) -> None:
        self.tool = self.tool_name


@dataclass
class WorkflowResult:
    """Execution result for a workflow."""

    workflow_name: str
    status: WorkflowStatus
    steps_completed: int
    steps_total: int
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    completed_at: Any | None = None


class SibylWorkflow:
    """Base class for defining workflows."""

    name: str
    description: str

    async def pre_workflow(self) -> None:
        """Hook executed before workflow steps start."""
        return

    async def define_steps(self) -> list[WorkflowStep]:
        """Return the list of steps to execute."""
        msg = "define_steps must be implemented by SibylWorkflow subclasses"
        raise NotImplementedError(msg)

    async def post_workflow(self, results: WorkflowResult) -> WorkflowResult:
        """Hook executed after workflow completes."""
        return results


__all__ = ["SibylWorkflow", "WorkflowResult", "WorkflowStatus", "WorkflowStep"]
