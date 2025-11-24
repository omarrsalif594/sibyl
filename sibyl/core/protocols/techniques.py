"""
Technique protocol interfaces.

This module contains the protocol abstractions for the technique system.
These are the interfaces that define the hyper-modular architecture.

Layering:
    core/protocols/techniques.py (this file) - Protocol definitions
    ├─> framework/techniques/* - Technique framework
    └─> techniques/* - Domain-specific techniques

Key protocols:
- BaseTechnique: Base technique interface
- BaseSubtechnique: Base subtechnique interface
- TechniqueConfig: Configuration container
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class TechniqueConfig:
    """
    Configuration container for techniques and subtechniques.

    Attributes:
        global_config: Global configuration settings
        technique_config: Technique-level configuration
        subtechnique_config: Subtechnique-level configuration
    """

    global_config: dict[str, Any]
    technique_config: dict[str, Any]
    subtechnique_config: dict[str, Any]


@runtime_checkable
class BaseSubtechnique(Protocol):
    """
    Base protocol for all subtechniques.

    Each subtechnique must implement:
    - name: Unique identifier for the subtechnique
    - execute: Core logic for the subtechnique
    - get_config: Retrieve subtechnique configuration
    - validate_config: Validate configuration before execution
    """

    @property
    def name(self) -> str:
        """
        Get the name of the subtechnique.

        Returns:
            Unique identifier for this subtechnique
        """
        ...

    @property
    def description(self) -> str:
        """
        Get a description of what this subtechnique does.

        Returns:
            Human-readable description
        """
        ...

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Execute the subtechnique with given input and configuration.

        Args:
            input_data: Input data for processing
            config: Merged configuration from cascade

        Returns:
            Processed output

        Raises:
            ValueError: If input_data is invalid
            RuntimeError: If execution fails
        """
        ...

    def get_config(self) -> dict[str, Any]:
        """
        Get the default configuration for this subtechnique.

        Returns:
            Default configuration dictionary
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate that the configuration is valid for this subtechnique.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises exception otherwise

        Raises:
            ValueError: If configuration is invalid
        """
        ...


@runtime_checkable
class BaseTechnique(Protocol):
    """
    Base protocol for all techniques.

    Each technique must implement:
    - name: Unique identifier for the technique
    - subtechniques: Registry of available subtechniques
    - execute: Orchestrate subtechnique execution
    - get_config: Retrieve technique configuration
    - load_config: Load configuration from file
    """

    @property
    def name(self) -> str:
        """
        Get the name of the technique.

        Returns:
            Unique identifier for this technique
        """
        ...

    @property
    def description(self) -> str:
        """
        Get a description of what this technique does.

        Returns:
            Human-readable description
        """
        ...

    @property
    def subtechniques(self) -> dict[str, BaseSubtechnique]:
        """
        Get all registered subtechniques for this technique.

        Returns:
            Dictionary mapping subtechnique names to implementations
        """
        ...

    def execute(
        self, input_data: Any, subtechnique: str, config: dict[str, Any], **kwargs: Any
    ) -> Any:
        """
        Execute a specific subtechnique with given configuration.

        Args:
            input_data: Input data for processing
            subtechnique: Name of subtechnique to use
            config: Configuration overrides
            **kwargs: Additional keyword arguments

        Returns:
            Processed output from subtechnique

        Raises:
            ValueError: If subtechnique is not found or invalid
            RuntimeError: If execution fails
        """
        ...

    def get_config(self) -> dict[str, Any]:
        """
        Get the default configuration for this technique.

        Returns:
            Default configuration dictionary
        """
        ...

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Loaded configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        ...

    def register_subtechnique(self, subtechnique: BaseSubtechnique) -> None:
        """
        Register a new subtechnique with this technique.

        Args:
            subtechnique: Subtechnique implementation to register

        Raises:
            ValueError: If subtechnique with same name already exists
        """
        ...

    def list_subtechniques(self) -> list[str]:
        """
        List all available subtechnique names.

        Returns:
            List of subtechnique names
        """
        ...


__all__ = [
    "BaseSubtechnique",
    "BaseTechnique",
    "TechniqueConfig",
]
