"""Metrics tracking for quality control system.

This module provides metrics collection for QC operations:
- Verdict counts by status and category
- Retry attempt counts and success rates
- Validation duration tracking
- Validator performance metrics
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sibyl.mcp_server.domain.quality_control import (
    QCRetryMetadata,
    ValidationVerdict,
)

logger = logging.getLogger(__name__)


@dataclass
class QCMetrics:
    """Quality control metrics container.

    Tracks metrics for observability and performance monitoring.
    All metrics are in-memory and reset on server restart.
    """

    # Verdict counts by status
    verdict_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Verdict counts by category
    category_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Retry statistics
    retry_attempts: list[int] = field(default_factory=list)
    retry_successes: int = 0
    retry_failures: int = 0

    # Validation duration (milliseconds)
    validation_durations_ms: list[float] = field(default_factory=list)

    # Validator-specific metrics
    validator_counts: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    # Error classification metrics
    error_classification_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_classification_unknown_count: int = 0
    error_classification_confidence_scores: list[float] = field(default_factory=list)

    # Timestamps
    first_validation: datetime | None = None
    last_validation: datetime | None = None

    def record_verdict(self, verdict: ValidationVerdict) -> None:
        """Record a validation verdict.

        Args:
            verdict: The validation verdict to record
        """
        now = datetime.utcnow()
        if self.first_validation is None:
            self.first_validation = now
        self.last_validation = now

        # Count by status
        status_key = verdict.status.value
        self.verdict_counts[status_key] += 1

        # Count by category (if present)
        if verdict.error_category:
            self.category_counts[verdict.error_category] += 1

        # Validator-specific counts
        validator_name = verdict.validator_name
        self.validator_counts[validator_name][status_key] += 1

        logger.debug(
            f"QC metric recorded: {status_key} from {validator_name} "
            f"(category={verdict.error_category})"
        )

    def record_retry(self, retry_metadata: QCRetryMetadata, success: bool) -> None:
        """Record a retry attempt.

        Args:
            retry_metadata: Metadata about the retry attempt
            success: Whether the retry ultimately succeeded
        """
        self.retry_attempts.append(retry_metadata.attempt)

        if success:
            self.retry_successes += 1
        else:
            self.retry_failures += 1

        logger.debug(
            f"QC retry recorded: attempt={retry_metadata.attempt}/{retry_metadata.max_attempts}, "
            f"success={success}"
        )

    def record_validation_duration(self, duration_ms: float) -> None:
        """Record validation duration.

        Args:
            duration_ms: Duration in milliseconds
        """
        self.validation_durations_ms.append(duration_ms)

    def record_error_classification(self, category: str, confidence: float) -> None:
        """Record an error classification.

        Args:
            category: Error category
            confidence: Classification confidence (0.0-1.0)
        """
        self.error_classification_counts[category] += 1

        if category == "unknown":
            self.error_classification_unknown_count += 1

        self.error_classification_confidence_scores.append(confidence)

        logger.debug("Error classification recorded: %s (confidence=%s)", category, confidence)

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all metrics.

        Returns:
            Dictionary with metric summaries
        """
        total_validations = sum(self.verdict_counts.values())
        total_retries = len(self.retry_attempts)

        # Calculate success rate
        retry_success_rate = 0.0
        if total_retries > 0:
            retry_success_rate = self.retry_successes / total_retries

        # Calculate average retry attempts
        avg_retry_attempts = 0.0
        if total_retries > 0:
            avg_retry_attempts = sum(self.retry_attempts) / total_retries

        # Calculate validation duration percentiles
        p50_duration_ms = 0.0
        p95_duration_ms = 0.0
        p99_duration_ms = 0.0
        if self.validation_durations_ms:
            sorted_durations = sorted(self.validation_durations_ms)
            p50_idx = int(len(sorted_durations) * 0.5)
            p95_idx = int(len(sorted_durations) * 0.95)
            p99_idx = int(len(sorted_durations) * 0.99)
            p50_duration_ms = sorted_durations[p50_idx]
            p95_duration_ms = sorted_durations[p95_idx]
            p99_duration_ms = sorted_durations[p99_idx]

        # Calculate error classification stats
        total_classifications = sum(self.error_classification_counts.values())
        avg_confidence = 0.0
        if self.error_classification_confidence_scores:
            avg_confidence = sum(self.error_classification_confidence_scores) / len(
                self.error_classification_confidence_scores
            )
        unknown_rate = 0.0
        if total_classifications > 0:
            unknown_rate = self.error_classification_unknown_count / total_classifications

        return {
            "total_validations": total_validations,
            "verdict_counts": dict(self.verdict_counts),
            "category_counts": dict(self.category_counts),
            "retry_stats": {
                "total_retries": total_retries,
                "successes": self.retry_successes,
                "failures": self.retry_failures,
                "success_rate": retry_success_rate,
                "avg_attempts": avg_retry_attempts,
            },
            "duration_stats": {
                "count": len(self.validation_durations_ms),
                "p50_ms": p50_duration_ms,
                "p95_ms": p95_duration_ms,
                "p99_ms": p99_duration_ms,
            },
            "validator_counts": {
                validator: dict(counts) for validator, counts in self.validator_counts.items()
            },
            "error_classification_stats": {
                "total_classifications": total_classifications,
                "classification_counts": dict(self.error_classification_counts),
                "unknown_count": self.error_classification_unknown_count,
                "unknown_rate": unknown_rate,
                "avg_confidence": avg_confidence,
            },
            "time_range": {
                "first_validation": self.first_validation.isoformat()
                if self.first_validation
                else None,
                "last_validation": self.last_validation.isoformat()
                if self.last_validation
                else None,
            },
        }

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            String with Prometheus-formatted metrics
        """
        lines = []

        # Verdict counts
        lines.append("# HELP qc_verdict_count Total number of QC verdicts by status")
        lines.append("# TYPE qc_verdict_count counter")
        for status, count in self.verdict_counts.items():
            lines.append(f'qc_verdict_count{{status="{status}"}} {count}')

        # Category counts
        lines.append("\n# HELP qc_error_category_count Total number of errors by category")
        lines.append("# TYPE qc_error_category_count counter")
        for category, count in self.category_counts.items():
            lines.append(f'qc_error_category_count{{category="{category}"}} {count}')

        # Retry stats
        lines.append("\n# HELP qc_retry_attempts_total Total number of retry attempts")
        lines.append("# TYPE qc_retry_attempts_total counter")
        lines.append(f"qc_retry_attempts_total {len(self.retry_attempts)}")

        lines.append("# HELP qc_retry_successes_total Total number of successful retries")
        lines.append("# TYPE qc_retry_successes_total counter")
        lines.append(f"qc_retry_successes_total {self.retry_successes}")

        lines.append("# HELP qc_retry_failures_total Total number of failed retries")
        lines.append("# TYPE qc_retry_failures_total counter")
        lines.append(f"qc_retry_failures_total {self.retry_failures}")

        # Duration stats
        if self.validation_durations_ms:
            sorted_durations = sorted(self.validation_durations_ms)
            p50_idx = int(len(sorted_durations) * 0.5)
            p95_idx = int(len(sorted_durations) * 0.95)
            p99_idx = int(len(sorted_durations) * 0.99)

            lines.append("\n# HELP qc_validation_duration_ms Validation duration percentiles")
            lines.append("# TYPE qc_validation_duration_ms gauge")
            lines.append(
                f'qc_validation_duration_ms{{percentile="p50"}} {sorted_durations[p50_idx]}'
            )
            lines.append(
                f'qc_validation_duration_ms{{percentile="p95"}} {sorted_durations[p95_idx]}'
            )
            lines.append(
                f'qc_validation_duration_ms{{percentile="p99"}} {sorted_durations[p99_idx]}'
            )

        # Validator counts
        lines.append("\n# HELP qc_validator_count Validator verdict counts by validator and status")
        lines.append("# TYPE qc_validator_count counter")
        for validator, counts in self.validator_counts.items():
            for status, count in counts.items():
                lines.append(
                    f'qc_validator_count{{validator="{validator}",status="{status}"}} {count}'
                )

        # Error classification counts
        lines.append(
            "\n# HELP qc_error_classification_count Error classification counts by category"
        )
        lines.append("# TYPE qc_error_classification_count counter")
        for category, count in self.error_classification_counts.items():
            lines.append(f'qc_error_classification_count{{category="{category}"}} {count}')

        lines.append(
            "\n# HELP qc_error_classification_unknown_total Total number of unknown errors"
        )
        lines.append("# TYPE qc_error_classification_unknown_total counter")
        lines.append(
            f"qc_error_classification_unknown_total {self.error_classification_unknown_count}"
        )

        # Error classification confidence
        if self.error_classification_confidence_scores:
            avg_confidence = sum(self.error_classification_confidence_scores) / len(
                self.error_classification_confidence_scores
            )
            lines.append(
                "\n# HELP qc_error_classification_confidence Average error classification confidence"
            )
            lines.append("# TYPE qc_error_classification_confidence gauge")
            lines.append(f"qc_error_classification_confidence {avg_confidence:.4f}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        self.verdict_counts.clear()
        self.category_counts.clear()
        self.retry_attempts.clear()
        self.retry_successes = 0
        self.retry_failures = 0
        self.validation_durations_ms.clear()
        self.validator_counts.clear()
        self.error_classification_counts.clear()
        self.error_classification_unknown_count = 0
        self.error_classification_confidence_scores.clear()
        self.first_validation = None
        self.last_validation = None
        logger.info("QC metrics reset")


# Global metrics instance
_global_metrics = QCMetrics()


def get_qc_metrics() -> QCMetrics:
    """Get the global QC metrics instance.

    Returns:
        Global QCMetrics instance
    """
    return _global_metrics


def record_verdict(verdict: ValidationVerdict) -> None:
    """Record a validation verdict in global metrics.

    Args:
        verdict: The validation verdict to record
    """
    _global_metrics.record_verdict(verdict)


def record_retry(retry_metadata: QCRetryMetadata, success: bool) -> None:
    """Record a retry attempt in global metrics.

    Args:
        retry_metadata: Metadata about the retry attempt
        success: Whether the retry ultimately succeeded
    """
    _global_metrics.record_retry(retry_metadata, success)


def record_validation_duration(duration_ms: float) -> None:
    """Record validation duration in global metrics.

    Args:
        duration_ms: Duration in milliseconds
    """
    _global_metrics.record_validation_duration(duration_ms)


class MetricsContext:
    """Context manager for tracking validation duration.

    Usage:
        with MetricsContext():
            verdict = await validate(...)
        # Duration automatically recorded
    """

    def __init__(self) -> None:
        self.start_time: float = 0

    def __enter__(self) -> Any:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.time() - self.start_time) * 1000
        record_validation_duration(duration_ms)
        return False  # Don't suppress exceptions
