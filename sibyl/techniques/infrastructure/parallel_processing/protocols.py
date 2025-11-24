"""
Protocol definitions for parallel_processing subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ParallelProcessingProtocol(Protocol):
    """Base protocol for parallel_processing implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the parallel_processing operation.

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
class MultiprocessBatchProtocol(ParallelProcessingProtocol):
    """Multiprocess Batch protocol."""
