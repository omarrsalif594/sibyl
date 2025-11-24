"""Environment variable expansion for workspace configurations.

This module provides utilities to expand environment variables in workspace
configurations using the syntax:
- ${VAR} - Required variable (raises error if undefined)
- ${VAR:-default} - Optional variable with default value

Environment variables can be used in any string field in the configuration,
such as provider URLs, API keys, tool parameters, etc.

Example:
    from sibyl.core.config.env_expansion import expand_env_vars

    config = {
        "providers": {
            "llm": {
                "default": {
                    "provider": "openai",
                    "model": "${MODEL:-gpt-4}",
                    "api_key_env": "OPENAI_API_KEY",
                    "base_url": "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
                }
            }
        }
    }

    expanded = expand_env_vars(config)
"""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


class EnvExpansionError(Exception):
    """Raised when environment variable expansion fails."""


# Regex patterns for environment variable syntax
# Matches ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


def expand_env_vars(
    config: dict | list | Any,
    env: dict[str, str] | None = None,
    strict: bool = True,
    path: str = "",
) -> dict | list | Any:
    """Recursively expand environment variables in configuration.

    Processes the configuration structure recursively, expanding ${VAR} and
    ${VAR:-default} syntax in all string values. Preserves non-string types.

    Args:
        config: Configuration dictionary, list, or primitive value
        env: Environment variable dictionary (defaults to os.environ)
        strict: If True, raise error for undefined variables without defaults.
                If False, leave unexpanded variables as-is.
        path: Current path in config (for error messages)

    Returns:
        Configuration with environment variables expanded

    Raises:
        EnvExpansionError: If strict=True and a required variable is undefined

    Example:
        >>> os.environ['MODEL'] = 'gpt-4'
        >>> config = {"model": "${MODEL}"}
        >>> expand_env_vars(config)
        {'model': 'gpt-4'}

        >>> config = {"url": "${BASE_URL:-http://localhost:8000}"}
        >>> expand_env_vars(config)
        {'url': 'http://localhost:8000'}
    """
    if env is None:
        env = dict(os.environ)

    # Handle dictionaries
    if isinstance(config, dict):
        result = {}
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            result[key] = expand_env_vars(value, env, strict, current_path)
        return result

    # Handle lists
    if isinstance(config, list):
        result = []
        for i, item in enumerate(config):
            current_path = f"{path}[{i}]"
            result.append(expand_env_vars(item, env, strict, current_path))
        return result

    # Handle strings (perform expansion)
    if isinstance(config, str):
        return _expand_string(config, env, strict, path)

    # Preserve other types (int, float, bool, None, etc.)
    return config


def _expand_string(value: str, env: dict[str, str], strict: bool, path: str) -> str:
    """Expand environment variables in a single string.

    Args:
        value: String value potentially containing ${VAR} or ${VAR:-default}
        env: Environment variable dictionary
        strict: Whether to raise error for undefined variables
        path: Current path in config (for error messages)

    Returns:
        String with environment variables expanded

    Raises:
        EnvExpansionError: If strict=True and a required variable is undefined
    """

    def replace_match(match: re.Match) -> str:
        """Replace a single ${VAR} or ${VAR:-default} match."""
        var_name = match.group(1)  # Variable name
        has_default = match.group(2) is not None  # Has :-default?
        default_value = match.group(3) if has_default else None  # Default value

        # Try to get variable from environment
        if var_name in env:
            return env[var_name]

        # Variable not found - use default if provided
        if has_default:
            logger.debug(
                f"Environment variable '{var_name}' not found at {path}, "
                f"using default: '{default_value}'"
            )
            return default_value if default_value is not None else ""

        # Variable not found and no default - error or leave as-is
        if strict:
            msg = (
                f"Required environment variable '{var_name}' is not defined at {path}. "
                f"Either set the variable or provide a default using ${{VAR:-default}} syntax."
            )
            raise EnvExpansionError(msg)
        logger.warning(f"Environment variable '{var_name}' not found at {path}, leaving unexpanded")
        return match.group(0)  # Return original ${VAR}

    # Replace all occurrences of ${VAR} or ${VAR:-default}
    try:
        return ENV_VAR_PATTERN.sub(replace_match, value)
    except EnvExpansionError:
        raise
    except Exception as e:
        msg = f"Failed to expand environment variables in '{value}' at {path}: {e}"
        raise EnvExpansionError(msg) from e


def validate_env_syntax(config: dict | list | Any, path: str = "") -> list[str]:
    """Validate environment variable syntax without expanding.

    Checks for common syntax errors in environment variable references:
    - Malformed variable names (must start with letter or underscore)
    - Unmatched braces
    - Invalid syntax patterns

    Args:
        config: Configuration to validate
        path: Current path in config (for error messages)

    Returns:
        List of validation error messages (empty if valid)

    Example:
        >>> config = {"model": "${123_INVALID}"}
        >>> errors = validate_env_syntax(config)
        >>> len(errors) > 0
        True
    """
    errors = []

    # Handle dictionaries
    if isinstance(config, dict):
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            errors.extend(validate_env_syntax(value, current_path))

    # Handle lists
    elif isinstance(config, list):
        for i, item in enumerate(config):
            current_path = f"{path}[{i}]"
            errors.extend(validate_env_syntax(item, current_path))

    # Validate strings
    elif isinstance(config, str):
        # Check for unmatched braces
        open_count = config.count("${")
        close_count = config.count("}")
        if open_count != close_count:
            errors.append(f"{path}: Unmatched braces in environment variable reference: '{config}'")

        # Check for invalid variable names (must match pattern)
        for match in re.finditer(r"\$\{([^}]+)\}", config):
            var_expr = match.group(1)
            # Split on :- to get variable name
            var_name = var_expr.split(":-")[0] if ":-" in var_expr else var_expr

            # Validate variable name (must start with letter or underscore)
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", var_name):
                errors.append(
                    f"{path}: Invalid environment variable name '{var_name}' in '{config}'. "
                    f"Variable names must start with a letter or underscore and contain only "
                    f"alphanumeric characters and underscores."
                )

    return errors


def extract_required_env_vars(config: dict | list | Any) -> list[str]:
    """Extract list of required environment variables from configuration.

    Returns all variables referenced without defaults (${VAR} syntax).
    Useful for validation and documentation.

    Args:
        config: Configuration to analyze

    Returns:
        List of required environment variable names (deduplicated)

    Example:
        >>> config = {
        ...     "api_key": "${API_KEY}",
        ...     "url": "${BASE_URL:-http://localhost}",
        ...     "model": "${MODEL}"
        ... }
        >>> sorted(extract_required_env_vars(config))
        ['API_KEY', 'MODEL']
    """
    required_vars = set()

    def extract_from_value(value: Any) -> None:
        """Recursively extract required variables."""
        if isinstance(value, dict):
            for v in value.values():
                extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
        elif isinstance(value, str):
            # Find all ${VAR} without defaults
            for match in ENV_VAR_PATTERN.finditer(value):
                var_name = match.group(1)
                has_default = match.group(2) is not None
                if not has_default:
                    required_vars.add(var_name)

    extract_from_value(config)
    return sorted(required_vars)


def extract_all_env_vars(config: dict | list | Any) -> dict[str, str | None]:
    """Extract all environment variables with their defaults.

    Returns a mapping of variable name to default value (None if no default).
    Useful for documentation and validation.

    Args:
        config: Configuration to analyze

    Returns:
        Dictionary mapping variable names to default values (None if required)

    Example:
        >>> config = {
        ...     "api_key": "${API_KEY}",
        ...     "url": "${BASE_URL:-http://localhost}",
        ...     "port": "${PORT:-8000}"
        ... }
        >>> vars = extract_all_env_vars(config)
        >>> vars['API_KEY'] is None
        True
        >>> vars['BASE_URL']
        'http://localhost'
    """
    env_vars = {}

    def extract_from_value(value: Any) -> None:
        """Recursively extract all variables."""
        if isinstance(value, dict):
            for v in value.values():
                extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
        elif isinstance(value, str):
            for match in ENV_VAR_PATTERN.finditer(value):
                var_name = match.group(1)
                has_default = match.group(2) is not None
                default_value = match.group(3) if has_default else None

                # Track first occurrence (don't overwrite with None)
                if var_name not in env_vars or (
                    default_value is not None and env_vars[var_name] is None
                ):
                    env_vars[var_name] = default_value

    extract_from_value(config)
    return env_vars


# Convenience function for common use case
def expand_workspace_config(config: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    """Convenience function to expand environment variables in workspace config.

    Uses os.environ as the environment variable source.

    Args:
        config: Workspace configuration dictionary
        strict: If True, raise error for undefined required variables

    Returns:
        Configuration with environment variables expanded

    Raises:
        EnvExpansionError: If strict=True and a required variable is undefined

    Example:
        >>> config = load_yaml("workspace.yaml")
        >>> expanded = expand_workspace_config(config)
    """
    return expand_env_vars(config, env=None, strict=strict, path="workspace")
