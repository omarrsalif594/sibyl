"""Dry-run mode for debugging pipelines.

This module provides dry-run capabilities to show planned execution
without actually running steps.

Example:
    from sibyl.core.observability import DryRunPlanner
    from sibyl.workspace import load_workspace

    workspace = load_workspace("config/workspaces/example.yaml")
    planner = DryRunPlanner(workspace)

    # Plan execution
    plan = planner.plan_pipeline("my_pipeline", query="test")

    # Show plan
    print(plan.to_string())
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sibyl.workspace.schema import PipelineStepConfig, WorkspaceSettings

logger = logging.getLogger(__name__)


@dataclass
class PlannedStep:
    """Planned step execution.

    Attributes:
        index: Step index
        name: Step name
        step_type: Type (technique or mcp)
        shop: Shop name
        technique: Technique name (if applicable)
        provider: MCP provider (if applicable)
        tool: MCP tool (if applicable)
        params: Resolved parameters
        condition: Conditional expression (if any)
        will_execute: Whether step will execute (based on dry-run condition evaluation)
        notes: Additional notes
    """

    index: int
    name: str
    step_type: str
    shop: str
    technique: str | None = None
    provider: str | None = None
    tool: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    will_execute: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "step_type": self.step_type,
            "shop": self.shop,
            "technique": self.technique,
            "provider": self.provider,
            "tool": self.tool,
            "params": self.params,
            "condition": self.condition,
            "will_execute": self.will_execute,
            "notes": self.notes,
        }


@dataclass
class ExecutionPlan:
    """Execution plan for a pipeline.

    Attributes:
        pipeline_name: Name of the pipeline
        input_params: Input parameters
        steps: List of planned steps
        warnings: List of warnings
        total_steps: Total number of steps
        steps_to_execute: Number of steps that will execute
    """

    pipeline_name: str
    input_params: dict[str, Any]
    steps: list[PlannedStep]
    warnings: list[str] = field(default_factory=list)
    total_steps: int = 0
    steps_to_execute: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "input_params": self.input_params,
            "steps": [s.to_dict() for s in self.steps],
            "warnings": self.warnings,
            "total_steps": self.total_steps,
            "steps_to_execute": self.steps_to_execute,
        }

    def to_string(self) -> str:
        """Format as human-readable string."""
        lines = []
        lines.append(f"Execution Plan: {self.pipeline_name}")
        lines.append(f"Input Parameters: {self.input_params}")
        lines.append(f"Total Steps: {self.total_steps}")
        lines.append(f"Steps to Execute: {self.steps_to_execute}")
        lines.append("")

        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        lines.append("Planned Steps:")
        for step in self.steps:
            status = "✓" if step.will_execute else "⊘"
            lines.append(f"  {status} Step {step.index}: {step.name}")
            lines.append(f"      Type: {step.step_type}")

            if step.technique:
                lines.append(f"      Technique: {step.shop}.{step.technique}")
            elif step.provider and step.tool:
                lines.append(f"      MCP: {step.provider}/{step.tool}")

            if step.params:
                lines.append(f"      Params: {step.params}")

            if step.condition:
                lines.append(f"      Condition: {step.condition}")

            if step.notes:
                for note in step.notes:
                    lines.append(f"      Note: {note}")

            lines.append("")

        return "\n".join(lines)


class DryRunPlanner:
    """Planner for dry-run execution.

    This class analyzes pipeline configurations and produces execution plans
    without actually running steps.

    Attributes:
        workspace: Workspace configuration
    """

    def __init__(self, workspace: WorkspaceSettings) -> None:
        """Initialize dry-run planner.

        Args:
            workspace: Workspace configuration
        """
        self.workspace = workspace

    def plan_pipeline(self, pipeline_name: str, **input_params: Any) -> ExecutionPlan:
        """Plan pipeline execution.

        Args:
            pipeline_name: Name of pipeline to plan
            **input_params: Input parameters

        Returns:
            ExecutionPlan with planned steps

        Raises:
            ValueError: If pipeline not found
        """
        if pipeline_name not in self.workspace.pipelines:
            msg = f"Pipeline '{pipeline_name}' not found"
            raise ValueError(msg)

        pipeline = self.workspace.pipelines[pipeline_name]
        planned_steps: list[PlannedStep] = []
        warnings: list[str] = []

        # Plan each step
        for i, step in enumerate(pipeline.steps):
            planned_step = self._plan_step(step, i, input_params, warnings)
            planned_steps.append(planned_step)

        # Count steps that will execute
        steps_to_execute = sum(1 for s in planned_steps if s.will_execute)

        return ExecutionPlan(
            pipeline_name=pipeline_name,
            input_params=input_params,
            steps=planned_steps,
            warnings=warnings,
            total_steps=len(planned_steps),
            steps_to_execute=steps_to_execute,
        )

    def _plan_step(
        self,
        step: PipelineStepConfig,
        index: int,
        input_params: dict[str, Any],
        warnings: list[str],
    ) -> PlannedStep:
        """Plan a single step.

        Args:
            step: Step configuration
            index: Step index
            input_params: Input parameters
            warnings: List to append warnings to

        Returns:
            PlannedStep
        """
        notes: list[str] = []

        # Check if this is an MCP step
        is_mcp_step = step.shop == "mcp"

        if is_mcp_step:
            name = f"mcp.{step.provider}.{step.tool}"
            step_type = "mcp"

            # Check provider exists
            if step.provider not in self.workspace.providers.mcp:
                warnings.append(f"Step {index}: Provider '{step.provider}' not found")
                notes.append("Provider not found")

            planned = PlannedStep(
                index=index,
                name=name,
                step_type=step_type,
                shop="mcp",
                provider=step.provider,
                tool=step.tool,
                params=step.params or {},
                condition=step.condition,
                will_execute=not step.condition,  # Simplified: conditions assumed false
                notes=notes,
            )
        else:
            # Technique step
            name = step.use
            step_type = "technique"

            # Parse reference
            if "." in step.use:
                shop_name, technique_name = step.use.split(".", 1)

                # Check shop exists
                if shop_name not in self.workspace.shops:
                    warnings.append(f"Step {index}: Shop '{shop_name}' not found")
                    notes.append("Shop not found")
                else:
                    # Check technique exists
                    shop = self.workspace.shops[shop_name]
                    if technique_name not in shop.techniques:
                        warnings.append(
                            f"Step {index}: Technique '{technique_name}' not found in shop '{shop_name}'"
                        )
                        notes.append("Technique not found")

                planned = PlannedStep(
                    index=index,
                    name=name,
                    step_type=step_type,
                    shop=shop_name,
                    technique=technique_name,
                    params=step.config or {},
                    condition=step.condition,
                    will_execute=not step.condition,
                    notes=notes,
                )
            else:
                warnings.append(f"Step {index}: Invalid step reference '{step.use}'")
                notes.append("Invalid step reference")

                planned = PlannedStep(
                    index=index,
                    name=name,
                    step_type="unknown",
                    shop="unknown",
                    params={},
                    will_execute=False,
                    notes=notes,
                )

        return planned
