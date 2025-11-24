"""
Time-based rotation strategy implementation.

Triggers rotation based on session duration with configurable thresholds.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class TimeRotationDecision:
    """Result of time-based rotation check."""

    should_rotate: bool
    reason: str
    elapsed_seconds: float
    threshold_seconds: float
    session_start: datetime
    current_time: datetime


class TimeBasedImplementation:
    """Time-based rotation strategy.

    Rotates sessions based on elapsed time since session creation.
    Useful for long-running sessions where token usage might be low
    but session staleness is a concern.
    """

    def __init__(self) -> None:
        self._name = "time_based"
        self._description = "Trigger rotation based on session duration"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> TimeRotationDecision:
        """Execute time-based rotation check.

        Args:
            input_data: Dict with:
                - session_start: Session start datetime or ISO timestamp string
                - current_time: Current datetime or ISO timestamp string (optional, defaults to now)
            config: Merged configuration with:
                - max_duration_seconds: Maximum session duration (default: 3600 = 1 hour)
                - max_duration_minutes: Alternative specification in minutes
                - max_duration_hours: Alternative specification in hours

        Returns:
            TimeRotationDecision with rotation recommendation and metadata
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        # Parse session start time
        session_start = input_data.get("session_start")
        if isinstance(session_start, str):
            session_start = datetime.fromisoformat(session_start)
        elif not isinstance(session_start, datetime):
            msg = "session_start must be a datetime or ISO string"
            raise TypeError(msg)

        # Parse current time (default to now)
        current_time = input_data.get("current_time")
        if current_time is None:
            current_time = datetime.now()
        elif isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time)
        elif not isinstance(current_time, datetime):
            msg = "current_time must be a datetime or ISO string"
            raise ValueError(msg)

        # Calculate elapsed time
        elapsed = current_time - session_start
        elapsed_seconds = elapsed.total_seconds()

        # Determine threshold (with multiple unit options)
        threshold_seconds = self._get_threshold_seconds(config)

        # Determine rotation decision
        should_rotate = elapsed_seconds >= threshold_seconds

        if should_rotate:
            reason = (
                f"Session duration {elapsed_seconds:.0f}s exceeds threshold "
                f"{threshold_seconds:.0f}s ({threshold_seconds / 3600:.1f}h)"
            )
        else:
            remaining = threshold_seconds - elapsed_seconds
            reason = (
                f"Session duration {elapsed_seconds:.0f}s below threshold "
                f"({remaining:.0f}s remaining)"
            )

        logger.debug(
            f"Time-based rotation check: rotate={should_rotate} "
            f"(elapsed={elapsed_seconds:.0f}s, threshold={threshold_seconds:.0f}s)"
        )

        return TimeRotationDecision(
            should_rotate=should_rotate,
            reason=reason,
            elapsed_seconds=elapsed_seconds,
            threshold_seconds=threshold_seconds,
            session_start=session_start,
            current_time=current_time,
        )

    def _get_threshold_seconds(self, config: dict[str, Any]) -> float:
        """Get threshold in seconds from config (supports multiple units)."""
        # Priority order: seconds > minutes > hours
        if "max_duration_seconds" in config:
            return float(config["max_duration_seconds"])
        if "max_duration_minutes" in config:
            return float(config["max_duration_minutes"]) * 60
        if "max_duration_hours" in config:
            return float(config["max_duration_hours"]) * 3600
        # Default: 1 hour
        return 3600.0

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {
            "max_duration_seconds": 3600,  # 1 hour default
            "max_duration_minutes": None,
            "max_duration_hours": None,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        threshold = self._get_threshold_seconds(config)

        if threshold <= 0:
            msg = f"max_duration must be positive, got {threshold}s"
            raise ValueError(msg)

        if threshold > 86400:  # 24 hours
            logger.warning(
                f"max_duration {threshold}s ({threshold / 3600:.1f}h) is very long. "
                "Consider using token-based rotation for long sessions."
            )

        return True
