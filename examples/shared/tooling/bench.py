#!/usr/bin/env python3
"""
Sibyl Examples Benchmarking Tool

Runs benchmarks across example scenarios, records timing, success/failure,
and generates reports in multiple formats.

Usage:
    python examples/shared/tooling/bench.py --help
    python examples/shared/tooling/bench.py --company all
    python examples/shared/tooling/bench.py --company riverbank_finance
    python examples/shared/tooling/bench.py --company all --output results.json
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    company: str
    scenario: str
    status: str  # success, failure, skipped
    duration_seconds: float
    timestamp: str
    artifacts_created: int
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class ExampleBenchmark:
    """Benchmark runner for Sibyl examples."""

    def __init__(self, examples_root: Path) -> None:
        self.examples_root = examples_root
        self.companies_dir = examples_root / "companies"
        self.results: list[BenchmarkResult] = []

    def discover_companies(self) -> list[str]:
        """Discover all company directories."""
        if not self.companies_dir.exists():
            return []

        companies = []
        for company_dir in self.companies_dir.iterdir():
            if company_dir.is_dir() and not company_dir.name.startswith("."):
                companies.append(company_dir.name)

        return sorted(companies)

    def discover_scenarios(self, company: str) -> list[str]:
        """Discover all scenarios for a company."""
        scenarios_dir = self.companies_dir / company / "scenarios"
        if not scenarios_dir.exists():
            return []

        scenarios = []
        for scenario_path in scenarios_dir.iterdir():
            if scenario_path.is_dir() and not scenario_path.name.startswith("."):
                scenarios.append(scenario_path.name)
            elif scenario_path.is_file() and scenario_path.suffix == ".py":
                scenarios.append(scenario_path.stem)

        return sorted(scenarios)

    def run_scenario_benchmark(
        self, company: str, scenario: str, dry_run: bool = False
    ) -> BenchmarkResult:
        """Run benchmark for a single scenario."""

        if dry_run:
            return BenchmarkResult(
                company=company,
                scenario=scenario,
                status="skipped",
                duration_seconds=0.0,
                timestamp=datetime.utcnow().isoformat(),
                artifacts_created=0,
                metadata={"dry_run": True},
            )

        start_time = time.time()
        scenario_path = self.companies_dir / company / "scenarios" / scenario

        try:
            # Check if scenario directory or file exists
            scenario_file = scenario_path.with_suffix(".py")
            if not scenario_path.exists() and not scenario_file.exists():
                return BenchmarkResult(
                    company=company,
                    scenario=scenario,
                    status="skipped",
                    duration_seconds=0.0,
                    timestamp=datetime.utcnow().isoformat(),
                    artifacts_created=0,
                    error_message="Scenario not found",
                )

            # TODO: Actually run the scenario
            # For now, we'll simulate by checking for expected artifacts
            artifacts_count = self._count_artifacts(company, scenario)

            duration = time.time() - start_time

            return BenchmarkResult(
                company=company,
                scenario=scenario,
                status="success",
                duration_seconds=duration,
                timestamp=datetime.utcnow().isoformat(),
                artifacts_created=artifacts_count,
            )

        except Exception as e:
            duration = time.time() - start_time
            return BenchmarkResult(
                company=company,
                scenario=scenario,
                status="failure",
                duration_seconds=duration,
                timestamp=datetime.utcnow().isoformat(),
                artifacts_created=0,
                error_message=str(e),
            )

    def _count_artifacts(self, company: str, scenario: str) -> int:
        """Count artifacts created by a scenario."""
        # Check common artifact locations
        output_dir = self.companies_dir / company / "scenarios" / scenario / "output"
        if output_dir.exists():
            return len(list(output_dir.rglob("*")))
        return 0

    def run_company_benchmarks(
        self, company: str, scenarios: list[str] | None = None, dry_run: bool = False
    ) -> list[BenchmarkResult]:
        """Run all benchmarks for a company."""

        if scenarios is None:
            scenarios = self.discover_scenarios(company)

        if not scenarios:
            return []

        results = []
        for scenario in scenarios:
            result = self.run_scenario_benchmark(company, scenario, dry_run)
            results.append(result)
            self.results.append(result)

        return results

    def run_all_benchmarks(self, companies: list[str] | None = None, dry_run: bool = False) -> None:
        """Run benchmarks for all companies."""
        if companies is None or "all" in companies:
            companies = self.discover_companies()

        if not companies:
            return

        for company in companies:
            self.run_company_benchmarks(company, dry_run=dry_run)

    def print_summary(self) -> None:
        """Print a summary of benchmark results."""
        if not self.results:
            return

        len(self.results)
        success = sum(1 for r in self.results if r.status == "success")
        sum(1 for r in self.results if r.status == "failure")
        sum(1 for r in self.results if r.status == "skipped")

        if success > 0:
            sum(r.duration_seconds for r in self.results if r.status == "success") / success

        # Group by company

        companies = {}
        for result in self.results:
            if result.company not in companies:
                companies[result.company] = []
            companies[result.company].append(result)

        for _company, results in sorted(companies.items()):
            sum(1 for r in results if r.status == "success")
            len(results)

            for result in results:
                {"success": "✓", "failure": "✗", "skipped": "○"}.get(result.status, "?")

                if result.error_message:
                    pass

    def save_json(self, output_path: Path) -> None:
        """Save results as JSON."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_scenarios": len(self.results),
            "results": [asdict(r) for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_csv(self, output_path: Path) -> None:
        """Save results as CSV."""
        if not self.results:
            return

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                ["Company", "Scenario", "Status", "Duration (s)", "Timestamp", "Artifacts", "Error"]
            )

            # Data rows
            for result in self.results:
                writer.writerow(
                    [
                        result.company,
                        result.scenario,
                        result.status,
                        f"{result.duration_seconds:.2f}",
                        result.timestamp,
                        result.artifacts_created,
                        result.error_message or "",
                    ]
                )

    def compare_with_baseline(self, baseline_path: Path) -> None:
        """Compare results with a baseline file."""
        if not baseline_path.exists():
            return

        with open(baseline_path) as f:
            baseline_data = json.load(f)

        baseline_results = {(r["company"], r["scenario"]): r for r in baseline_data["results"]}

        regressions = []
        improvements = []

        for result in self.results:
            key = (result.company, result.scenario)
            if key not in baseline_results:
                continue

            baseline = baseline_results[key]
            baseline_duration = baseline["duration_seconds"]
            current_duration = result.duration_seconds

            if current_duration > baseline_duration * 1.1:  # >10% slower
                diff = current_duration - baseline_duration
                pct = (diff / baseline_duration) * 100
                regressions.append((result, diff, pct))

            elif current_duration < baseline_duration * 0.9:  # >10% faster
                diff = baseline_duration - current_duration
                pct = (diff / baseline_duration) * 100
                improvements.append((result, diff, pct))

        if regressions:
            for result, diff, pct in regressions:
                pass

        if improvements:
            for result, diff, pct in improvements:
                pass

        if not regressions and not improvements:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Sibyl examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --company all
  %(prog)s --company riverbank_finance vertex_foundry
  %(prog)s --company all --output results.json
  %(prog)s --company all --output results.csv --format csv
  %(prog)s --company all --baseline baseline.json
  %(prog)s --dry-run
        """,
    )

    parser.add_argument(
        "--company", nargs="+", default=["all"], help="Companies to benchmark (default: all)"
    )

    parser.add_argument("--scenario", nargs="+", help="Specific scenarios to run (optional)")

    parser.add_argument("--output", type=Path, help="Output file for results")

    parser.add_argument(
        "--format",
        choices=["json", "csv", "text"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument("--baseline", type=Path, help="Baseline file for comparison")

    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (discover only, no execution)"
    )

    parser.add_argument(
        "--examples-root",
        type=Path,
        default=Path(__file__).parent.parent.parent,
        help="Root directory of examples (default: auto-detect)",
    )

    args = parser.parse_args()

    # Initialize benchmark runner
    benchmark = ExampleBenchmark(args.examples_root)

    # Discover and display available companies
    if args.dry_run:
        pass

    companies = benchmark.discover_companies()
    if not companies:
        sys.exit(1)

    if args.dry_run:
        for company in companies:
            scenarios = benchmark.discover_scenarios(company)
            for _scenario in scenarios:
                pass
            if not scenarios:
                pass
        sys.exit(0)

    # Run benchmarks
    benchmark.run_all_benchmarks(
        companies=args.company if args.company != ["all"] else None, dry_run=args.dry_run
    )

    # Print summary
    benchmark.print_summary()

    # Compare with baseline if provided
    if args.baseline:
        benchmark.compare_with_baseline(args.baseline)

    # Save results
    if args.output:
        if args.format == "json":
            benchmark.save_json(args.output)
        elif args.format == "csv":
            benchmark.save_csv(args.output)
        elif args.format == "text":
            # Text output is already printed to console
            pass


if __name__ == "__main__":
    main()
