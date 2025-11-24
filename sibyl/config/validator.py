"""
Configuration Schema Validator

Validates configuration against schema.yaml to ensure all values are within acceptable ranges.
"""

from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""


class ConfigValidator:
    """Validates configuration against schema"""

    def __init__(self, schema_path: Path | None = None) -> None:
        """
        Args:
            schema_path: Path to schema.yaml file (defaults to sibyl/core/config/schema.yaml)
        """
        if schema_path is None:
            schema_path = Path(__file__).parent / "schema.yaml"

        if not schema_path.exists():
            msg = f"Schema file not found: {schema_path}"
            raise FileNotFoundError(msg)

        with open(schema_path) as f:
            self.schema = yaml.safe_load(f)

        self.errors: list[str] = []

    def validate(self, config: dict[str, Any], strict: bool = False) -> bool:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate
            strict: If True, fail on any validation error. If False, collect all errors.

        Returns:
            True if valid, False otherwise

        Raises:
            ConfigValidationError: If strict=True and validation fails
        """
        self.errors = []
        self._validate_dict(config, self.schema, path="")

        if self.errors:
            if strict:
                raise ConfigValidationError(
                    "Configuration validation failed:\n" + "\n".join(self.errors)
                )
            return False

        return True

    def _validate_dict(self, config: dict[str, Any], schema: dict[str, Any], path: str) -> None:
        """Validate a dictionary against schema"""
        for key, schema_def in schema.items():
            if key not in config:
                # Check if required
                if isinstance(schema_def, dict) and schema_def.get("required", False):
                    self.errors.append(f"{path}.{key}: Required field missing")
                continue

            value = config[key]
            self._validate_value(value, schema_def, f"{path}.{key}" if path else key)

    def _validate_value(self, value: Any, schema_def: dict[str, Any], path: str) -> None:
        """Validate a single value against its schema definition"""
        if not isinstance(schema_def, dict):
            return

        value_type = schema_def.get("type")

        if value_type == "object":
            if not isinstance(value, dict):
                self.errors.append(f"{path}: Expected object/dict, got {type(value).__name__}")
                return

            properties = schema_def.get("properties", {})
            if properties:
                self._validate_dict(value, properties, path)

        elif value_type == "array":
            if not isinstance(value, list):
                self.errors.append(f"{path}: Expected array/list, got {type(value).__name__}")
                return

            items_schema = schema_def.get("items", {})
            for i, item in enumerate(value):
                self._validate_value(item, items_schema, f"{path}[{i}]")

        elif value_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                self.errors.append(f"{path}: Expected integer, got {type(value).__name__}")
                return

            if "min" in schema_def and value < schema_def["min"]:
                self.errors.append(
                    f"{path}: Value {value} is less than minimum {schema_def['min']}"
                )
            if "max" in schema_def and value > schema_def["max"]:
                self.errors.append(
                    f"{path}: Value {value} is greater than maximum {schema_def['max']}"
                )

        elif value_type == "float":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                self.errors.append(f"{path}: Expected float, got {type(value).__name__}")
                return

            if "min" in schema_def and value < schema_def["min"]:
                self.errors.append(
                    f"{path}: Value {value} is less than minimum {schema_def['min']}"
                )
            if "max" in schema_def and value > schema_def["max"]:
                self.errors.append(
                    f"{path}: Value {value} is greater than maximum {schema_def['max']}"
                )

        elif value_type == "string":
            if not isinstance(value, str):
                self.errors.append(f"{path}: Expected string, got {type(value).__name__}")
                return

            if "enum" in schema_def and value not in schema_def["enum"]:
                self.errors.append(
                    f"{path}: Value '{value}' not in allowed values: {schema_def['enum']}"
                )

        elif value_type == "boolean":
            if not isinstance(value, bool):
                self.errors.append(f"{path}: Expected boolean, got {type(value).__name__}")

    def get_errors(self) -> list[str]:
        """Get list of validation errors from last validation"""
        return self.errors

    def format_errors(self) -> str:
        """Format errors as a readable string"""
        if not self.errors:
            return "No validation errors"
        return "\n".join(f"  - {error}" for error in self.errors)


def validate_config(config: dict[str, Any], strict: bool = False) -> bool:
    """
    Convenience function to validate configuration.

    Args:
        config: Configuration dictionary to validate
        strict: If True, raise exception on validation failure

    Returns:
        True if valid, False otherwise

    Raises:
        ConfigValidationError: If strict=True and validation fails
    """
    validator = ConfigValidator()
    return validator.validate(config, strict=strict)
