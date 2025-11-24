"""
Core Configuration Loader

Loads configuration from core_defaults.yaml with support for:
- Environment variable overrides
- Custom config file paths
- Section-specific access
- Fallback to sensible defaults
- Schema validation
"""

import os
import warnings
from pathlib import Path
from typing import Any

import yaml

# Cache for loaded config
_CONFIG_CACHE: dict[str, Any] | None = None

# Validation enabled by default (can be disabled via environment variable)
_VALIDATION_ENABLED = os.environ.get("SIBYL_DISABLE_CONFIG_VALIDATION", "").lower() not in (
    "1",
    "true",
    "yes",
)


def _find_config_file() -> Path:
    """Find the core_defaults.yaml file."""
    # Check for environment variable override
    env_path = os.environ.get("SIBYL_CORE_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Default location: sibyl/core/config/core_defaults.yaml
    current_file = Path(__file__).resolve()
    config_path = current_file.parent / "core_defaults.yaml"

    if not config_path.exists():
        msg = (
            f"Core config file not found at {config_path}. "
            "Set SIBYL_CORE_CONFIG environment variable to specify a custom location."
        )
        raise FileNotFoundError(msg)

    return config_path


def _apply_env_overrides(config: dict[str, Any], prefix: str = "SIBYL") -> dict[str, Any]:
    """
    Apply environment variable overrides to config.

    Environment variables should follow the pattern:
    SIBYL_<SECTION>_<KEY>=value

    Example:
    SIBYL_AGENT_MAX_TOOLS_PER_PLAN=10
    SIBYL_LLM_RETRY_MAX_RETRIES=5
    """
    result = config.copy()

    for env_key, env_value in os.environ.items():
        if not env_key.startswith(f"{prefix}_"):
            continue

        # Parse the key: SIBYL_AGENT_MAX_TOOLS_PER_PLAN -> ['agent', 'max_tools_per_plan']
        parts = env_key[len(prefix) + 1 :].lower().split("_")
        if len(parts) < 2:
            continue

        section = parts[0]
        key_parts = parts[1:]

        # Navigate to the right section
        if section not in result:
            continue

        # Handle nested keys
        current = result[section]
        for _i, part in enumerate(key_parts[:-1]):
            if not isinstance(current, dict):
                break
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            # Set the value (try to parse as int/float/bool)
            final_key = key_parts[-1]
            if isinstance(current, dict):
                current[final_key] = _parse_env_value(env_value)

    return result


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate type."""
    # Try boolean
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value


def load_core_config(
    section: str | None = None, reload: bool = False, validate: bool = True
) -> dict[str, Any]:
    """
    Load core configuration from core_defaults.yaml.

    Args:
        section: Optional section name to return (e.g., 'agent', 'llm', 'security')
                If None, returns the entire config.
        reload: If True, force reload from disk (ignores cache)
        validate: If True, validate config against schema (default: True)

    Returns:
        Configuration dictionary or section dictionary

    Raises:
        FileNotFoundError: If config file cannot be found
        KeyError: If specified section does not exist

    Examples:
        >>> config = load_core_config()  # Load entire config
        >>> agent_config = load_core_config('agent')  # Load agent section
        >>> max_tools = load_core_config('agent').get('max_tools_per_plan', 5)
    """
    global _CONFIG_CACHE

    # Use cache if available
    if _CONFIG_CACHE is not None and not reload:
        config = _CONFIG_CACHE
    else:
        # Load from file
        config_path = _find_config_file()
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Apply environment variable overrides
        config = _apply_env_overrides(config)

        # Validate configuration if enabled
        if validate and _VALIDATION_ENABLED:
            try:
                from .validator import ConfigValidator

                validator = ConfigValidator()
                if not validator.validate(config, strict=False):
                    # Collect errors but only warn (don't fail)
                    warnings.warn(
                        f"Configuration validation warnings:\n{validator.format_errors()}",
                        UserWarning,
                        stacklevel=2,
                    )
            except ImportError:
                # Validator not available, skip validation
                pass
            except Exception as e:
                warnings.warn(f"Configuration validation failed: {e}", UserWarning, stacklevel=2)

        # Cache it
        _CONFIG_CACHE = config

    # Return section or full config
    if section is None:
        return config

    if section not in config:
        msg = (
            f"Configuration section '{section}' not found. "
            f"Available sections: {', '.join(config.keys())}"
        )
        raise KeyError(msg)

    return config[section]


def get_config_value(section: str, *keys: str, default: Any = None) -> Any:
    """
    Get a specific config value with fallback.

    Args:
        section: Config section (e.g., 'agent', 'llm')
        *keys: Nested keys to traverse (e.g., 'retry', 'max_retries')
        default: Default value if key not found

    Returns:
        Config value or default

    Examples:
        >>> max_retries = get_config_value('llm', 'retry', 'max_retries', default=3)
        >>> max_tools = get_config_value('agent', 'max_tools_per_plan', default=5)
    """
    try:
        config = load_core_config(section)
        value = config
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def reload_config() -> None:
    """Force reload of configuration from disk."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    load_core_config(reload=True)


# Convenience functions for common sections
def get_agent_config() -> dict[str, Any]:
    """Get agent configuration."""
    return load_core_config("agent")


def get_llm_config() -> dict[str, Any]:
    """Get LLM/infrastructure configuration."""
    return load_core_config("llm")


def get_orchestration_config() -> dict[str, Any]:
    """Get orchestration configuration."""
    return load_core_config("orchestration")


def get_security_config() -> dict[str, Any]:
    """Get security configuration."""
    return load_core_config("security")


def get_learning_config() -> dict[str, Any]:
    """Get learning configuration."""
    return load_core_config("learning")


def get_consensus_config() -> dict[str, Any]:
    """Get consensus configuration."""
    return load_core_config("consensus")


def get_session_config() -> dict[str, Any]:
    """Get session management configuration."""
    return load_core_config("session")


def get_quality_control_config() -> dict[str, Any]:
    """Get quality control configuration."""
    return load_core_config("quality_control")


def get_budget_config() -> dict[str, Any]:
    """Get budget configuration."""
    return load_core_config("budget")


def get_checkpointing_config() -> dict[str, Any]:
    """Get checkpointing configuration."""
    return load_core_config("checkpointing")


def get_graph_config() -> dict[str, Any]:
    """Get graph configuration."""
    return load_core_config("graph")


def get_performance_config() -> dict[str, Any]:
    """Get performance/platform configuration."""
    return load_core_config("performance")
