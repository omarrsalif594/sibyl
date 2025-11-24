#!/usr/bin/env python3
"""
Sibyl Examples Test Runner

Discovers and runs all smoke tests across example companies.
Aggregates results and provides a summary.

Usage:
    python examples/shared/tooling/test_runner.py
    python examples/shared/tooling/test_runner.py --company riverbank_finance
    python examples/shared/tooling/test_runner.py --verbose
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Result of running tests for a company."""

    company: str
    test_file: Path
    passed: int
    failed: int
    skipped: int
    duration: float
    exit_code: int
    output: str


class ExampleTestRunner:
    """Runner for example smoke tests."""

    def __init__(self, examples_root: Path) -> None:
        self.examples_root = examples_root
        self.companies_dir = examples_root / "companies"
        self.results: list[TestResult] = []

    def discover_test_files(self, company: str | None = None) -> dict[str, list[Path]]:
        """Discover test files for companies."""
        test_files = {}

        if company:
            # Single company
            company_dir = self.companies_dir / company
            if not company_dir.exists():
                return test_files

            tests_dir = company_dir / "tests"
            if tests_dir.exists():
                test_files[company] = list(tests_dir.glob("test_*.py"))

        else:
            # All companies
            for company_dir in self.companies_dir.iterdir():
                if not company_dir.is_dir() or company_dir.name.startswith("."):
                    continue

                tests_dir = company_dir / "tests"
                if tests_dir.exists():
                    test_paths = list(tests_dir.glob("test_*.py"))
                    if test_paths:
                        test_files[company_dir.name] = test_paths

        return test_files

    def run_pytest(
        self, test_file: Path, verbose: bool = False, markers: str | None = None
    ) -> TestResult:
        """Run pytest on a single test file."""
        company = test_file.parent.parent.name

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-v" if verbose else "-q",
            "--tb=short",
        ]

        if markers:
            cmd.extend(["-m", markers])

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                check=False,
                cwd=self.examples_root.parent,  # Project root
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test file
            )

            duration = time.time() - start_time

            # Parse output to extract test counts
            output = result.stdout + result.stderr
            passed, failed, skipped = self._parse_pytest_output(output)

            return TestResult(
                company=company,
                test_file=test_file,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration,
                exit_code=result.returncode,
                output=output,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                company=company,
                test_file=test_file,
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=-1,
                output="Test timed out after 300 seconds",
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                company=company,
                test_file=test_file,
                passed=0,
                failed=1,
                skipped=0,
                duration=duration,
                exit_code=-1,
                output=f"Error running tests: {e!s}",
            )

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output to extract test counts."""
        passed = 0
        failed = 0
        skipped = 0

        # Look for summary line like: "5 passed, 2 failed, 1 skipped in 1.23s"
        for line in output.split("\n"):
            line_lower = line.lower()

            if "passed" in line_lower:
                parts = line_lower.split("passed")
                if parts:
                    try:
                        # Extract number before 'passed'
                        num_str = parts[0].strip().split()[-1]
                        passed = int(num_str)
                    except (ValueError, IndexError):
                        pass

            if "failed" in line_lower:
                parts = line_lower.split("failed")
                if parts:
                    try:
                        num_str = parts[0].strip().split()[-1]
                        if num_str.isdigit():
                            failed = int(num_str)
                    except (ValueError, IndexError):
                        pass

            if "skipped" in line_lower:
                parts = line_lower.split("skipped")
                if parts:
                    try:
                        num_str = parts[0].strip().split()[-1]
                        if num_str.isdigit():
                            skipped = int(num_str)
                    except (ValueError, IndexError):
                        pass

        return passed, failed, skipped

    def run_all_tests(
        self, company: str | None = None, verbose: bool = False, markers: str | None = None
    ) -> None:
        """Run all tests for specified company or all companies."""
        test_files = self.discover_test_files(company)

        if not test_files:
            if company:
                pass
            else:
                pass
            return

        len(test_files)
        sum(len(files) for files in test_files.values())

        for _company_name, test_paths in sorted(test_files.items()):
            for test_path in test_paths:
                result = self.run_pytest(test_path, verbose, markers)
                self.results.append(result)

                # Show immediate result

                if result.exit_code != 0 and verbose:
                    pass

    def print_summary(self) -> Any:
        """Print summary of all test results."""
        if not self.results:
            return None

        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_passed + total_failed + total_skipped
        sum(r.duration for r in self.results)

        # Group by company

        companies = {}
        for result in self.results:
            if result.company not in companies:
                companies[result.company] = []
            companies[result.company].append(result)

        for _company, results in sorted(companies.items()):
            company_passed = sum(r.passed for r in results)
            company_failed = sum(r.failed for r in results)
            company_skipped = sum(r.skipped for r in results)
            company_passed + company_failed + company_skipped

            for result in results:
                pass

        # Overall status
        if total_failed == 0:
            pass
        else:
            pass

        return total_failed == 0

    def get_failed_companies(self) -> list[str]:
        """Get list of companies with failed tests."""
        failed_companies = set()
        for result in self.results:
            if result.failed > 0 or result.exit_code != 0:
                failed_companies.add(result.company)
        return sorted(failed_companies)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run smoke tests for Sibyl examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --company riverbank_finance
  %(prog)s --verbose
  %(prog)s --markers smoke
        """,
    )

    parser.add_argument("--company", help="Run tests for specific company only")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output (show test details)"
    )

    parser.add_argument(
        "--markers", "-m", help='Run only tests with specific pytest markers (e.g., "smoke")'
    )

    parser.add_argument(
        "--examples-root",
        type=Path,
        default=Path(__file__).parent.parent.parent,
        help="Root directory of examples (default: auto-detect)",
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = ExampleTestRunner(args.examples_root)

    # Run tests

    runner.run_all_tests(company=args.company, verbose=args.verbose, markers=args.markers)

    # Print summary
    all_passed = runner.print_summary()

    # Exit with appropriate code
    if all_passed:
        sys.exit(0)
    else:
        runner.get_failed_companies()
        sys.exit(1)


if __name__ == "__main__":
    main()
