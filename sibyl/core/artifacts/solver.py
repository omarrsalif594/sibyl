"""Solver Result Artifact for constraint solver outputs.

This module provides typed artifacts for constraint solver results from MCP tools
like MCP Solver, Z3, PySAT, etc. It replaces generic dict outputs with type-safe
structures and domain-specific methods.

Example:
    from sibyl.core.artifacts.solver import SolverResultArtifact, SolverStatus

    # Create from MCP response
    result = SolverResultArtifact.from_mcp_response(
        response={"status": "SATISFIED", "solution": {"x": 5, "y": 10}},
        backend="MiniZinc"
    )

    # Type-safe access
    if result.is_feasible():
        x = result.get_variable("x")
        print(f"Solved in {result.solve_time_ms}ms")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SolverStatus(Enum):
    """Standard solver result statuses.

    These statuses cover the common outcomes from constraint solvers
    like MiniZinc, Z3, PySAT, and others.
    """

    SATISFIED = "SATISFIED"  # Constraint satisfaction problem solved
    UNSATISFIABLE = "UNSATISFIABLE"  # No solution exists
    OPTIMAL = "OPTIMAL"  # Optimization problem solved optimally
    TIMEOUT = "TIMEOUT"  # Solver timed out
    ERROR = "ERROR"  # Solver encountered an error
    UNKNOWN = "UNKNOWN"  # Status could not be determined


@dataclass
class SolverResultArtifact:
    """Artifact for constraint solver results.

    This artifact provides a typed interface to solver outputs, with methods
    for checking feasibility, accessing solution variables, and serialization.

    Attributes:
        status: Solver execution status (SATISFIED, UNSATISFIABLE, etc.)
        solution: Dictionary mapping variable names to their values (if feasible)
        objective_value: Objective function value for optimization problems
        solve_time_ms: Time taken to solve in milliseconds
        backend: Solver backend name (e.g., "MiniZinc", "Z3", "PySAT")
        statistics: Additional solver statistics (iterations, backtracks, etc.)

    Example:
        result = SolverResultArtifact(
            status=SolverStatus.SATISFIED,
            solution={"x": 5, "y": 10},
            objective_value=15.0,
            solve_time_ms=123,
            backend="MiniZinc",
            statistics={"iterations": 42}
        )

        if result.is_feasible():
            print(f"x = {result.get_variable('x')}")
    """

    status: SolverStatus
    solution: dict[str, Any] | None
    objective_value: float | None
    solve_time_ms: int
    backend: str
    statistics: dict[str, int] = field(default_factory=dict)

    def is_feasible(self) -> bool:
        """Check if the problem is feasible (has a solution).

        Returns:
            True if status is SATISFIED or OPTIMAL, False otherwise.

        Example:
            if result.is_feasible():
                solution = result.solution
        """
        return self.status in {SolverStatus.SATISFIED, SolverStatus.OPTIMAL}

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a solution variable value by name.

        Args:
            name: Variable name to retrieve
            default: Default value if variable not found or no solution exists

        Returns:
            Variable value if found, otherwise default value.

        Example:
            x = result.get_variable("x", default=0)
            y = result.get_variable("y")  # Returns None if not found
        """
        if self.solution is None:
            return default
        return self.solution.get(name, default)

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary.

        Returns:
            Dictionary representation of the artifact.

        Example:
            data = result.to_dict()
            json.dumps(data)
        """
        return {
            "status": self.status.value,
            "solution": self.solution,
            "objective_value": self.objective_value,
            "solve_time_ms": self.solve_time_ms,
            "backend": self.backend,
            "statistics": self.statistics,
        }

    @classmethod
    def from_mcp_response(cls, response: dict[str, Any], backend: str) -> "SolverResultArtifact":
        """Create SolverResultArtifact from MCP tool response.

        This factory method handles various response formats from different
        solver backends, normalizing them to a standard artifact structure.

        Args:
            response: Raw response dictionary from MCP solver tool
            backend: Solver backend name (e.g., "MiniZinc", "Z3")

        Returns:
            SolverResultArtifact instance

        Example:
            # From MCP Solver
            mcp_result = await mcp_adapter(tool="solve_model", ...)
            artifact = SolverResultArtifact.from_mcp_response(
                mcp_result,
                backend="MiniZinc"
            )

        Note:
            Status parsing is case-insensitive and handles common variations.
            Unknown statuses default to SolverStatus.UNKNOWN.
        """
        # Parse status (case-insensitive, with fallback)
        status_str = str(response.get("status", "UNKNOWN")).upper()

        # Handle common status variations
        status_mapping = {
            "SATISFIED": SolverStatus.SATISFIED,
            "SAT": SolverStatus.SATISFIED,
            "FEASIBLE": SolverStatus.SATISFIED,
            "UNSATISFIABLE": SolverStatus.UNSATISFIABLE,
            "UNSAT": SolverStatus.UNSATISFIABLE,
            "INFEASIBLE": SolverStatus.UNSATISFIABLE,
            "OPTIMAL": SolverStatus.OPTIMAL,
            "OPTIMUM": SolverStatus.OPTIMAL,
            "TIMEOUT": SolverStatus.TIMEOUT,
            "TIME_LIMIT": SolverStatus.TIMEOUT,
            "ERROR": SolverStatus.ERROR,
            "FAILED": SolverStatus.ERROR,
            "UNKNOWN": SolverStatus.UNKNOWN,
        }

        status = status_mapping.get(status_str, SolverStatus.UNKNOWN)

        # Extract solution (may be None for unsatisfiable problems)
        solution = response.get("solution")

        # Extract objective value (may be None for satisfaction problems)
        objective_value = response.get("objective_value")
        if objective_value is not None:
            try:
                objective_value = float(objective_value)
            except (TypeError, ValueError):
                objective_value = None

        # Extract solve time (default to 0 if not present)
        solve_time_ms = int(response.get("solve_time_ms", 0))

        # Extract statistics (may be empty dict)
        statistics = response.get("statistics", {})
        if not isinstance(statistics, dict):
            statistics = {}

        # Convert statistics values to int where possible
        normalized_statistics: dict[str, int] = {}
        for key, value in statistics.items():
            try:
                normalized_statistics[key] = int(value)
            except (TypeError, ValueError):
                # Skip non-integer statistics
                pass

        return cls(
            status=status,
            solution=solution,
            objective_value=objective_value,
            solve_time_ms=solve_time_ms,
            backend=backend,
            statistics=normalized_statistics,
        )
