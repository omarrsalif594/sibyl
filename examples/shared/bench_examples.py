#!/usr/bin/env python3
"""
Sibyl Examples Benchmarking & CI Integration
============================================

This script provides performance baselines and CI-ready benchmark execution
for all example companies in the Sibyl project.

Usage:
    # Run all benchmarks (full mode)
    python examples/shared/bench_examples.py

    # Run CI-optimized benchmarks (fast, essential tests only)
    python examples/shared/bench_examples.py --mode=ci

    # Generate new baseline
    python examples/shared/bench_examples.py --mode=full --write-baseline=examples/shared/benchmarks/baseline.json

    # Compare against baseline
    python examples/shared/bench_examples.py --compare=examples/shared/benchmarks/baseline.json

    # Run specific company benchmarks
    python examples/shared/bench_examples.py --company=northwind_analytics

    # Dry run to see what would be tested
    python examples/shared/bench_examples.py --dry-run

Features:
    - Measures runtime, steps executed, and status for each pipeline
    - Supports CI and full benchmark modes
    - Generates JSON baseline files for regression tracking
    - Compares current results against baseline
    - Tracks MCP calls and memory usage (when available)
"""

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.examples.conftest import run_example_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Benchmark Configuration
# ============================================================================


@dataclass
class BenchmarkConfig:
    """Configuration for a single pipeline benchmark."""

    company: str
    pipeline: str
    workspace_path: str
    params: dict[str, Any]
    skip_ci: bool = False  # Skip in CI mode if True
    requires_mcp: bool = False  # Requires MCP server if True
    timeout_s: int = 300
    description: str = ""


# Curated benchmark suite
# These are fast, representative pipelines from each company
BENCHMARKS: list[BenchmarkConfig] = [
    # Northwind Analytics - BI/Analytics SaaS
    BenchmarkConfig(
        company="northwind_analytics",
        pipeline="revenue_analysis",
        workspace_path="examples/companies/northwind_analytics/config/workspace.yaml",
        params={"question": "What are the key revenue trends in Q3?", "time_period": "2024-Q3"},
        skip_ci=False,
        requires_mcp=False,
        timeout_s=180,
        description="Analyze revenue trends with SQL + RAG",
    ),
    BenchmarkConfig(
        company="northwind_analytics",
        pipeline="explain_dashboard",
        workspace_path="examples/companies/northwind_analytics/config/workspace.yaml",
        params={"dashboard_name": "Revenue Overview", "audience": "new product manager"},
        skip_ci=False,
        requires_mcp=False,
        timeout_s=120,
        description="Pure RAG pipeline for documentation",
    ),
    # RiverBank Finance - Compliance/Fintech
    BenchmarkConfig(
        company="riverbank_finance",
        pipeline="code_compliance_check",
        workspace_path="examples/companies/riverbank_finance/config/workspace.yaml",
        params={"file_path": "data/code/interest_calculator.py", "policy_reference": "INT-001"},
        skip_ci=True,  # Requires AST MCP server
        requires_mcp=True,
        timeout_s=240,
        description="Code compliance analysis with AST parsing",
    ),
    BenchmarkConfig(
        company="riverbank_finance",
        pipeline="risk_graph_analysis",
        workspace_path="examples/companies/riverbank_finance/config/workspace.yaml",
        params={
            "transaction_file": "data/transactions/sample_transactions.json",
            "metric_type": "pagerank",
            "top_n": 10,
        },
        skip_ci=True,  # Requires Graphiti MCP
        requires_mcp=True,
        timeout_s=300,
        description="Transaction graph risk analysis with Graphiti",
    ),
    # Vertex Foundry - ML Ops
    BenchmarkConfig(
        company="vertex_foundry",
        pipeline="hyperparameter_sweep",
        workspace_path="examples/companies/vertex_foundry/config/pipelines.yaml",
        params={
            "budget_usd": 100,
            "param_space": {"learning_rate": [0.001, 0.01], "batch_size": [32, 64]},
            "target_metric": "val_acc",
        },
        skip_ci=True,  # Long-running, requires Conductor MCP
        requires_mcp=True,
        timeout_s=600,
        description="Hyperparameter optimization with job polling",
    ),
    # BrightOps Agency - Knowledge work
    BenchmarkConfig(
        company="brightops_agency",
        pipeline="meeting_to_plan",
        workspace_path="examples/companies/brightops_agency/config/pipelines.yaml",
        params={"meeting_file": "data/meetings/project_kickoff.md"},
        skip_ci=True,  # Requires Sequential Thinking MCP
        requires_mcp=True,
        timeout_s=300,
        description="Convert meeting notes to structured plan",
    ),
    BenchmarkConfig(
        company="brightops_agency",
        pipeline="learn_preferences",
        workspace_path="examples/companies/brightops_agency/config/pipelines.yaml",
        params={"email_file": "data/emails/client_communications.md"},
        skip_ci=True,  # Requires MCP
        requires_mcp=True,
        timeout_s=180,
        description="Pattern learning from client emails",
    ),
]


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class PipelineBenchmarkResult:
    """Result of benchmarking a single pipeline."""

    company: str
    pipeline: str
    status: str  # "completed", "failed", "skipped", "timeout"
    runtime_ms: int
    steps_executed: int | None = None
    mcp_calls: int | None = None
    memory_mb: float | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class BenchmarkSuiteResult:
    """Overall results from benchmark suite."""

    timestamp: str
    mode: str  # "ci" or "full"
    total: int
    completed: int
    failed: int
    skipped: int
    total_runtime_ms: int
    pipelines: list[PipelineBenchmarkResult]


# ============================================================================
# Benchmark Execution
# ============================================================================


class BenchmarkRunner:
    """Runs and manages benchmark execution."""

    def __init__(self, mode: str = "full", dry_run: bool = False) -> None:
        """
        Initialize benchmark runner.

        Args:
            mode: "ci" (fast, essential tests) or "full" (all benchmarks)
            dry_run: If True, only print what would be run
        """
        self.mode = mode
        self.dry_run = dry_run
        self.results: list[PipelineBenchmarkResult] = []
        self.project_root = PROJECT_ROOT

    def should_run_benchmark(self, config: BenchmarkConfig) -> tuple[bool, str]:
        """
        Determine if a benchmark should run.

        Returns:
            (should_run, skip_reason)
        """
        # Check CI mode
        if self.mode == "ci" and config.skip_ci:
            return False, "Skipped in CI mode"

        # Check MCP requirements
        if config.requires_mcp:
            # In real implementation, check if MCP servers are available
            # For now, skip MCP-required benchmarks unless in full mode
            if self.mode == "ci":
                return False, "Requires MCP server (not available in CI)"

        # Check workspace file exists
        workspace_path = self.project_root / config.workspace_path
        if not workspace_path.exists():
            return False, f"Workspace file not found: {workspace_path}"

        return True, ""

    def run_single_benchmark(self, config: BenchmarkConfig) -> PipelineBenchmarkResult:
        """Run a single pipeline benchmark."""
        should_run, skip_reason = self.should_run_benchmark(config)

        if not should_run:
            logger.info("  SKIP: %s/%s - %s", config.company, config.pipeline, skip_reason)
            return PipelineBenchmarkResult(
                company=config.company,
                pipeline=config.pipeline,
                status="skipped",
                runtime_ms=0,
                error_message=skip_reason,
            )

        if self.dry_run:
            logger.info("  DRY RUN: %s/%s", config.company, config.pipeline)
            return PipelineBenchmarkResult(
                company=config.company,
                pipeline=config.pipeline,
                status="skipped",
                runtime_ms=0,
                metadata={"dry_run": True},
            )

        logger.info("  RUN: %s/%s", config.company, config.pipeline)
        logger.debug("       Description: %s", config.description)

        # Resolve workspace path
        workspace_path = str(self.project_root / config.workspace_path)

        # Track start time
        start_time = time.time()

        try:
            # Run the pipeline using conftest helper
            result = run_example_pipeline(
                workspace_path=workspace_path,
                pipeline_name=config.pipeline,
                params=config.params,
                timeout=config.timeout_s,
            )

            # Calculate runtime
            runtime_ms = int((time.time() - start_time) * 1000)

            # Extract metrics from result
            status = result.get("status", "unknown")
            steps_executed = len(result.get("step_results", []))

            # Count MCP calls if available
            mcp_calls = None
            if "metadata" in result and "mcp_calls" in result["metadata"]:
                mcp_calls = result["metadata"]["mcp_calls"]

            # Extract error if failed
            error_message = None
            if status in ["failed", "error", "timeout"]:
                error_message = result.get("error", "Unknown error")

            # Log result
            if status in ["completed", "ok", "success"]:
                logger.info("       OK: %sms (%s steps)", runtime_ms, steps_executed)
                status = "completed"
            else:
                logger.warning("       FAILED: %s", error_message)

            return PipelineBenchmarkResult(
                company=config.company,
                pipeline=config.pipeline,
                status=status,
                runtime_ms=runtime_ms,
                steps_executed=steps_executed,
                mcp_calls=mcp_calls,
                error_message=error_message,
                metadata=result.get("metadata", {}),
            )

        except Exception as e:
            runtime_ms = int((time.time() - start_time) * 1000)
            error_message = f"{type(e).__name__}: {e!s}"
            logger.exception("       ERROR: %s", error_message)
            logger.debug(traceback.format_exc())

            return PipelineBenchmarkResult(
                company=config.company,
                pipeline=config.pipeline,
                status="failed",
                runtime_ms=runtime_ms,
                error_message=error_message,
            )

    def run_all_benchmarks(self, filter_company: str | None = None) -> BenchmarkSuiteResult:
        """
        Run all benchmarks (or filtered subset).

        Args:
            filter_company: If provided, only run benchmarks for this company

        Returns:
            BenchmarkSuiteResult with aggregated results
        """
        logger.info("\nStarting benchmark suite (mode=%s)", self.mode)
        logger.info("=" * 80)

        # Filter benchmarks
        benchmarks_to_run = BENCHMARKS
        if filter_company:
            benchmarks_to_run = [b for b in BENCHMARKS if b.company == filter_company]
            if not benchmarks_to_run:
                logger.error("No benchmarks found for company: %s", filter_company)
                sys.exit(1)

        logger.info("Total benchmarks: %s\n", len(benchmarks_to_run))

        # Run each benchmark
        suite_start_time = time.time()

        for config in benchmarks_to_run:
            result = self.run_single_benchmark(config)
            self.results.append(result)

        total_runtime_ms = int((time.time() - suite_start_time) * 1000)

        # Aggregate results
        completed = sum(1 for r in self.results if r.status == "completed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        return BenchmarkSuiteResult(
            timestamp=datetime.utcnow().isoformat() + "Z",
            mode=self.mode,
            total=len(self.results),
            completed=completed,
            failed=failed,
            skipped=skipped,
            total_runtime_ms=total_runtime_ms,
            pipelines=self.results,
        )

    def print_summary(self, suite_result: BenchmarkSuiteResult) -> None:
        """Print human-readable summary."""

        # Group by company
        by_company: dict[str, list[PipelineBenchmarkResult]] = {}
        for result in suite_result.pipelines:
            if result.company not in by_company:
                by_company[result.company] = []
            by_company[result.company].append(result)

        for company in sorted(by_company.keys()):
            results = by_company[company]
            sum(1 for r in results if r.status == "completed")

            for result in results:
                {"completed": "✓", "failed": "✗", "skipped": "○", "timeout": "⏱"}.get(
                    result.status, "?"
                )

                f"{result.runtime_ms}ms".rjust(8)

                if result.error_message and result.status not in ["skipped"]:
                    # Truncate long error messages
                    error = result.error_message[:100]
                    if len(result.error_message) > 100:  # noqa: PLR2004
                        error += "..."

    def save_baseline(self, output_path: Path) -> None:
        """Save results as baseline JSON."""
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build baseline data
        baseline = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": self.mode,
            "pipelines": [asdict(r) for r in self.results],
        }

        # Write to file
        with output_path.open("w") as f:
            json.dump(baseline, f, indent=2, sort_keys=True)

        logger.info("\nBaseline saved to: %s", output_path)

    def compare_with_baseline(
        self, baseline_path: Path, allow_new_benchmarks: bool = False
    ) -> tuple[bool, int]:
        """Compare current results with baseline.

        Args:
            baseline_path: Path to baseline JSON file
            allow_new_benchmarks: If True, allow new benchmarks without failing

        Returns:
            Tuple of (has_serious_issues, exit_code) where:
            - has_serious_issues: True if baseline missing or has new failures/regressions
            - exit_code: 1 if serious issues, 0 otherwise
        """
        if not baseline_path.exists():
            logger.error("Baseline file not found: %s", baseline_path)
            logger.info("To generate a baseline, run:")
            logger.info(
                "  python examples/shared/bench_examples.py --mode=%s --write-baseline=%s",
                self.mode,
                baseline_path,
            )
            return True, 1

        # Load baseline
        try:
            with baseline_path.open("r") as f:
                baseline_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.exception("Invalid baseline JSON: %s", e)
            return True, 1

        baseline_results = {(r["company"], r["pipeline"]): r for r in baseline_data["pipelines"]}

        regressions = []
        improvements = []
        new_failures = []
        new_successes = []

        new_benchmarks = []

        for result in self.results:
            key = (result.company, result.pipeline)

            if key not in baseline_results:
                # New benchmark not in baseline
                new_benchmarks.append(result)
                if not allow_new_benchmarks:
                    logger.warning(
                        f"New benchmark (not in baseline): {result.company}/{result.pipeline}. "
                        f"Use --allow-new-benchmarks to permit."
                    )
                else:
                    logger.info("New benchmark allowed: %s/%s", result.company, result.pipeline)
                continue

            baseline = baseline_results[key]
            baseline_runtime = baseline["runtime_ms"]
            current_runtime = result.runtime_ms

            # Skip skipped tests
            if result.status == "skipped" or baseline["status"] == "skipped":
                continue

            # Check for status changes
            if baseline["status"] == "completed" and result.status == "failed":
                new_failures.append(result)
            elif baseline["status"] == "failed" and result.status == "completed":
                new_successes.append(result)

            # Check for performance regressions with absolute floor (FIX3-G)
            # Regression if: (>20% slower) AND (>100ms absolute difference)
            if result.status == "completed" and baseline["status"] == "completed":
                diff_ms = current_runtime - baseline_runtime
                pct = (diff_ms / baseline_runtime) * 100 if baseline_runtime > 0 else 0

                # Regression detection with absolute floor
                if diff_ms > max(baseline_runtime * 0.2, 100):
                    regressions.append((result, diff_ms, pct))

                elif (
                    current_runtime < baseline_runtime * 0.8 and diff_ms < -100
                ):  # >20% faster AND >100ms  # noqa: PLR2004
                    diff_ms_abs = abs(diff_ms)
                    improvements.append((result, diff_ms_abs, abs(pct)))

        # Print comparison results
        if new_failures:
            for result in new_failures:
                pass

        if new_successes:
            for result in new_successes:
                pass

        if regressions:
            for result, diff_ms, pct in regressions:
                pass

        if improvements:
            for result, diff_ms, pct in improvements:
                pass

        if new_benchmarks and not allow_new_benchmarks:
            for result in new_benchmarks:
                pass

        if not any([new_failures, new_successes, regressions, improvements, new_benchmarks]):
            pass

        # Determine if there are serious issues that should fail CI (FIX3-G)
        has_serious_issues = bool(
            new_failures or regressions or (new_benchmarks and not allow_new_benchmarks)
        )

        if has_serious_issues:
            if new_failures:
                pass
            if regressions:
                pass
            if new_benchmarks and not allow_new_benchmarks:
                pass
            return True, 1

        return False, 0


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Sibyl example pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks (full mode)
  %(prog)s

  # Run CI-optimized benchmarks
  %(prog)s --mode=ci

  # Generate new baseline
  %(prog)s --mode=full --write-baseline=examples/shared/benchmarks/baseline.json

  # Compare against baseline
  %(prog)s --compare=examples/shared/benchmarks/baseline.json

  # CI workflow: compare only
  %(prog)s --mode=ci --compare=examples/shared/benchmarks/baseline.json

  # Run specific company
  %(prog)s --company=northwind_analytics

  # Dry run
  %(prog)s --dry-run
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["ci", "full"],
        default="full",
        help="Benchmark mode: 'ci' (fast, essential) or 'full' (all benchmarks)",
    )

    parser.add_argument("--company", type=str, help="Run benchmarks for specific company only")

    parser.add_argument(
        "--write-baseline",
        type=Path,
        dest="write_baseline",
        help="Write results as baseline JSON to specified path",
    )

    parser.add_argument("--compare", type=Path, help="Compare results against baseline file")

    parser.add_argument(
        "--allow-new-benchmarks",
        action="store_true",
        help="Allow new benchmarks that don't exist in baseline (won't fail CI)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (show what would be run)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize runner
    runner = BenchmarkRunner(mode=args.mode, dry_run=args.dry_run)

    # Run benchmarks
    suite_result = runner.run_all_benchmarks(filter_company=args.company)

    # Print summary
    runner.print_summary(suite_result)

    # Determine output path for baseline
    output_path = args.write_baseline or args.output

    # Save baseline if requested
    if output_path:
        runner.save_baseline(output_path)
    elif not args.compare and not args.dry_run:
        # Auto-save to default location
        default_output = PROJECT_ROOT / "examples/shared/benchmarks/baseline.json"
        runner.save_baseline(default_output)

    # Compare with baseline if requested
    has_comparison_issues = False
    comparison_exit_code = 0
    if args.compare:
        has_comparison_issues, comparison_exit_code = runner.compare_with_baseline(
            args.compare, allow_new_benchmarks=args.allow_new_benchmarks
        )

    # Exit with appropriate code
    # Priority order:
    # 1. Comparison issues (baseline missing or regressions)
    # 2. Benchmark failures
    if has_comparison_issues:
        logger.error("\nComparison with baseline failed due to serious issues")
        sys.exit(comparison_exit_code)

    if suite_result.failed > 0:
        logger.error("\n%s benchmark(s) failed", suite_result.failed)
        sys.exit(1)

    logger.info("\nBenchmark suite completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
