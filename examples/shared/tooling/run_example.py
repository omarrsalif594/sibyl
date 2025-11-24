#!/usr/bin/env python3
"""
Sibyl Examples Runner

Helper script to run company examples with proper configuration and error handling.

Usage:
    python examples/shared/tooling/run_example.py --company acme_retail --scenario 01_daily_sales
    python examples/shared/tooling/run_example.py --company acme_retail --list
    python examples/shared/tooling/run_example.py --company acme_retail --scenario 01_daily_sales --preview

IMPORTANT: All examples use synthetic data for demonstration purposes only.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(1)


class ExampleRunner:
    """Run Sibyl examples with proper configuration and validation"""

    def __init__(self, examples_dir: Path | None = None) -> None:
        """
        Initialize the example runner

        Args:
            examples_dir: Path to examples directory (auto-detected if None)
        """
        if examples_dir is None:
            # Auto-detect examples directory
            script_dir = Path(__file__).parent
            self.examples_dir = script_dir.parent.parent
        else:
            self.examples_dir = Path(examples_dir)

        self.companies_dir = self.examples_dir / "companies"

        if not self.companies_dir.exists():
            msg = f"Companies directory not found: {self.companies_dir}"
            raise RuntimeError(msg)

    def list_companies(self) -> list[str]:
        """List all available company examples"""
        if not self.companies_dir.exists():
            return []

        companies = [
            d.name
            for d in self.companies_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        return sorted(companies)

    def get_company_dir(self, company: str) -> Path:
        """Get path to company directory"""
        company_dir = self.companies_dir / company

        if not company_dir.exists():
            msg = f"Company '{company}' not found. Available: {', '.join(self.list_companies())}"
            raise ValueError(msg)

        return company_dir

    def list_scenarios(self, company: str) -> list[dict[str, str]]:
        """
        List all scenarios for a company

        Returns:
            List of dicts with keys: id, name, file, description
        """
        company_dir = self.get_company_dir(company)
        scenarios_dir = company_dir / "scenarios"

        if not scenarios_dir.exists():
            return []

        scenarios = []
        for scenario_file in sorted(scenarios_dir.glob("*.md")):
            if scenario_file.name == "README.md":
                continue

            scenario_id = scenario_file.stem
            scenario_name = self._extract_scenario_name(scenario_file)

            scenarios.append(
                {
                    "id": scenario_id,
                    "name": scenario_name,
                    "file": str(scenario_file),
                }
            )

        return scenarios

    def _extract_scenario_name(self, scenario_file: Path) -> str:
        """Extract scenario name from markdown file"""
        try:
            with open(scenario_file) as f:
                for line in f:
                    if line.startswith("# "):
                        return line[2:].strip()
        except Exception:
            logging.debug(f"Could not read title from {scenario_file}")
        return scenario_file.stem.replace("_", " ").title()

    def get_workspace_config(self, company: str, workspace: Path | None = None) -> Path:
        """Get path to workspace configuration"""
        if workspace:
            workspace_path = Path(workspace)
            if not workspace_path.exists():
                msg = f"Workspace file not found: {workspace_path}"
                raise ValueError(msg)
            return workspace_path

        company_dir = self.get_company_dir(company)
        workspace_path = company_dir / "config" / "workspace.yaml"

        if not workspace_path.exists():
            msg = f"Default workspace.yaml not found for {company}: {workspace_path}"
            raise ValueError(msg)

        return workspace_path

    def load_pipelines(self, company: str) -> dict:
        """Load pipeline definitions for a company"""
        company_dir = self.get_company_dir(company)
        pipelines_path = company_dir / "config" / "pipelines.yaml"

        if not pipelines_path.exists():
            msg = f"pipelines.yaml not found for {company}: {pipelines_path}"
            raise ValueError(msg)

        try:
            with open(pipelines_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            msg = f"Failed to load pipelines.yaml: {e}"
            raise ValueError(msg) from e

    def get_scenario_pipeline(self, company: str, scenario: str) -> str | None:
        """
        Try to determine which pipeline corresponds to a scenario

        Returns:
            Pipeline ID or None if not found
        """
        pipelines = self.load_pipelines(company)

        # Strategy 1: Look for pipeline with matching scenario metadata
        for pipeline_id, pipeline_config in pipelines.get("pipelines", {}).items():
            metadata = pipeline_config.get("metadata", {})
            if metadata.get("scenario") == scenario:
                return pipeline_id

        # Strategy 2: Try to match scenario name to pipeline name
        scenario_base = scenario.split("_", 1)[-1] if "_" in scenario else scenario
        for pipeline_id in pipelines.get("pipelines", {}):
            if scenario_base in pipeline_id:
                return pipeline_id

        return None

    def run_pipeline(  # noqa: PLR0913
        self,
        company: str,
        pipeline_id: str,
        workspace: Path | None = None,
        params: dict | None = None,
        preview: bool = False,
        log_level: str = "INFO",
    ) -> subprocess.CompletedProcess:
        """
        Run a Sibyl pipeline for a company example

        Args:
            company: Company name
            pipeline_id: Pipeline ID to run
            workspace: Optional custom workspace path
            params: Optional pipeline parameters
            preview: If True, run in preview mode without execution
            log_level: Log level (DEBUG, INFO, WARNING, ERROR)

        Returns:
            subprocess.CompletedProcess with execution results
        """
        workspace_path = self.get_workspace_config(company, workspace)

        # Build command
        cmd = [
            "sibyl",
            "pipeline",
            "run",
            "--workspace",
            str(workspace_path),
            "--pipeline-id",
            pipeline_id,
        ]

        if params:
            cmd.extend(["--params", json.dumps(params)])

        if preview:
            cmd.append("--preview")

        if log_level != "INFO":
            cmd.extend(["--log-level", log_level])

        # Print command for user

        # Execute
        try:
            return subprocess.run(
                cmd,
                check=False,
                cwd=self.get_company_dir(company),
                capture_output=False,
                text=True,
            )
        except FileNotFoundError:
            sys.exit(1)
        except Exception:
            sys.exit(1)

    def run_scenario(  # noqa: PLR0913
        self,
        company: str,
        scenario: str,
        workspace: Path | None = None,
        params: dict | None = None,
        preview: bool = False,
        log_level: str = "INFO",
    ) -> subprocess.CompletedProcess:
        """
        Run a scenario by finding and executing its pipeline

        Args:
            company: Company name
            scenario: Scenario ID (e.g., "01_daily_sales")
            workspace: Optional custom workspace path
            params: Optional pipeline parameters
            preview: If True, run in preview mode
            log_level: Log level

        Returns:
            subprocess.CompletedProcess with execution results
        """
        # Find pipeline for scenario
        pipeline_id = self.get_scenario_pipeline(company, scenario)

        if not pipeline_id:
            pipelines = self.load_pipelines(company)
            for _pid in pipelines.get("pipelines", {}):
                pass
            sys.exit(1)

        return self.run_pipeline(
            company=company,
            pipeline_id=pipeline_id,
            workspace=workspace,
            params=params,
            preview=preview,
            log_level=log_level,
        )

    def print_company_info(self, company: str) -> None:
        """Print information about a company"""
        company_dir = self.get_company_dir(company)
        readme_path = company_dir / "README.md"

        # Print README excerpt if available
        if readme_path.exists():
            with open(readme_path) as f:
                lines = f.readlines()
                # Print first paragraph after title
                in_overview = False
                for line in lines[:30]:  # First 30 lines
                    if line.startswith("# "):
                        pass
                    elif line.startswith("## "):
                        if in_overview:
                            break
                        if "background" in line.lower() or "overview" in line.lower():
                            in_overview = True
                    elif in_overview and line.strip():
                        pass

    def print_scenarios_list(self, company: str) -> None:
        """Print list of available scenarios"""
        scenarios = self.list_scenarios(company)

        if not scenarios:
            return

        for _scenario in scenarios:
            pass


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run Sibyl company examples with proper configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all companies
  %(prog)s --list-companies

  # Show company info and scenarios
  %(prog)s --company acme_retail --list

  # Run a scenario
  %(prog)s --company acme_retail --scenario 01_daily_sales

  # Run with custom parameters
  %(prog)s --company acme_retail --scenario 01_daily_sales --params '{"date":"2024-01-15"}'

  # Preview mode (no execution)
  %(prog)s --company acme_retail --scenario 01_daily_sales --preview

  # Run with debug logging
  %(prog)s --company acme_retail --scenario 01_daily_sales --log-level DEBUG

  # Run specific pipeline directly
  %(prog)s --company acme_retail --pipeline-id daily_sales_pipeline

IMPORTANT: All examples use synthetic data for demonstration purposes only.
        """,
    )

    parser.add_argument(
        "--company",
        type=str,
        help="Company name (e.g., acme_retail)",
    )

    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario ID to run (e.g., 01_daily_sales)",
    )

    parser.add_argument(
        "--pipeline-id",
        type=str,
        help="Pipeline ID to run directly (alternative to --scenario)",
    )

    parser.add_argument(
        "--workspace",
        type=Path,
        help="Path to custom workspace.yaml (default: config/workspace.yaml)",
    )

    parser.add_argument(
        "--params",
        type=str,
        help='Pipeline parameters as JSON (e.g., \'{"date":"2024-01-15"}\')',
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Run in preview mode without execution",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List scenarios for specified company",
    )

    parser.add_argument(
        "--list-companies",
        action="store_true",
        help="List all available companies",
    )

    parser.add_argument(
        "--examples-dir",
        type=Path,
        help="Path to examples directory (auto-detected by default)",
    )

    args = parser.parse_args()

    # Initialize runner
    try:
        runner = ExampleRunner(examples_dir=args.examples_dir)
    except Exception:
        sys.exit(1)

    # Handle list-companies
    if args.list_companies:
        companies = runner.list_companies()
        if not companies:
            sys.exit(1)

        for _company in companies:
            pass
        return

    # Require company for other operations
    if not args.company:
        parser.error("--company is required (or use --list-companies)")

    # Handle list scenarios
    if args.list:
        runner.print_company_info(args.company)
        runner.print_scenarios_list(args.company)
        return

    # Parse params if provided
    params = None
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError:
            sys.exit(1)

    # Run pipeline or scenario
    try:
        if args.pipeline_id:
            # Run pipeline directly
            result = runner.run_pipeline(
                company=args.company,
                pipeline_id=args.pipeline_id,
                workspace=args.workspace,
                params=params,
                preview=args.preview,
                log_level=args.log_level,
            )
        elif args.scenario:
            # Run scenario
            result = runner.run_scenario(
                company=args.company,
                scenario=args.scenario,
                workspace=args.workspace,
                params=params,
                preview=args.preview,
                log_level=args.log_level,
            )
        else:
            parser.error("Either --scenario or --pipeline-id is required")

        sys.exit(result.returncode)

    except ValueError:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
