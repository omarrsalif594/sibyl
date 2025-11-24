"""
Configuration cascade system for techniques and subtechniques.

This module implements a cascading configuration system where settings
can be defined at multiple levels (global, technique, subtechnique) with
proper precedence handling.

Precedence order: subtechnique > technique > global
"""

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigCascade:
    """
    Cascading configuration manager.

    This class merges configurations from multiple levels:
    1. Global configuration (lowest priority)
    2. Technique configuration (medium priority)
    3. Subtechnique configuration (highest priority)

    Configuration values at higher levels override those at lower levels.

    Example:
        >>> cascade = ConfigCascade(
        ...     global_config={"timeout": 30, "retries": 3},
        ...     technique_config={"timeout": 60},
        ...     subtechnique_config={"retries": 5}
        ... )
        >>> cascade.get("timeout")  # Returns 60 (from technique)
        60
        >>> cascade.get("retries")  # Returns 5 (from subtechnique)
        5
    """

    def __init__(
        self,
        global_config: dict[str, Any] | None = None,
        technique_config: dict[str, Any] | None = None,
        subtechnique_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize configuration cascade.

        Args:
            global_config: Global-level configuration
            technique_config: Technique-level configuration
            subtechnique_config: Subtechnique-level configuration
        """
        self.global_config = global_config or {}
        self.technique_config = technique_config or {}
        self.subtechnique_config = subtechnique_config or {}

        # Merged configuration cache
        self._merged_config: dict[str, Any] | None = None

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with cascading priority.

        Priority: subtechnique > technique > global

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> cascade.get("provider.api_key")
            'abc123'
        """
        # Check subtechnique config first (highest priority)
        value = self._get_nested(self.subtechnique_config, key)
        if value is not None:
            return value

        # Check technique config (medium priority)
        value = self._get_nested(self.technique_config, key)
        if value is not None:
            return value

        # Check global config (lowest priority)
        value = self._get_nested(self.global_config, key)
        if value is not None:
            return value

        return default

    def _get_nested(self, config: dict[str, Any], key: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            config: Configuration dictionary
            key: Key (supports dot notation like "a.b.c")

        Returns:
            Value if found, None otherwise
        """
        if "." not in key:
            return config.get(key)

        # Handle nested keys
        parts = key.split(".")
        current = config

        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None

        return current

    def merge(self) -> dict[str, Any]:
        """
        Merge all configuration levels into a single dictionary.

        Returns a deep copy to prevent mutation of original configs.

        Returns:
            Merged configuration dictionary

        Example:
            >>> cascade.merge()
            {'timeout': 60, 'retries': 5, 'log_level': 'INFO'}
        """
        if self._merged_config is not None:
            return copy.deepcopy(self._merged_config)

        # Start with global config
        merged = copy.deepcopy(self.global_config)

        # Merge technique config (overrides global)
        merged = self._deep_merge(merged, self.technique_config)

        # Merge subtechnique config (overrides technique and global)
        merged = self._deep_merge(merged, self.subtechnique_config)

        # Cache the result
        self._merged_config = merged

        return copy.deepcopy(merged)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries.

        Values in override replace those in base. For nested dictionaries,
        recursively merge them.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary

        Example:
            >>> base = {"a": 1, "b": {"c": 2}}
            >>> override = {"b": {"d": 3}, "e": 4}
            >>> _deep_merge(base, override)
            {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = copy.deepcopy(value)

        return result

    def set(self, key: str, value: Any, level: str = "subtechnique") -> None:
        """
        Set a configuration value at a specific level.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            level: Configuration level ("global", "technique", or "subtechnique")

        Raises:
            ValueError: If level is invalid

        Example:
            >>> cascade.set("timeout", 120, level="technique")
        """
        if level == "global":
            target = self.global_config
        elif level == "technique":
            target = self.technique_config
        elif level == "subtechnique":
            target = self.subtechnique_config
        else:
            msg = f"Invalid level: {level}. Must be 'global', 'technique', or 'subtechnique'"
            raise ValueError(msg)

        # Handle dot notation
        if "." not in key:
            target[key] = value
        else:
            parts = key.split(".")
            current = target

            # Navigate to parent
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set value
            current[parts[-1]] = value

        # Invalidate cache
        self._merged_config = None

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """
        Export all configuration levels.

        Returns:
            Dictionary with keys "global", "technique", "subtechnique"

        Example:
            >>> cascade.to_dict()
            {
                "global": {...},
                "technique": {...},
                "subtechnique": {...}
            }
        """
        return {
            "global": copy.deepcopy(self.global_config),
            "technique": copy.deepcopy(self.technique_config),
            "subtechnique": copy.deepcopy(self.subtechnique_config),
        }

    @classmethod
    def from_files(
        cls,
        global_config_path: Path | None = None,
        technique_config_path: Path | None = None,
        subtechnique_config_path: Path | None = None,
    ) -> "ConfigCascade":
        """
        Create ConfigCascade from configuration files.

        Args:
            global_config_path: Path to global config YAML
            technique_config_path: Path to technique config YAML
            subtechnique_config_path: Path to subtechnique config YAML

        Returns:
            ConfigCascade instance

        Raises:
            FileNotFoundError: If a specified file doesn't exist
            ValueError: If a config file is invalid YAML

        Example:
            >>> cascade = ConfigCascade.from_files(
            ...     global_config_path=Path("global.yaml"),
            ...     technique_config_path=Path("chunking/config.yaml")
            ... )
        """
        global_config = cls._load_yaml_file(global_config_path) if global_config_path else {}
        technique_config = (
            cls._load_yaml_file(technique_config_path) if technique_config_path else {}
        )
        subtechnique_config = (
            cls._load_yaml_file(subtechnique_config_path) if subtechnique_config_path else {}
        )

        return cls(
            global_config=global_config,
            technique_config=technique_config,
            subtechnique_config=subtechnique_config,
        )

    @staticmethod
    def _load_yaml_file(path: Path) -> dict[str, Any]:
        """
        Load YAML configuration file.

        Args:
            path: Path to YAML file

        Returns:
            Loaded configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        if not path.exists():
            msg = f"Configuration file not found: {path}"
            raise FileNotFoundError(msg)

        try:
            with open(path) as f:
                config = yaml.safe_load(f)
                return config if config is not None else {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in {path}: {e}"
            raise ValueError(msg) from None

    def __repr__(self) -> str:
        """String representation of ConfigCascade."""
        return (
            f"ConfigCascade("
            f"global={len(self.global_config)} keys, "
            f"technique={len(self.technique_config)} keys, "
            f"subtechnique={len(self.subtechnique_config)} keys)"
        )
