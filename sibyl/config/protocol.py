"""Configuration source protocol and types.

This module defines the protocol for configuration sources and related types.

Example:
    from sibyl.mcp_server.infrastructure.config import ConfigSource, ConfigValue

    class CustomConfigSource:
        '''Custom config source implementation.'''

        name = "custom"
        priority = 60

        def load(self) -> dict[str, ConfigValue]:
            return {
                "setting1": ConfigValue(value="value1", source="custom", priority=60),
                "setting2": ConfigValue(value=123, source="custom", priority=60),
            }

        def get(self, key: str) -> ConfigValue | None:
            config = self.load()
            return config.get(key)
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigValue:
    """A configuration value with metadata.

    Attributes:
        value: The actual configuration value
        source: Name of the config source that provided this value
        priority: Priority of the source (higher = more important)
        path: Dot-separated path to this value (e.g., "database.timeout")
    """

    value: Any
    source: str
    priority: int
    path: str | None = None

    def __repr__(self) -> str:
        """String representation of config value."""
        return f"ConfigValue(value={self.value!r}, source={self.source}, priority={self.priority})"


@runtime_checkable
class ConfigSource(Protocol):
    """Protocol for configuration sources.

    A config source provides configuration values from a specific source
    (e.g., YAML file, environment variables, CLI arguments).

    Attributes:
        name: Unique name for this config source
        priority: Priority of this source (higher = more important)

    Priority conventions:
        0-19: Default values
        20-49: Config file values
        50-79: Environment variables
        80-99: CLI arguments
        100+: Programmatic overrides
    """

    name: str
    priority: int

    def load(self) -> dict[str, ConfigValue]:
        """Load all configuration values from this source.

        Returns:
            Dictionary mapping config keys to ConfigValue objects

        Raises:
            ConfigLoadError: If configuration cannot be loaded
        """
        ...

    def get(self, key: str) -> Optional["ConfigValue"]:
        """Get a specific configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)

        Returns:
            ConfigValue or None if key not found
        """
        ...


class ConfigLoadError(Exception):
    """Exception raised when configuration cannot be loaded."""


class ConfigMergeError(Exception):
    """Exception raised when configuration merge fails."""
