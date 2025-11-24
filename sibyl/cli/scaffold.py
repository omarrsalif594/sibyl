"""
CLI scaffolding helper for Sibyl workspace templates.

Provides interactive template scaffolding with customization prompts.

Usage:
    sibyl workspace scaffold --template local_dev --output my_workspace.yaml
    sibyl workspace scaffold --template code_assistant --output my_workspace.yaml --interactive
"""

import contextlib
import sys
from pathlib import Path
from typing import Any

import yaml

# Template directory (relative to this file)
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "config" / "workspaces"

# Available templates with descriptions
AVAILABLE_TEMPLATES = {
    "local_dev": {
        "description": "Local development and testing (no external APIs)",
        "providers": ["echo_llm", "sentence_transformer"],
        "complexity": "low",
    },
    "prod_web_research": {
        "description": "Production web research with RAG",
        "providers": ["openai"],
        "complexity": "high",
    },
    "cloud_rag": {
        "description": "Cloud-based RAG system",
        "providers": ["openai", "anthropic"],
        "complexity": "medium",
    },
    "agentic_research": {
        "description": "Multi-agent research system",
        "providers": ["openai", "anthropic"],
        "complexity": "high",
    },
    "code_assistant": {
        "description": "Code analysis and generation",
        "providers": ["openai", "anthropic"],
        "complexity": "medium",
    },
    "evaluation_pipeline": {
        "description": "Evaluation and benchmarking",
        "providers": ["openai", "anthropic"],
        "complexity": "high",
    },
}


class WorkspaceScaffold:
    """Helper for scaffolding workspaces from templates."""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}

    def list_templates(self) -> None:
        """List available templates."""
        for _name, info in AVAILABLE_TEMPLATES.items():
            (
                "🟢"
                if info["complexity"] == "low"
                else "🟡"
                if info["complexity"] == "medium"
                else "🔴"
            )

    def validate_template(self, template_name: str) -> bool:
        """Validate template name."""
        return template_name in AVAILABLE_TEMPLATES

    def get_template_path(self, template_name: str) -> Path:
        """Get path to template file."""
        template_file = f"{template_name}.yaml"
        template_path = TEMPLATES_DIR / template_file
        if not template_path.exists():
            # Try with hyphens converted to underscores
            alt_template = template_name.replace("_", "-")
            alt_path = TEMPLATES_DIR / f"{alt_template}.yaml"
            if alt_path.exists():
                return alt_path
        return template_path

    def load_template(self, template_name: str) -> dict[str, Any]:
        """Load template configuration."""
        template_path = self.get_template_path(template_name)

        if not template_path.exists():
            msg = f"Template file not found: {template_path}"
            raise FileNotFoundError(msg)

        with open(template_path) as f:
            return yaml.safe_load(f)

    def prompt_customization(self, template: dict[str, Any]) -> None:
        """Interactively prompt for customizations."""

        # Workspace name
        default_name = template.get("name", "custom-workspace")
        name = input(f"Workspace name [{default_name}]: ").strip() or default_name
        template["name"] = name

        # Description
        default_desc = template.get("description", "")
        desc = input(f"Description [{default_desc}]: ").strip() or default_desc
        if desc:
            template["description"] = desc

        # LLM provider customization
        if "providers" in template and "llm" in template["providers"]:
            self._customize_llm_providers(template)

        # Budget customization
        if "budget" in template:
            self._customize_budget(template)

    def _customize_llm_providers(self, template: dict[str, Any]) -> None:
        """Customize LLM providers."""

        llm_providers = template["providers"]["llm"]
        for provider_name in list(llm_providers.keys())[:1]:  # Just the default
            provider = llm_providers[provider_name]

            # Ask about provider type
            provider_type = input(
                "  Provider type [openai/anthropic/local] (leave blank to skip): "
            ).strip()

            if provider_type:
                provider["provider"] = provider_type

                if provider_type == "anthropic":
                    provider["model"] = "claude-3-5-sonnet-20241022"
                    provider["api_key_env"] = "ANTHROPIC_API_KEY"
                elif provider_type == "openai":
                    model = (
                        input("  Model [gpt-4/gpt-3.5-turbo] (default: gpt-4): ").strip() or "gpt-4"
                    )
                    provider["model"] = model
                    provider["api_key_env"] = "OPENAI_API_KEY"

    def _customize_budget(self, template: dict[str, Any]) -> None:
        """Customize budget settings."""

        budget = template.get("budget", {})

        # Max cost
        current_cost = budget.get("max_cost_usd", 5.0)
        cost_str = input(f"Max cost USD [{current_cost}]: ").strip()
        if cost_str:
            with contextlib.suppress(ValueError):
                budget["max_cost_usd"] = float(cost_str)

        # Max tokens
        current_tokens = budget.get("max_tokens", 100000)
        tokens_str = input(f"Max tokens [{current_tokens}]: ").strip()
        if tokens_str:
            with contextlib.suppress(ValueError):
                budget["max_tokens"] = int(tokens_str)

        template["budget"] = budget

    def scaffold(
        self,
        template_name: str,
        output_path: str,
        interactive: bool = False,
        force: bool = False,
    ) -> bool:
        """Scaffold a new workspace from template.

        Args:
            template_name: Name of template to use
            output_path: Path where to write the new workspace file
            interactive: Whether to prompt for customizations
            force: Whether to overwrite existing file

        Returns:
            True if successful, False otherwise
        """
        # Validate template
        if not self.validate_template(template_name):
            return False

        # Check output path
        output_file = Path(output_path)
        if output_file.exists() and not force:
            response = input(f"File {output_file} already exists. Overwrite? [y/N]: ").strip()
            if response.lower() != "y":
                return False

        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Load template
        try:
            template = self.load_template(template_name)
        except FileNotFoundError:
            return False

        # Interactive customization
        if interactive:
            self.prompt_customization(template)

        # Write output file
        try:
            with open(output_file, "w") as f:
                yaml.dump(template, f, default_flow_style=False, sort_keys=False)
            return True
        except OSError:
            return False

    @staticmethod
    def print_help() -> None:
        """Print usage help."""
        scaffold = WorkspaceScaffold()
        scaffold.list_templates()


def main(args: list | None = None) -> int:
    """Main entry point for scaffold CLI.

    Args:
        args: Command line arguments (sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if args is None:
        args = sys.argv[1:]

    scaffold = WorkspaceScaffold()

    # Handle help
    if not args or "--help" in args or "-h" in args:
        scaffold.print_help()
        return 0

    # Handle list
    if "--list" in args:
        scaffold.list_templates()
        return 0

    # Parse arguments
    template_name = None
    output_path = None
    interactive = False
    force = False

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--template":
            if i + 1 < len(args):
                template_name = args[i + 1]
                i += 2
            else:
                return 1

        elif arg == "--output":
            if i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
            else:
                return 1

        elif arg in ("--interactive", "-i"):
            interactive = True
            i += 1

        elif arg in ("--force", "-f"):
            force = True
            i += 1

        else:
            return 1

    # Validate required arguments
    if not template_name:
        return 1

    if not output_path:
        return 1

    # Run scaffolding
    success = scaffold.scaffold(
        template_name=template_name,
        output_path=output_path,
        interactive=interactive,
        force=force,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
