"""
Opencode Sibyl Adapter.

This adapter maps Opencode commands to Sibyl workspaces and pipelines,
enabling users to define custom Opencode commands that trigger Sibyl
data processing and AI workflows.

Opencode is a tool that allows users to define custom commands. This adapter
provides the glue between Opencode's command system and Sibyl's pipeline execution.

Architecture:
    1. User defines commands in a YAML mapping file
    2. Each command maps to: workspace + pipeline + optional default params
    3. OpencodeAdapter loads the mapping and resolves commands
    4. Commands are executed via sibyl_runner.run_pipeline()

Example Mapping (opencode_sibyl_example.yaml):
    commands:
      northwind.data_quality:
        workspace: "examples/companies/northwind_analytics/config/workspace.yaml"
        pipeline: "revenue_analysis"
        default_params:
          time_period: "2024-Q3"

Usage:
    >>> from plugins.opencode import OpencodeAdapter
    >>> adapter = OpencodeAdapter("plugins/opencode/opencode_sibyl_example.yaml")
    >>> result = adapter.execute("northwind.data_quality", {"question": "Why is revenue down?"})
    >>> print(result["status"])
"""

import logging
from pathlib import Path
from typing import Any

from plugins.common.sibyl_runner import load_pipeline_config, run_pipeline

logger = logging.getLogger(__name__)


class OpencodeAdapter:
    """
    Adapter for mapping Opencode commands to Sibyl pipelines.

    This class handles:
    - Loading command mapping configuration
    - Resolving command names to workspace + pipeline
    - Merging default params with runtime params
    - Executing pipelines via sibyl_runner
    - Providing metadata about available commands

    Attributes:
        config_path: Path to the command mapping YAML file
        commands: Dictionary of command name -> command configuration
        base_dir: Base directory for resolving relative paths
    """

    def __init__(self, config_path: str | Path, base_dir: str | Path | None = None) -> None:
        """
        Initialize the Opencode adapter.

        Args:
            config_path: Path to the command mapping YAML configuration
            base_dir: Base directory for resolving relative workspace paths
                     (defaults to config file's directory)

        Raises:
            ValueError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        self.base_dir = Path(base_dir) if base_dir else self.config_path.parent
        self.commands = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load and validate command mapping configuration."""
        config = load_pipeline_config(self.config_path)

        if "commands" not in config:
            msg = f"Configuration must have 'commands' key: {self.config_path}"
            raise ValueError(msg)

        self.commands = config["commands"]
        logger.info("Loaded %s Opencode commands from %s", len(self.commands), self.config_path)

    def resolve_command(self, command_name: str) -> dict[str, Any]:
        """
        Resolve a command name to its configuration.

        Args:
            command_name: Name of the Opencode command (e.g., "northwind.data_quality")

        Returns:
            Dictionary with command configuration:
            {
                "workspace": str,
                "pipeline": str,
                "default_params": dict (optional),
                "description": str (optional)
            }

        Raises:
            KeyError: If command is not found

        Example:
            >>> adapter = OpencodeAdapter("config.yaml")
            >>> config = adapter.resolve_command("northwind.data_quality")
            >>> print(config["workspace"])
        """
        if command_name not in self.commands:
            available = ", ".join(self.commands.keys())
            msg = f"Command '{command_name}' not found. Available commands: {available}"
            raise KeyError(msg)

        cmd_config = self.commands[command_name].copy()

        # Resolve relative workspace path
        workspace_path = Path(cmd_config["workspace"])
        if not workspace_path.is_absolute():
            workspace_path = (self.base_dir / workspace_path).resolve()
        cmd_config["workspace"] = str(workspace_path)

        return cmd_config

    def execute(
        self, command_name: str, params: dict[str, Any] | None = None, timeout: int | None = 300
    ) -> dict[str, Any]:
        """
        Execute an Opencode command.

        This method:
        1. Resolves the command to workspace + pipeline
        2. Merges default params with provided params
        3. Executes the pipeline via sibyl_runner
        4. Returns structured result

        Args:
            command_name: Name of the Opencode command
            params: Runtime parameters (merged with default_params)
            timeout: Maximum execution time in seconds

        Returns:
            Pipeline execution result dictionary (see sibyl_runner.run_pipeline)

        Example:
            >>> adapter = OpencodeAdapter("config.yaml")
            >>> result = adapter.execute(
            ...     "northwind.data_quality",
            ...     params={"question": "Why is revenue down?"}
            ... )
            >>> if result["status"] == "success":
            ...     print("Command succeeded!")
        """
        logger.info("Executing Opencode command: %s", command_name)

        # Resolve command configuration
        cmd_config = self.resolve_command(command_name)

        # Merge parameters (runtime params override defaults)
        merged_params = cmd_config.get("default_params", {}).copy()
        if params:
            merged_params.update(params)

        # Execute pipeline
        result = run_pipeline(
            workspace_path=cmd_config["workspace"],
            pipeline_name=cmd_config["pipeline"],
            params=merged_params,
            timeout=timeout,
        )

        # Add command metadata to result
        result["command"] = command_name

        return result

    def list_commands(self) -> list[dict[str, Any]]:
        """
        List all available commands with metadata.

        Returns:
            List of dictionaries with command information:
            [
                {
                    "name": str,
                    "pipeline": str,
                    "workspace": str,
                    "description": str (optional),
                    "default_params": dict (optional)
                },
                ...
            ]

        Example:
            >>> adapter = OpencodeAdapter("config.yaml")
            >>> for cmd in adapter.list_commands():
            ...     print(f"{cmd['name']}: {cmd['description']}")
        """
        result = []
        for cmd_name, cmd_config in self.commands.items():
            result.append(
                {
                    "name": cmd_name,
                    "pipeline": cmd_config["pipeline"],
                    "workspace": cmd_config["workspace"],
                    "description": cmd_config.get("description", ""),
                    "default_params": cmd_config.get("default_params", {}),
                }
            )
        return result

    def validate_command(self, command_name: str) -> dict[str, Any]:
        """
        Validate that a command configuration is correct.

        This checks:
        - Command exists
        - Workspace file exists
        - Required fields are present

        Args:
            command_name: Name of the command to validate

        Returns:
            Validation result:
            {
                "valid": bool,
                "command": str,
                "workspace_exists": bool,
                "errors": List[str]
            }

        Example:
            >>> adapter = OpencodeAdapter("config.yaml")
            >>> validation = adapter.validate_command("northwind.data_quality")
            >>> if not validation["valid"]:
            ...     print(validation["errors"])
        """
        errors = []

        try:
            cmd_config = self.resolve_command(command_name)
        except KeyError as e:
            return {
                "valid": False,
                "command": command_name,
                "workspace_exists": False,
                "errors": [str(e)],
            }

        # Check workspace file exists
        workspace_path = Path(cmd_config["workspace"])
        workspace_exists = workspace_path.exists()
        if not workspace_exists:
            errors.append(f"Workspace file not found: {workspace_path}")

        # Check required fields
        if "pipeline" not in cmd_config:
            errors.append("Missing required field: 'pipeline'")

        return {
            "valid": len(errors) == 0,
            "command": command_name,
            "workspace_exists": workspace_exists,
            "errors": errors,
        }


# Convenience functions for simple usage


def load_command_mapping(config_path: str | Path) -> OpencodeAdapter:
    """
    Load command mapping and create adapter (convenience function).

    Args:
        config_path: Path to command mapping YAML

    Returns:
        Initialized OpencodeAdapter

    Example:
        >>> adapter = load_command_mapping("plugins/opencode/opencode_sibyl_example.yaml")
        >>> result = adapter.execute("northwind.data_quality")
    """
    return OpencodeAdapter(config_path)


def resolve_command(config_path: str | Path, command_name: str) -> dict[str, Any]:
    """
    Quick command resolution without creating adapter instance.

    Args:
        config_path: Path to command mapping YAML
        command_name: Command to resolve

    Returns:
        Command configuration dictionary

    Example:
        >>> config = resolve_command("config.yaml", "northwind.data_quality")
        >>> print(config["workspace"])
    """
    adapter = OpencodeAdapter(config_path)
    return adapter.resolve_command(command_name)


def execute_command(
    config_path: str | Path,
    command_name: str,
    params: dict[str, Any] | None = None,
    timeout: int | None = 300,
) -> dict[str, Any]:
    """
    Execute a command directly (convenience function).

    Args:
        config_path: Path to command mapping YAML
        command_name: Command to execute
        params: Runtime parameters
        timeout: Execution timeout in seconds

    Returns:
        Pipeline execution result

    Example:
        >>> result = execute_command(
        ...     "config.yaml",
        ...     "northwind.data_quality",
        ...     {"question": "Why is revenue down?"}
        ... )
    """
    adapter = OpencodeAdapter(config_path)
    return adapter.execute(command_name, params, timeout)


__all__ = ["OpencodeAdapter", "execute_command", "load_command_mapping", "resolve_command"]
