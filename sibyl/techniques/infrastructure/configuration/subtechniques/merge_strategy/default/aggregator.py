"""Configuration aggregator for merging multiple sources.

This module provides ConfigAggregator for priority-based config merging.

Example:
    from sibyl.mcp_server.infrastructure.config import (
        ConfigAggregator,
        YAMLConfigSource,
        EnvVarConfigSource,
    )

    # Create aggregator
    aggregator = ConfigAggregator()

    # Add sources (order doesn't matter - priority determines precedence)
    aggregator.add_source(YAMLConfigSource("config.yml"))  # priority 50
    aggregator.add_source(EnvVarConfigSource(prefix="APP_"))  # priority 80

    # Get merged config
    config = aggregator.get_config()

    # Access values
    max_workers = config.get("max_workers", default=4)
    # If both sources have "max_workers", env var wins (higher priority)
"""

import logging
from typing import Any

from sibyl.config.protocol import (
    ConfigMergeError,
    ConfigSource,
    ConfigValue,
)

logger = logging.getLogger(__name__)

__all__ = ["ConfigAggregator", "MergedConfig"]


class ConfigAggregator:
    """Aggregates configuration from multiple sources with priority-based merging.

    Sources are merged by priority: higher priority values override lower priority ones.

    Example:
        aggregator = ConfigAggregator()
        aggregator.add_source(YAMLConfigSource("config.yml"))  # priority 50
        aggregator.add_source(EnvVarConfigSource())  # priority 80

        config = aggregator.get_config()
        max_workers = config.get("max_workers", default=4)
    """

    def __init__(self) -> None:
        """Initialize config aggregator."""
        self._sources: list[ConfigSource] = []
        self._cached_config: dict[str, ConfigValue] | None = None

    def add_source(self, source: ConfigSource) -> None:
        """Add a configuration source.

        Args:
            source: ConfigSource implementation
        """
        self._sources.append(source)
        # Invalidate cache
        self._cached_config = None

        logger.debug("Added config source: %s (priority %s)", source.name, source.priority)

    def remove_source(self, source_name: str) -> None:
        """Remove a configuration source by name.

        Args:
            source_name: Name of source to remove
        """
        self._sources = [s for s in self._sources if s.name != source_name]
        self._cached_config = None

        logger.debug("Removed config source: %s", source_name)

    def get_config(self) -> "MergedConfig":
        """Get merged configuration from all sources.

        Returns:
            MergedConfig object with all merged values

        Raises:
            ConfigMergeError: If config merge fails
        """
        if self._cached_config is not None:
            return MergedConfig(self._cached_config)

        # Load all sources
        all_configs = {}

        for source in self._sources:
            try:
                source_config = source.load()
                logger.debug("Loaded %s config values from %s", len(source_config), source.name)

                # Merge with priority-based resolution
                for key, value in source_config.items():
                    if key not in all_configs:
                        # New key - add it
                        all_configs[key] = value
                    else:
                        # Key exists - check priority
                        existing = all_configs[key]
                        if value.priority > existing.priority:
                            # Higher priority - replace
                            logger.debug(
                                f"Config key '{key}': {source.name} (priority {value.priority}) "
                                f"overrides {existing.source} (priority {existing.priority})"
                            )
                            all_configs[key] = value
                        elif value.priority == existing.priority:
                            # Same priority - warn and keep first
                            logger.warning(
                                f"Config key '{key}' has same priority ({value.priority}) "
                                f"in {source.name} and {existing.source}. Keeping {existing.source}."
                            )

            except Exception as e:
                logger.exception("Failed to load config from %s: %s", source.name, e)
                msg = f"Failed to merge config from {source.name}"
                raise ConfigMergeError(msg) from e

        # Cache merged config
        self._cached_config = all_configs

        logger.info(
            f"Merged config from {len(self._sources)} sources: {len(all_configs)} total values"
        )

        return MergedConfig(all_configs)

    def get_sources(self) -> list[ConfigSource]:
        """Get list of all config sources.

        Returns:
            List of ConfigSource objects
        """
        return list(self._sources)

    def clear_cache(self) -> None:
        """Clear cached config to force reload."""
        self._cached_config = None
        logger.debug("Cleared config cache")


class MergedConfig:
    """Merged configuration from multiple sources.

    Provides convenient access to config values with type conversion
    and default values.
    """

    def __init__(self, config: dict[str, ConfigValue]) -> None:
        """Initialize merged config.

        Args:
            config: Dictionary of merged ConfigValue objects
        """
        self._config = config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Handle nested keys (e.g., "database.host")
        if "." in key:
            return self._get_nested(key, default)

        # Simple key lookup
        config_value = self._config.get(key)
        if config_value is None:
            return default

        return config_value.value

    def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer.

        Args:
            key: Configuration key
            default: Default value if key not found or conversion fails

        Returns:
            Integer value or default
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(
                "Failed to convert config '%s' value '%s' to int, using default %s",
                key,
                value,
                default,
            )
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get configuration value as float.

        Args:
            key: Configuration key
            default: Default value if key not found or conversion fails

        Returns:
            Float value or default
        """
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(
                "Failed to convert config '%s' value '%s' to float, using default %s",
                key,
                value,
                default,
            )
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean.

        Args:
            key: Configuration key
            default: Default value if key not found or conversion fails

        Returns:
            Boolean value or default
        """
        value = self.get(key, default)

        if isinstance(value, bool):
            return value

        # Convert string to bool
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ("true", "yes", "1", "on"):
                return True
            if value_lower in ("false", "no", "0", "off"):
                return False

        logger.warning(
            "Failed to convert config '%s' value '%s' to bool, using default %s",
            key,
            value,
            default,
        )
        return default

    def get_list(self, key: str, default: list | None = None) -> list:
        """Get configuration value as list.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            List value or default
        """
        value = self.get(key, default or [])

        if isinstance(value, list):
            return value

        # Convert comma-separated string to list
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]

        logger.warning(
            "Failed to convert config '%s' value '%s' to list, using default %s",
            key,
            value,
            default or [],
        )
        return default or []

    def has(self, key: str) -> bool:
        """Check if configuration key exists.

        Args:
            key: Configuration key

        Returns:
            True if key exists
        """
        if "." in key:
            try:
                self._get_nested(key, None)
                return True
            except KeyError:
                return False

        return key in self._config

    def get_source(self, key: str) -> str | None:
        """Get the source that provided a configuration value.

        Args:
            key: Configuration key

        Returns:
            Source name or None if key not found
        """
        config_value = self._config.get(key)
        if config_value is None:
            return None

        return config_value.source

    def get_all(self) -> dict[str, Any]:
        """Get all configuration values.

        Returns:
            Dictionary mapping keys to values
        """
        return {key: value.value for key, value in self._config.items()}

    def get_all_with_metadata(self) -> dict[str, ConfigValue]:
        """Get all configuration values with metadata.

        Returns:
            Dictionary mapping keys to ConfigValue objects
        """
        return dict(self._config)

    def _get_nested(self, key: str, default: Any) -> Any:
        """Get nested configuration value using dot notation.

        Args:
            key: Nested key (e.g., "database.host")
            default: Default value if key not found

        Returns:
            Nested value or default
        """
        parts = key.split(".")
        current = self._config

        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    config_value = current[part]
                    # If it's a ConfigValue, get the actual value
                    if isinstance(config_value, ConfigValue):
                        current = config_value.value
                    else:
                        current = config_value
                else:
                    return default
            else:
                return default

        return current
