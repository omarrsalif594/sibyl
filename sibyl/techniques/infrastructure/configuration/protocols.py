"""
Protocol definitions for configuration subtechniques.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigurationProtocol(Protocol):
    """Base protocol for configuration implementations."""

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the configuration operation.

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
class MergeStrategyProtocol(ConfigurationProtocol):
    """Merge Strategy protocol."""


@runtime_checkable
class SchemaValidationProtocol(ConfigurationProtocol):
    """Schema Validation protocol."""
