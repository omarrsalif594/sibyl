"""
Orchestration script for training multiple specialists.

This script manages training multiple specialist models in sequence or parallel,
with support for different configurations and domains.
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SpecialistConfig:
    """Configuration for a specialist to train."""

    name: str
    config_path: str
    description: str
    priority: int = 1  # Higher = train first


@dataclass
class TrainingRun:
    """Record of a training run."""

    specialist_name: str
    config_path: str
    start_time: str
    end_time: str | None = None
    duration_minutes: float | None = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: str | None = None


class SpecialistOrchestrator:
    """
    Orchestrates training of multiple specialist models.

    Features:
    - Sequential or parallel training
    - Progress tracking
    - Error handling and recovery
    - Training logs and reports
    """

    def __init__(self, toolkit_root: Path | None = None) -> None:
        """
        Initialize orchestrator.

        Args:
            toolkit_root: Root directory of training toolkit
        """
        self.toolkit_root = toolkit_root or Path(__file__).parent.parent
        self.runs: list[TrainingRun] = []
        self.start_time = None
        self.end_time = None

    def discover_configs(self, config_dir: Path | None = None) -> list[SpecialistConfig]:
        """
        Discover training configurations.

        Args:
            config_dir: Directory containing config YAML files

        Returns:
            List of specialist configurations
        """
        if config_dir is None:
            config_dir = self.toolkit_root / "config" / "training"

        configs = []

        # Default toy configs
        toy_configs = [
            SpecialistConfig(
                name="toy_fast_1_5b",
                config_path=str(config_dir / "toy_fast_1_5b.yaml"),
                description="Fast 1.5B model for rapid prototyping",
                priority=2,
            ),
            SpecialistConfig(
                name="toy_deep_3b",
                config_path=str(config_dir / "toy_deep_3b.yaml"),
                description="Deep 3B model for higher quality",
                priority=1,
            ),
        ]

        # Filter to only existing configs
        for config in toy_configs:
            if Path(config.config_path).exists():
                configs.append(config)

        # Sort by priority (higher first)
        configs.sort(key=lambda x: x.priority, reverse=True)

        return configs

    def train_specialist(self, specialist: SpecialistConfig, dry_run: bool = False) -> TrainingRun:
        """
        Train a single specialist.

        Args:
            specialist: Specialist configuration
            dry_run: If True, don't actually run training

        Returns:
            TrainingRun record
        """
        run = TrainingRun(
            specialist_name=specialist.name,
            config_path=specialist.config_path,
            start_time=datetime.now().isoformat(),
            status="running",
        )

        if dry_run:
            run.status = "completed"
            run.end_time = datetime.now().isoformat()
            run.duration_minutes = 0.0
            return run

        start = time.time()

        try:
            # Build command
            train_script = self.toolkit_root / "pipeline" / "train_specialist.py"
            cmd = [
                sys.executable,
                str(train_script),
                "--config",
                specialist.config_path,
                "--toolkit-root",
                str(self.toolkit_root),
            ]

            # Run training
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Success
            run.status = "completed"

        except subprocess.CalledProcessError as e:
            # Training failed
            run.status = "failed"
            run.error_message = str(e)

        except Exception as e:
            # Unexpected error
            run.status = "failed"
            run.error_message = str(e)

        finally:
            # Record timing
            elapsed = time.time() - start
            run.end_time = datetime.now().isoformat()
            run.duration_minutes = elapsed / 60

        return run

    def train_all(
        self,
        specialists: list[SpecialistConfig] | None = None,
        dry_run: bool = False,
        parallel: bool = False,
    ) -> None:
        """
        Train all specialists.

        Args:
            specialists: List of specialists to train (None = discover all)
            dry_run: If True, don't actually run training
            parallel: If True, train in parallel (not implemented yet)
        """
        if specialists is None:
            specialists = self.discover_configs()

        if not specialists:
            return

        for _spec in specialists:
            pass

        if parallel:
            pass

        self.start_time = datetime.now()

        # Train each specialist
        for _i, specialist in enumerate(specialists, 1):
            run = self.train_specialist(specialist, dry_run=dry_run)
            self.runs.append(run)

        self.end_time = datetime.now()

        # Generate report
        self.generate_report()

    def generate_report(self) -> None:
        """Generate training report."""
        if not self.runs:
            return

        (self.end_time - self.start_time).total_seconds() / 60

        # Summary statistics
        sum(1 for r in self.runs if r.status == "completed")
        sum(1 for r in self.runs if r.status == "failed")

        # Individual results
        for run in self.runs:
            if run.error_message:
                pass

        # Save report to file
        self.save_report()

    def save_report(self) -> None:
        """Save training report to JSON file."""
        report_dir = self.toolkit_root / "outputs" / "training_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"training_report_{timestamp}.json"

        report_data = {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_specialists": len(self.runs),
            "completed": sum(1 for r in self.runs if r.status == "completed"),
            "failed": sum(1 for r in self.runs if r.status == "failed"),
            "runs": [asdict(run) for run in self.runs],
        }

        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Train multiple specialist models")
    parser.add_argument(
        "--config-dir", type=str, default=None, help="Directory containing config files"
    )
    parser.add_argument(
        "--specialists",
        type=str,
        nargs="+",
        default=None,
        help="Specific specialists to train (by name)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't actually run training")
    parser.add_argument(
        "--parallel", action="store_true", help="Train specialists in parallel (not implemented)"
    )
    parser.add_argument(
        "--toolkit-root", type=str, default=None, help="Root directory of training toolkit"
    )

    args = parser.parse_args()

    # Initialize orchestrator
    toolkit_root = Path(args.toolkit_root) if args.toolkit_root else None
    orchestrator = SpecialistOrchestrator(toolkit_root)

    # Discover configs
    config_dir = Path(args.config_dir) if args.config_dir else None
    specialists = orchestrator.discover_configs(config_dir)

    # Filter to specific specialists if requested
    if args.specialists:
        specialists = [s for s in specialists if s.name in args.specialists]

    # Train all
    orchestrator.train_all(specialists=specialists, dry_run=args.dry_run, parallel=args.parallel)


if __name__ == "__main__":
    main()
