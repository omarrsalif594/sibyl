"""
Protocol definitions for planning subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlanningProtocol(Protocol):
    """Base protocol for planning implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the planning operation.

        Args:
            input_data: Input data to process
            config: Configuration parameters

        Returns:
            Processed result
        """
        ...

    @property
    def name(self) -> str:
        """Get implementation name."""
        ...

    @property
    def description(self) -> str:
        """Get implementation description."""
        ...


@runtime_checkable
class HeuristicPlannerProtocol(PlanningProtocol):
    """Heuristic Planner protocol."""
