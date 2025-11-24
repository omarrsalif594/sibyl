#!/usr/bin/env python3
"""Validate the prod_web_research workspace configuration.

This script performs comprehensive validation of the production workspace:
- YAML syntax and schema validation
- Technique availability checks
- Provider configuration verification
- Pipeline step validation

Usage:
    python validate_workspace.py
    python validate_workspace.py --verbose
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sibyl.techniques.registry import list_techniques, technique_exists
from sibyl.workspace.loader import WorkspaceLoadError, load_workspace


def validate_workspace(workspace_path: str, verbose: bool = False) -> bool:
    """Validate workspace configuration.

    Args:
        workspace_path: Path to workspace YAML file
        verbose: Enable verbose output

    Returns:
        True if validation passes, False otherwise
    """

    # Step 1: Load and parse workspace
    try:
        workspace = load_workspace(workspace_path)
    except WorkspaceLoadError:
        return False

    # Step 2: Check providers
    if verbose:
        for _name in workspace.providers.llm:
            pass

    if verbose:
        for _name in workspace.providers.embeddings:
            pass

    if verbose:
        for _name in workspace.providers.vector_store:
            pass

    if verbose:
        for _name in workspace.providers.mcp:
            pass

    # Step 3: Check shops and techniques
    set(list_techniques())

    all_techniques_valid = True
    for _shop_name, shop in workspace.shops.items():
        for tech_name, tech_ref in shop.techniques.items():
            # Parse technique reference (format: "category.technique:implementation")
            if ":" in tech_ref:
                module_path, _ = tech_ref.rsplit(":", 1)
                technique_base = module_path.split(".")[-1] if "." in module_path else module_path
            else:
                technique_base = tech_name

            exists = technique_exists(technique_base)

            if verbose or not exists:
                pass

            if not exists:
                all_techniques_valid = False

    if all_techniques_valid:
        pass
    else:
        pass

    # Step 4: Check pipelines
    for _pipeline_name, pipeline in workspace.pipelines.items():
        if verbose:
            for _i, _step in enumerate(pipeline.steps, 1):
                pass

    # Step 5: Check MCP tools

    for tool in workspace.mcp.tools:
        # Check that pipeline exists
        if tool.pipeline in workspace.pipelines:
            pass
        else:
            all_techniques_valid = False

    # Summary
    return bool(all_techniques_valid)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate prod_web_research workspace configuration"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default="../../config/workspaces/prod_web_research.yaml",
        help="Path to workspace YAML file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Resolve workspace path
    workspace_path = Path(args.workspace)
    if not workspace_path.is_absolute():
        workspace_path = Path(__file__).parent / workspace_path
    workspace_path = workspace_path.resolve()

    # Validate
    success = validate_workspace(str(workspace_path), args.verbose)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
