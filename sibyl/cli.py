"""Sibyl CLI - Command-line interface for Sibyl workspace management.

This module provides command-line tools for:
- Validating workspace configurations
- Running pipelines
- Starting MCP servers
- Managing workspace deployments

Example:
    # Validate a workspace
    sibyl workspace validate --file config/workspaces/my_workspace.yaml

    # Run a pipeline
    sibyl pipeline run --workspace my_workspace --pipeline search --param query="test"

    # Start MCP server
    sibyl mcp serve --workspace config/workspaces/my_workspace.yaml
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from sibyl.runtime.pipeline import PipelineResult, WorkspaceRuntime
from sibyl.runtime.providers import build_providers
from sibyl.server.mcp_server import serve_mcp
from sibyl.workspace import (
    WorkspaceLoadError,
    get_workspace_info,
    load_workspace,
    validate_workspace_file,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Workspace Commands
# =============================================================================


def workspace_validate(args: argparse.Namespace) -> int:
    """Validate workspace configuration.

    Args:
        args: Parsed command-line arguments with 'file' attribute

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    file_path = args.file

    try:
        # Validate the workspace
        is_valid, _message = validate_workspace_file(file_path)

        if is_valid:
            # Load workspace to get details
            workspace = load_workspace(file_path)

            # Count providers
            provider_count = 0
            if workspace.providers.llm:
                provider_count += len(workspace.providers.llm)
            if workspace.providers.embeddings:
                provider_count += len(workspace.providers.embeddings)
            if workspace.providers.vector_store:
                provider_count += len(workspace.providers.vector_store)
            if workspace.providers.mcp:
                provider_count += len(workspace.providers.mcp)

            # List provider types
            if workspace.providers.llm:
                for _name in workspace.providers.llm:
                    pass

            if workspace.providers.embeddings:
                for _name in workspace.providers.embeddings:
                    pass

            if workspace.providers.vector_store:
                for _name in workspace.providers.vector_store:
                    pass

            # List shops
            if workspace.shops:
                for _shop_name, _shop_config in workspace.shops.items():
                    pass

            # List pipelines
            if workspace.pipelines:
                for _pipeline_name, _pipeline_config in workspace.pipelines.items():
                    pass

            return 0
        return 1

    except WorkspaceLoadError:
        return 1
    except Exception:
        logger.exception("Unexpected error during workspace validation")
        return 1


def workspace_info(args: argparse.Namespace) -> int:
    """Display workspace information.

    Args:
        args: Parsed command-line arguments with 'file' attribute

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    file_path = args.file

    try:
        get_workspace_info(file_path)

        return 0

    except WorkspaceLoadError:
        return 1


# =============================================================================
# Pipeline Commands
# =============================================================================


def pipeline_run(args: argparse.Namespace) -> int:
    """Run a pipeline once.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    pipeline_name = args.pipeline
    params = {}

    # Load parameters from file if provided
    if args.params_file:
        try:
            with open(args.params_file) as f:
                params = json.load(f)
        except FileNotFoundError:
            return 1
        except json.JSONDecodeError:
            return 1

    # Parse command-line parameters (override file params)
    if args.param:
        for param in args.param:
            if "=" not in param:
                return 1

            key, value = param.split("=", 1)

            # Try to parse as JSON for complex values
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                # If not JSON, use as string
                params[key] = value

    if params:
        pass

    try:
        # Load workspace
        workspace = load_workspace(workspace_path)

        # Build providers
        providers = build_providers(workspace)

        # Create runtime
        runtime = WorkspaceRuntime(workspace, providers)

        # Run pipeline
        result: PipelineResult = asyncio.run(runtime.run_pipeline_v2(pipeline_name, **params))

        # Format output based on requested format
        output_format = getattr(args, "format", "pretty")

        if output_format == "json":
            # JSON output
            return 0 if result.ok else 1

        if output_format == "yaml":
            # YAML output (requires pyyaml)
            try:
                import yaml  # optional dependency

            except ImportError:
                return 1
            return 0 if result.ok else 1

        # Pretty format (default)
        if result.ok:
            # Display results
            if "last_result" in result.data:
                last_result = result.data["last_result"]
                if isinstance(last_result, str):
                    pass
                else:
                    pass

            # Display other context data (excluding internal fields)
            exclude_keys = {
                "pipeline_name",
                "pipeline_shop",
                "last_result",
                "success",
                "trace_id",
            }
            other_data = {k: v for k, v in result.data.items() if k not in exclude_keys}

            if other_data and args.verbose:
                pass

            return 0

        if result.error.details and args.verbose:
            pass

        return 1

    except WorkspaceLoadError:
        return 1
    except Exception:
        if args.verbose:
            logger.exception("Pipeline execution error")
        return 1


def pipeline_list(args: argparse.Namespace) -> int:
    """List available pipelines in a workspace.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace

    try:
        workspace = load_workspace(workspace_path)

        if not workspace.pipelines:
            return 0

        for _pipeline_name, pipeline_config in workspace.pipelines.items():
            if pipeline_config.description:
                pass
            if pipeline_config.timeout_s:
                pass

        return 0

    except WorkspaceLoadError:
        return 1


def pipeline_info(args: argparse.Namespace) -> int:
    """Show detailed information about a pipeline.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    pipeline_name = args.pipeline

    try:
        workspace = load_workspace(workspace_path)
        providers = build_providers(workspace)
        runtime = WorkspaceRuntime(workspace, providers)

        # Get pipeline info
        info = runtime.get_pipeline_info(pipeline_name)

        if info is None:
            runtime.list_pipelines()
            return 1

        # Display pipeline info
        if info["description"]:
            pass
        if info["timeout_s"]:
            pass

        for _i, _step in enumerate(info["steps"], 1):
            pass

        return 0

    except WorkspaceLoadError:
        return 1


# =============================================================================
# HTTP Commands
# =============================================================================


def http_serve(args: argparse.Namespace) -> int:
    """Start HTTP API server.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    host = args.host
    port = args.port
    reload = args.reload

    try:
        from sibyl.server.http_server import start_server  # optional server dependency

        # This will block until server is stopped
        start_server(
            workspace_path=workspace_path,
            host=host,
            port=port,
            reload=reload,
            log_level=args.log_level.lower(),
        )
        return 0

    except KeyboardInterrupt:
        return 0
    except Exception:
        logger.exception("HTTP server error")
        return 1


# =============================================================================
# Validation Commands
# =============================================================================


def pipeline_validate(args: argparse.Namespace) -> int:
    """Validate pipeline configuration.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    pipeline_name = args.pipeline if hasattr(args, "pipeline") else None

    try:
        from sibyl.core.validation import PipelineValidator

        # Load workspace
        workspace = load_workspace(workspace_path)

        # Create validator
        validator = PipelineValidator(workspace)

        if pipeline_name:
            # Validate single pipeline
            result = validator.validate_pipeline(pipeline_name)

            # Display results
            if result.is_valid:
                pass
            else:
                pass

            # Display errors and warnings
            for error in result.errors:
                if error.suggestion:
                    pass

            return 0 if result.is_valid else 1

        # Validate all pipelines
        results = validator.validate_all_pipelines()

        valid_count = sum(1 for r in results.values() if r.is_valid)
        total_count = len(results)

        for _name, result in results.items():
            # Show errors for failed pipelines
            if not result.is_valid:
                for error in result.errors:
                    if error.severity.value == "error":
                        pass

        return 0 if valid_count == total_count else 1

    except WorkspaceLoadError:
        return 1
    except Exception:
        if args.verbose:
            logger.exception("Validation error")
        return 1


# =============================================================================
# Discovery Commands
# =============================================================================


def discover_providers(args: argparse.Namespace) -> int:
    """List MCP providers in workspace.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace

    try:
        from sibyl.core.discovery import WorkspaceDiscovery

        # Load workspace
        workspace = load_workspace(workspace_path)

        # Create discovery API
        discovery = WorkspaceDiscovery(workspace)

        # List providers
        providers = discovery.list_mcp_providers()

        for _provider in providers:
            pass

        return 0

    except WorkspaceLoadError:
        return 1
    except Exception:
        if args.verbose:
            logger.exception("Discovery error")
        return 1


def discover_tools(args: argparse.Namespace) -> int:
    """List MCP tools in workspace.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    provider_name = args.provider if hasattr(args, "provider") else None

    try:
        from sibyl.core.discovery import WorkspaceDiscovery

        # Load workspace
        workspace = load_workspace(workspace_path)

        # Create discovery API
        discovery = WorkspaceDiscovery(workspace)

        # List tools
        tools = discovery.list_mcp_tools(provider_name)

        if provider_name:
            pass
        else:
            pass

        # Group by provider
        by_provider: dict[str, List[Any]] = {}
        for tool in tools:
            if tool.provider not in by_provider:
                by_provider[tool.provider] = []
            by_provider[tool.provider].append(tool)

        for _prov_name, prov_tools in by_provider.items():
            for tool in prov_tools:
                pass

        return 0

    except WorkspaceLoadError:
        return 1
    except Exception:
        if args.verbose:
            logger.exception("Discovery error")
        return 1


def discover_artifacts(args: argparse.Namespace) -> int:
    """List available artifact types.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace

    try:
        from sibyl.core.discovery import WorkspaceDiscovery

        # Load workspace
        workspace = load_workspace(workspace_path)

        # Create discovery API
        discovery = WorkspaceDiscovery(workspace)

        # List artifacts
        artifacts = discovery.list_artifact_types()

        for _artifact in artifacts:
            pass

        return 0

    except WorkspaceLoadError:
        return 1
    except Exception:
        if args.verbose:
            logger.exception("Discovery error")
        return 1


# =============================================================================
# MCP Commands
# =============================================================================


def mcp_serve(args: argparse.Namespace) -> int:
    """Start MCP server.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workspace_path = args.workspace
    server_name = args.server_name

    if server_name:
        pass

    try:
        # This will block until server is stopped
        serve_mcp(workspace_path, server_name)
        return 0

    except KeyboardInterrupt:
        return 0
    except Exception:
        logger.exception("MCP server error")
        return 1


# =============================================================================
# Main CLI
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="sibyl",
        description="Sibyl - Universal AI Orchestration Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a workspace
  sibyl workspace validate --file config/workspaces/my_workspace.yaml

  # Run a pipeline
  sibyl pipeline run --workspace my_workspace.yaml --pipeline search --param query="test"

  # List pipelines
  sibyl pipeline list --workspace my_workspace.yaml

  # Start MCP server
  sibyl mcp serve --workspace config/workspaces/my_workspace.yaml

For more information, visit: https://github.com/yourusername/sibyl
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # -------------------------------------------------------------------------
    # Workspace commands
    # -------------------------------------------------------------------------
    workspace_parser = subparsers.add_parser("workspace", help="Workspace management commands")
    workspace_subparsers = workspace_parser.add_subparsers(
        dest="workspace_command", help="Workspace subcommand"
    )

    # workspace validate
    validate_parser = workspace_subparsers.add_parser(
        "validate", help="Validate workspace configuration"
    )
    validate_parser.add_argument("--file", "-f", required=True, help="Path to workspace YAML file")
    validate_parser.set_defaults(func=workspace_validate)

    # workspace info
    info_parser = workspace_subparsers.add_parser("info", help="Display workspace information")
    info_parser.add_argument("--file", "-f", required=True, help="Path to workspace YAML file")
    info_parser.set_defaults(func=workspace_info)

    # -------------------------------------------------------------------------
    # Pipeline commands
    # -------------------------------------------------------------------------
    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline execution commands")
    pipeline_subparsers = pipeline_parser.add_subparsers(
        dest="pipeline_command", help="Pipeline subcommand"
    )

    # pipeline run
    run_parser = pipeline_subparsers.add_parser("run", help="Run a pipeline")
    run_parser.add_argument("--workspace", "-w", required=True, help="Path to workspace YAML file")
    run_parser.add_argument("--pipeline", "-p", required=True, help="Pipeline name to execute")
    run_parser.add_argument(
        "--param",
        action="append",
        help="Pipeline parameter in format key=value (can be used multiple times)",
    )
    run_parser.add_argument(
        "--params-file",
        help="Path to JSON file containing pipeline parameters",
    )
    run_parser.add_argument(
        "--format",
        choices=["json", "yaml", "pretty"],
        default="pretty",
        help="Output format (default: pretty)",
    )
    run_parser.set_defaults(func=pipeline_run)

    # pipeline list
    list_parser = pipeline_subparsers.add_parser("list", help="List available pipelines")
    list_parser.add_argument("--workspace", "-w", required=True, help="Path to workspace YAML file")
    list_parser.set_defaults(func=pipeline_list)

    # pipeline info
    info_parser = pipeline_subparsers.add_parser("info", help="Show pipeline details")
    info_parser.add_argument("--workspace", "-w", required=True, help="Path to workspace YAML file")
    info_parser.add_argument("--pipeline", "-p", required=True, help="Pipeline name to inspect")
    info_parser.set_defaults(func=pipeline_info)

    # pipeline validate
    validate_pipeline_parser = pipeline_subparsers.add_parser(
        "validate", help="Validate pipeline configuration"
    )
    validate_pipeline_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    validate_pipeline_parser.add_argument(
        "--pipeline", "-p", help="Optional pipeline name (validates all if not specified)"
    )
    validate_pipeline_parser.set_defaults(func=pipeline_validate)

    # -------------------------------------------------------------------------
    # Discovery commands
    # -------------------------------------------------------------------------
    discover_parser = subparsers.add_parser("discover", help="Discover workspace capabilities")
    discover_subparsers = discover_parser.add_subparsers(
        dest="discover_command", help="Discovery subcommand"
    )

    # discover providers
    providers_parser = discover_subparsers.add_parser("providers", help="List MCP providers")
    providers_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    providers_parser.set_defaults(func=discover_providers)

    # discover tools
    tools_parser = discover_subparsers.add_parser("tools", help="List MCP tools")
    tools_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    tools_parser.add_argument("--provider", "-p", help="Optional provider name to filter tools")
    tools_parser.set_defaults(func=discover_tools)

    # discover artifacts
    artifacts_parser = discover_subparsers.add_parser("artifacts", help="List artifact types")
    artifacts_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    artifacts_parser.set_defaults(func=discover_artifacts)

    # -------------------------------------------------------------------------
    # HTTP commands
    # -------------------------------------------------------------------------
    http_parser = subparsers.add_parser("http", help="HTTP API server commands")
    http_subparsers = http_parser.add_subparsers(dest="http_command", help="HTTP subcommand")

    # http serve
    http_serve_parser = http_subparsers.add_parser("serve", help="Start HTTP API server")
    http_serve_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    # S104: 0.0.0.0 default is intentional for flexibility
    # Users can override with --host 127.0.0.1 for local-only access
    http_serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0, use 127.0.0.1 for local only)",
    )
    http_serve_parser.add_argument(
        "--port", "-p", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    http_serve_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    http_serve_parser.set_defaults(func=http_serve)

    # -------------------------------------------------------------------------
    # MCP commands
    # -------------------------------------------------------------------------
    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", help="MCP subcommand")

    # mcp serve
    serve_parser = mcp_subparsers.add_parser("serve", help="Start MCP server")
    serve_parser.add_argument(
        "--workspace", "-w", required=True, help="Path to workspace YAML file"
    )
    serve_parser.add_argument("--server-name", help="Optional server name override")
    serve_parser.set_defaults(func=mcp_serve)

    return parser


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if hasattr(args, "func"):
        return args.func(args)
    # Subcommand not provided
    if args.command == "workspace":
        parser.parse_args(["workspace", "--help"])
    elif args.command == "pipeline":
        parser.parse_args(["pipeline", "--help"])
    elif args.command == "http":
        parser.parse_args(["http", "--help"])
    elif args.command == "mcp":
        parser.parse_args(["mcp", "--help"])
    elif args.command == "discover":
        parser.parse_args(["discover", "--help"])
    else:
        parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
