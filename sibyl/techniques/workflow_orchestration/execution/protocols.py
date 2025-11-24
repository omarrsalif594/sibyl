"""
Protocol definitions for execution subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExecutionProtocol(Protocol):
    """Base protocol for execution implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the execution operation.

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
class TaskExecutorProtocol(ExecutionProtocol):
    """Task Executor protocol."""
