"""Concrete configuration source implementations.

This module provides implementations of ConfigSource for various sources:
- YAMLConfigSource: Load from YAML files
- EnvVarConfigSource: Load from environment variables
- CLIArgsConfigSource: Load from command-line arguments
- DictConfigSource: Load from Python dictionary (for defaults/testing)

Example:
    # YAML file config
    yaml_source = YAMLConfigSource("config.yml", priority=50)

    # Environment variables with prefix (framework config)
    env_source = EnvVarConfigSource(prefix="SIBYL_", priority=80)

    # Environment variables for application-specific config
    app_env_source = EnvVarConfigSource(prefix="ExampleDomain_", priority=80)

    # CLI arguments
    cli_source = CLIArgsConfigSource(sys.argv, priority=100)

    # Default values
    defaults = DictConfigSource({"max_workers": 4, "timeout": 300}, name="defaults", priority=10)
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from sibyl.mcp_server.infrastructure.config.protocol import (
    ConfigLoadError,
    ConfigValue,
)

logger = logging.getLogger(__name__)


class YAMLConfigSource:
    """Configuration source that loads from YAML file.

    Example:
        source = YAMLConfigSource("config.yml", priority=50)
        config = source.load()
    """

    def __init__(
        self,
        file_path: str | Path,
        name: str | None = None,
        priority: int = 50,
    ) -> None:
        """Initialize YAML config source.

        Args:
            file_path: Path to YAML file
            name: Optional name for this source (defaults to filename)
            priority: Priority of this source (default 50)
        """
        self.file_path = Path(file_path)
        self.name = name or f"yaml:{self.file_path.name}"
        self.priority = priority

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from YAML file.

        Returns:
            Dictionary of ConfigValue objects

        Raises:
            ConfigLoadError: If file cannot be loaded
        """
        if not YAML_AVAILABLE:
            msg = "PyYAML not available, cannot load YAML config"
            raise ConfigLoadError(msg)

        if not self.file_path.exists():
            logger.warning("Config file %s does not exist, skipping", self.file_path)
            return {}

        try:
            with open(self.file_path) as f:
                data = yaml.safe_load(f)

            if data is None:
                return {}

            # Flatten nested dict to dot notation
            flattened = self._flatten_dict(data)

            # Convert to ConfigValue objects
            config = {
                key: ConfigValue(value=value, source=self.name, priority=self.priority)
                for key, value in flattened.items()
            }

            logger.debug("Loaded %s values from %s", len(config), self.file_path)

            return config

        except Exception as e:
            msg = f"Failed to load YAML config from {self.file_path}: {e}"
            raise ConfigLoadError(msg) from e

    def get(self, key: str) -> ConfigValue | None:
        """Get a specific configuration value.

        Args:
            key: Configuration key (supports dot notation)

        Returns:
            ConfigValue or None
        """
        config = self.load()
        return config.get(key)

    def _flatten_dict(self, data: dict, parent_key: str = "", sep: str = ".") -> dict:
        """Flatten nested dictionary to dot notation.

        Args:
            data: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys

        Returns:
            Flattened dictionary

        Example:
            {"database": {"host": "localhost"}} -> {"database.host": "localhost"}
        """
        items = []

        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                # Recursively flatten nested dicts
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))

        return dict(items)


class EnvVarConfigSource:
    """Configuration source that loads from environment variables.

    Environment variable names are converted to config keys:
    - Prefix is removed
    - Converted to lowercase
    - Double underscores become dots (for nested keys)
    """

    def __init__(
        self,
        prefix: str = "",
        name: str = "env",
        priority: int = 80,
    ) -> None:
        """Initialize environment variable config source.

        Args:
            prefix: Prefix for environment variables
            name: Name for this source
            priority: Priority of this source (default 80)
        """
        self.prefix = prefix
        self.name = name
        self.priority = priority

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from environment variables.

        Returns:
            Dictionary of ConfigValue objects
        """
        config = {}

        for env_key, env_value in os.environ.items():
            # Check if env var matches prefix
            if not env_key.startswith(self.prefix):
                continue

            # Remove prefix and convert to config key
            config_key = env_key[len(self.prefix) :]

            # Convert to lowercase and replace __ with .
            config_key = config_key.lower().replace("__", ".")

            # Try to parse value
            parsed_value = self._parse_value(env_value)

            config[config_key] = ConfigValue(
                value=parsed_value,
                source=self.name,
                priority=self.priority,
                path=config_key,
            )

        logger.debug("Loaded %s values from environment variables", len(config))

        return config

    def get(self, key: str) -> ConfigValue | None:
        """Get a specific configuration value.

        Args:
            key: Configuration key

        Returns:
            ConfigValue or None
        """
        # Convert key to env var name
        env_key = self.prefix + key.upper().replace(".", "__")

        env_value = os.environ.get(env_key)
        if env_value is None:
            return None

        parsed_value = self._parse_value(env_value)

        return ConfigValue(
            value=parsed_value,
            source=self.name,
            priority=self.priority,
            path=key,
        )

    def _parse_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type.

        Args:
            value: String value from environment

        Returns:
            Parsed value (int, float, bool, or str)
        """
        # Try to parse as int
        try:
            return int(value)
        except ValueError:
            pass

        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass

        # Parse as bool
        value_lower = value.lower()
        if value_lower in ("true", "yes", "1", "on"):
            return True
        if value_lower in ("false", "no", "0", "off"):
            return False

        # Return as string
        return value


class CLIArgsConfigSource:
    """Configuration source that loads from CLI arguments.

    Parses command-line arguments using argparse conventions.

    Example:
        # Command: python script.py --max-workers 8 --timeout 300
        # Results: {"max_workers": 8, "timeout": 300}

        source = CLIArgsConfigSource(sys.argv, priority=100)
        config = source.load()
    """

    def __init__(
        self,
        args: list[str] | None = None,
        name: str = "cli",
        priority: int = 100,
        parser: argparse.ArgumentParser | None = None,
    ) -> None:
        """Initialize CLI args config source.

        Args:
            args: Command-line arguments (defaults to sys.argv)
            name: Name for this source
            priority: Priority of this source (default 100)
            parser: Optional argparse parser (will be created if not provided)
        """
        self.args = args
        self.name = name
        self.priority = priority
        self.parser = parser

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from CLI arguments.

        Returns:
            Dictionary of ConfigValue objects
        """
        if self.parser is None:
            # No parser configured - parse simple --key value pairs
            return self._parse_simple_args()

        # Use provided parser
        try:
            parsed_args = self.parser.parse_args(self.args)
            args_dict = vars(parsed_args)

            config = {
                key: ConfigValue(
                    value=value,
                    source=self.name,
                    priority=self.priority,
                    path=key,
                )
                for key, value in args_dict.items()
                if value is not None  # Exclude None values (not provided)
            }

            logger.debug("Loaded %s values from CLI arguments", len(config))

            return config

        except Exception as e:
            logger.warning("Failed to parse CLI arguments: %s", e)
            return {}

    def get(self, key: str) -> ConfigValue | None:
        """Get a specific configuration value.

        Args:
            key: Configuration key

        Returns:
            ConfigValue or None
        """
        config = self.load()
        return config.get(key)

    def _parse_simple_args(self) -> dict[str, ConfigValue]:
        """Parse simple --key value CLI arguments.

        Returns:
            Dictionary of ConfigValue objects
        """
        if not self.args:
            return {}

        config = {}
        i = 0

        while i < len(self.args):
            arg = self.args[i]

            # Check if this is a flag (--key or -key)
            if arg.startswith("--"):
                key = arg[2:].replace("-", "_")

                # Check if next arg is the value
                if i + 1 < len(self.args) and not self.args[i + 1].startswith("-"):
                    value_str = self.args[i + 1]
                    i += 2

                    # Parse value
                    value = self._parse_value(value_str)

                    config[key] = ConfigValue(
                        value=value,
                        source=self.name,
                        priority=self.priority,
                        path=key,
                    )
                else:
                    # Flag without value - treat as boolean True
                    config[key] = ConfigValue(
                        value=True,
                        source=self.name,
                        priority=self.priority,
                        path=key,
                    )
                    i += 1
            else:
                i += 1

        logger.debug("Parsed %s values from simple CLI arguments", len(config))

        return config

    def _parse_value(self, value: str) -> Any:
        """Parse CLI argument value to appropriate type.

        Args:
            value: String value from CLI

        Returns:
            Parsed value (int, float, bool, or str)
        """
        # Try to parse as int
        try:
            return int(value)
        except ValueError:
            pass

        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass

        # Parse as bool
        value_lower = value.lower()
        if value_lower in ("true", "yes", "1", "on"):
            return True
        if value_lower in ("false", "no", "0", "off"):
            return False

        # Return as string
        return value


class DictConfigSource:
    """Configuration source that loads from Python dictionary.

    Useful for providing default values or testing.

    Example:
        defaults = DictConfigSource(
            {"max_workers": 4, "timeout": 300},
            name="defaults",
            priority=10,
        )

        config = defaults.load()
    """

    def __init__(
        self,
        data: dict[str, Any],
        name: str = "dict",
        priority: int = 0,
    ) -> None:
        """Initialize dictionary config source.

        Args:
            data: Configuration dictionary
            name: Name for this source
            priority: Priority of this source (default 0 for defaults)
        """
        self.data = data
        self.name = name
        self.priority = priority

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from dictionary.

        Returns:
            Dictionary of ConfigValue objects
        """
        config = {
            key: ConfigValue(
                value=value,
                source=self.name,
                priority=self.priority,
                path=key,
            )
            for key, value in self.data.items()
        }

        logger.debug("Loaded %s values from dictionary", len(config))

        return config

    def get(self, key: str) -> ConfigValue | None:
        """Get a specific configuration value.

        Args:
            key: Configuration key

        Returns:
            ConfigValue or None
        """
        value = self.data.get(key)
        if value is None:
            return None

        return ConfigValue(
            value=value,
            source=self.name,
            priority=self.priority,
            path=key,
        )
