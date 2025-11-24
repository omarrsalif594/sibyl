"""Workspace configuration loader.

This module provides functionality to load and validate workspace configurations
from YAML files using the workspace schema defined in workspace_schema.py.

Example:
    from sibyl.config.workspace_loader import load_workspace

    # Load workspace from YAML file
    workspace = load_workspace("config/workspaces/example_local.yaml")

    # Access configuration
    llm_config = workspace.providers.llm["default"]
    print(f"Using {llm_config.provider} with model {llm_config.model}")

    # Access pipelines
    pipeline = workspace.pipelines["web_research_pipeline"]
    print(f"Pipeline has {len(pipeline.steps)} steps")
"""

import logging
from pathlib import Path

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from pydantic import ValidationError

from sibyl.config.workspace_schema import WorkspaceSettings
from sibyl.core.config.env_expansion import EnvExpansionError, expand_workspace_config
from sibyl.core.config.feature_validation import (
    format_validation_errors,
    validate_features,
)

logger = logging.getLogger(__name__)


class WorkspaceLoadError(Exception):
    """Raised when workspace configuration cannot be loaded or validated."""


def load_workspace(path: str | Path) -> WorkspaceSettings:
    """Load and validate workspace configuration from YAML file.

    Args:
        path: Path to workspace YAML file

    Returns:
        WorkspaceSettings: Validated workspace configuration

    Raises:
        WorkspaceLoadError: If file cannot be loaded or validation fails

    Example:
        workspace = load_workspace("config/workspaces/example_local.yaml")
        assert workspace.name == "local-rag-demo"
        assert "default" in workspace.providers.llm
    """
    if not YAML_AVAILABLE:
        msg = "PyYAML is not available. Install it with: pip install pyyaml"
        raise WorkspaceLoadError(msg)

    file_path = Path(path)

    # Check if file exists
    if not file_path.exists():
        msg = f"Workspace file not found: {file_path}"
        raise WorkspaceLoadError(msg)

    # Check if it's a file (not a directory)
    if not file_path.is_file():
        msg = f"Path is not a file: {file_path}"
        raise WorkspaceLoadError(msg)

    try:
        # Load YAML file
        with open(file_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if yaml_data is None:
            msg = f"Workspace file is empty: {file_path}"
            raise WorkspaceLoadError(msg)

        if not isinstance(yaml_data, dict):
            msg = f"Workspace file must contain a YAML dictionary, got {type(yaml_data).__name__}"
            raise WorkspaceLoadError(msg)

        logger.debug("Loaded YAML data from %s", file_path)

        # Step 1: Expand environment variables
        try:
            yaml_data = expand_workspace_config(yaml_data, strict=True)
            logger.debug("Environment variables expanded successfully")
        except EnvExpansionError as e:
            msg = f"Environment variable expansion failed for {file_path}: {e}"
            raise WorkspaceLoadError(msg) from e

        # Step 2: Validate features (opt-in validation)
        validation_errors = validate_features(yaml_data)
        error_list = [e for e in validation_errors if e.severity == "error"]
        if error_list:
            formatted_errors = format_validation_errors(error_list)
            msg = f"Feature validation failed for {file_path}:\n{formatted_errors}"
            raise WorkspaceLoadError(msg)

        # Log warnings but don't fail
        warnings = [e for e in validation_errors if e.severity == "warning"]
        if warnings:
            logger.warning(
                f"Feature validation warnings for {file_path}:\n"
                + format_validation_errors(warnings)
            )

        # Step 3: Validate and parse using Pydantic schema
        try:
            workspace = WorkspaceSettings.model_validate(yaml_data)
            logger.info("Successfully loaded workspace '%s' from %s", workspace.name, file_path)
            return workspace

        except ValidationError as e:
            # Format validation errors in a user-friendly way
            error_messages = []
            for error in e.errors():
                location = " -> ".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_messages.append(f"  {location}: {message}")

            error_summary = "\n".join(error_messages)
            msg = f"Workspace validation failed for {file_path}:\n{error_summary}"
            raise WorkspaceLoadError(msg) from e

    except yaml.YAMLError as e:
        msg = f"Failed to parse YAML file {file_path}: {e}"
        raise WorkspaceLoadError(msg) from e

    except OSError as e:
        msg = f"Failed to read workspace file {file_path}: {e}"
        raise WorkspaceLoadError(msg) from e


def load_workspace_dict(data: dict) -> WorkspaceSettings:
    """Load and validate workspace configuration from dictionary.

    Useful for testing or programmatic configuration.

    Args:
        data: Dictionary containing workspace configuration

    Returns:
        WorkspaceSettings: Validated workspace configuration

    Raises:
        WorkspaceLoadError: If validation fails

    Example:
        config_dict = {
            "name": "test-workspace",
            "providers": {"llm": {}, "embeddings": {}, "vector_store": {}, "mcp": {}},
        }
        workspace = load_workspace_dict(config_dict)
    """
    try:
        workspace = WorkspaceSettings.model_validate(data)
        logger.debug("Successfully validated workspace '%s' from dictionary", workspace.name)
        return workspace

    except ValidationError as e:
        # Format validation errors
        error_messages = []
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"  {location}: {message}")

        error_summary = "\n".join(error_messages)
        msg = f"Workspace validation failed:\n{error_summary}"
        raise WorkspaceLoadError(msg) from e


def validate_workspace_file(path: str | Path) -> tuple[bool, str]:
    """Validate a workspace configuration file without loading it fully.

    Args:
        path: Path to workspace YAML file

    Returns:
        Tuple of (is_valid, message) where message contains error details if invalid

    Example:
        is_valid, message = validate_workspace_file("config/workspaces/example.yaml")
        if not is_valid:
            print(f"Validation failed: {message}")
    """
    try:
        load_workspace(path)
        return True, "Workspace configuration is valid"
    except WorkspaceLoadError as e:
        return False, str(e)


def get_workspace_info(path: str | Path) -> dict:
    """Get basic information about a workspace without full validation.

    Extracts name, description, and version from the workspace file.

    Args:
        path: Path to workspace YAML file

    Returns:
        Dictionary with workspace metadata (name, description, version)

    Raises:
        WorkspaceLoadError: If file cannot be read

    Example:
        info = get_workspace_info("config/workspaces/example.yaml")
        print(f"Workspace: {info['name']} - {info['description']}")
    """
    if not YAML_AVAILABLE:
        msg = "PyYAML is not available"
        raise WorkspaceLoadError(msg)

    file_path = Path(path)

    if not file_path.exists():
        msg = f"Workspace file not found: {file_path}"
        raise WorkspaceLoadError(msg)

    try:
        with open(file_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if not isinstance(yaml_data, dict):
            msg = "Invalid workspace file format"
            raise WorkspaceLoadError(msg)

        return {
            "name": yaml_data.get("name", "unknown"),
            "description": yaml_data.get("description", ""),
            "version": yaml_data.get("version", "1.0"),
        }

    except yaml.YAMLError as e:
        msg = f"Failed to parse YAML file: {e}"
        raise WorkspaceLoadError(msg) from e
    except OSError as e:
        msg = f"Failed to read file: {e}"
        raise WorkspaceLoadError(msg) from e
