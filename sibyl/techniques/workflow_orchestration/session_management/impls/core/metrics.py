"""Rotation metrics with invariants and SLA tracking.

This module provides comprehensive metrics tracking for session rotation:
- **Latency metrics**: p50, p95, p99 rotation latencies
- **Compression metrics**: Compression ratios achieved by summarization
- **Success rates**: Rotation success/failure rates
- **Invariant checking**: Automated SLA enforcement
- **Alerting**: Warnings when invariants violated

Key invariants (production SLAs):
1. **Rotation latency p95 < 500ms**: 95% of rotations complete within 500ms
2. **Rotation success rate > 99%**: At most 1% failure rate
3. **Compression ratio > 0.3**: Summaries achieve at least 30% compression
4. **No double rotations**: Generation counter always increments by 1
5. **Fallback usage < 10%**: LLM summarization succeeds 90% of the time

Typical usage:
    metrics = RotationMetrics()

    # Record rotation
    metrics.record_rotation(
        latency_ms=250,
        success=True,
        compression_ratio=0.42,
        fallback_used=False,
        old_generation=1,
        new_generation=2,
    )

    # Check invariants
    violations = metrics.check_invariants()
    if violations:
        logger.error("Invariant violations: %s", violations)

    # Get statistics
    stats = metrics.get_stats()
    print(f"p95 latency: {stats['latency_p95_ms']}ms")
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RotationRecord:
    """Single rotation event record.

    Attributes:
        timestamp: When rotation occurred
        latency_ms: Rotation latency in milliseconds
        success: Whether rotation succeeded
        compression_ratio: Compression ratio (original_size / compressed_size)
        fallback_used: Whether fallback (delta compression) was used
        old_generation: Old session generation
        new_generation: New session generation
        trigger: What triggered the rotation
        error_message: Error message (if failed)
    """

    timestamp: float
    latency_ms: int
    success: bool
    compression_ratio: float | None
    fallback_used: bool
    old_generation: int
    new_generation: int
    trigger: str
    error_message: str | None = None


@dataclass
class InvariantViolation:
    """Record of an invariant violation.

    Attributes:
        invariant_name: Name of violated invariant
        expected: Expected value/condition
        actual: Actual value/condition
        severity: Severity level (warning, error, critical)
        message: Human-readable violation message
        timestamp: When violation occurred
    """

    invariant_name: str
    expected: str
    actual: str
    severity: str
    message: str
    timestamp: float = field(default_factory=time.time)


class RotationMetrics:
    """Rotation metrics tracker with invariant checking.

    This class tracks rotation metrics and enforces production SLAs.

    Invariants:
    - LATENCY_P95_MS: p95 latency < 500ms
    - SUCCESS_RATE_PCT: success rate > 99%
    - COMPRESSION_RATIO_MIN: compression ratio > 0.3
    - GENERATION_INCREMENT: generation always increments by 1
    - FALLBACK_RATE_MAX: fallback usage < 10%
    """

    # Invariant thresholds (production SLAs)
    LATENCY_P95_MS_MAX = 500  # p95 rotation latency
    LATENCY_P99_MS_MAX = 1000  # p99 rotation latency
    SUCCESS_RATE_MIN_PCT = 99.0  # Minimum success rate
    COMPRESSION_RATIO_MIN = 0.3  # Minimum compression ratio
    FALLBACK_RATE_MAX_PCT = 10.0  # Maximum fallback usage

    # Window size for rolling metrics
    WINDOW_SIZE = 100  # Last 100 rotations

    def __init__(self, window_size: int = WINDOW_SIZE) -> None:
        """Initialize rotation metrics.

        Args:
            window_size: Number of rotations to keep for rolling metrics
        """
        self.window_size = window_size

        # Rolling window of rotation records
        self._records: deque[RotationRecord] = deque(maxlen=window_size)

        # Cumulative counters
        self._total_rotations = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_fallbacks = 0

        # Admission rejection counters (by error type)
        self._admission_rejections: dict[str, int] = {}
        self._total_admission_attempts = 0
        self._total_admission_rejections = 0

        # Invariant violations
        self._violations: list[InvariantViolation] = []

        logger.info("RotationMetrics initialized (window_size=%s)", window_size)

    def record_rotation(
        self,
        latency_ms: int,
        success: bool,
        compression_ratio: float | None,
        fallback_used: bool,
        old_generation: int,
        new_generation: int,
        trigger: str = "token_threshold",
        error_message: str | None = None,
    ) -> None:
        """Record a rotation event.

        Args:
            latency_ms: Rotation latency in milliseconds
            success: Whether rotation succeeded
            compression_ratio: Compression ratio (0.0-1.0), None if no summarization
            fallback_used: Whether fallback was used
            old_generation: Old session generation
            new_generation: New session generation
            trigger: What triggered the rotation
            error_message: Error message (if failed)
        """
        record = RotationRecord(
            timestamp=time.time(),
            latency_ms=latency_ms,
            success=success,
            compression_ratio=compression_ratio,
            fallback_used=fallback_used,
            old_generation=old_generation,
            new_generation=new_generation,
            trigger=trigger,
            error_message=error_message,
        )

        self._records.append(record)

        # Update cumulative counters
        self._total_rotations += 1
        if success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        if fallback_used:
            self._total_fallbacks += 1

        # Check invariants after recording
        self._check_invariants_incremental(record)

        logger.debug(
            f"Recorded rotation: latency={latency_ms}ms, success={success}, "
            f"compression={compression_ratio:.2f if compression_ratio else 'N/A'}, "
            f"generation={old_generation}→{new_generation}"
        )

    def record_admission_attempt(self, allowed: bool, error_type: str | None = None) -> None:
        """Record an admission control attempt.

        Args:
            allowed: Whether admission was allowed
            error_type: Error type if rejected (e.g., "rotation_in_progress", "generation_mismatch")
        """
        self._total_admission_attempts += 1

        if not allowed:
            self._total_admission_rejections += 1
            error_type = error_type or "unknown"
            self._admission_rejections[error_type] = (
                self._admission_rejections.get(error_type, 0) + 1
            )

            logger.debug(
                f"Admission rejected: error_type={error_type}, "
                f"total_rejections={self._total_admission_rejections}"
            )

    def get_admission_stats(self) -> dict[str, Any]:
        """Get admission control statistics.

        Returns:
            Dict with admission metrics
        """
        total_attempts = self._total_admission_attempts
        total_rejections = self._total_admission_rejections

        return {
            "total_attempts": total_attempts,
            "total_rejections": total_rejections,
            "total_allowed": total_attempts - total_rejections,
            "rejection_rate_pct": (
                (total_rejections / total_attempts * 100) if total_attempts > 0 else 0.0
            ),
            "rejections_by_type": dict(self._admission_rejections),
        }

    def _check_invariants_incremental(self, record: RotationRecord) -> None:
        """Check invariants incrementally for latest record.

        This performs lightweight checks on the latest record only.

        Args:
            record: Latest rotation record
        """
        # Invariant 1: Generation must increment by 1
        if record.new_generation != record.old_generation + 1:
            violation = InvariantViolation(
                invariant_name="GENERATION_INCREMENT",
                expected="new_generation = old_generation + 1",
                actual=f"{record.new_generation} != {record.old_generation} + 1",
                severity="critical",
                message=f"Generation jumped from {record.old_generation} to {record.new_generation}",
            )
            self._violations.append(violation)
            logger.error("INVARIANT VIOLATION: %s", violation.message)

        # Invariant 2: Latency should be reasonable (< 5 seconds absolute limit)
        if record.latency_ms > 5000:
            violation = InvariantViolation(
                invariant_name="LATENCY_ABSOLUTE_MAX",
                expected="latency < 5000ms",
                actual=f"{record.latency_ms}ms",
                severity="error",
                message=f"Rotation took {record.latency_ms}ms (absolute limit: 5000ms)",
            )
            self._violations.append(violation)
            logger.error("INVARIANT VIOLATION: %s", violation.message)

    def check_invariants(self) -> list[InvariantViolation]:
        """Check all invariants against rolling window.

        This performs comprehensive checks on the entire rolling window.

        Returns:
            List of invariant violations (empty if all pass)
        """
        violations = []

        if len(self._records) == 0:
            return violations  # No data to check

        # Get current stats
        stats = self.get_stats()

        # Invariant 1: p95 latency < 500ms
        if stats["latency_p95_ms"] > self.LATENCY_P95_MS_MAX:
            violation = InvariantViolation(
                invariant_name="LATENCY_P95_MS",
                expected=f"< {self.LATENCY_P95_MS_MAX}ms",
                actual=f"{stats['latency_p95_ms']}ms",
                severity="warning",
                message=f"p95 latency {stats['latency_p95_ms']}ms exceeds SLA {self.LATENCY_P95_MS_MAX}ms",
            )
            violations.append(violation)
            logger.warning("INVARIANT VIOLATION: %s", violation.message)

        # Invariant 2: p99 latency < 1000ms
        if stats["latency_p99_ms"] > self.LATENCY_P99_MS_MAX:
            violation = InvariantViolation(
                invariant_name="LATENCY_P99_MS",
                expected=f"< {self.LATENCY_P99_MS_MAX}ms",
                actual=f"{stats['latency_p99_ms']}ms",
                severity="error",
                message=f"p99 latency {stats['latency_p99_ms']}ms exceeds SLA {self.LATENCY_P99_MS_MAX}ms",
            )
            violations.append(violation)
            logger.error("INVARIANT VIOLATION: %s", violation.message)

        # Invariant 3: Success rate > 99%
        if stats["success_rate_pct"] < self.SUCCESS_RATE_MIN_PCT:
            violation = InvariantViolation(
                invariant_name="SUCCESS_RATE_PCT",
                expected=f"> {self.SUCCESS_RATE_MIN_PCT}%",
                actual=f"{stats['success_rate_pct']:.1f}%",
                severity="critical",
                message=f"Success rate {stats['success_rate_pct']:.1f}% below SLA {self.SUCCESS_RATE_MIN_PCT}%",
            )
            violations.append(violation)
            logger.error("INVARIANT VIOLATION: %s", violation.message)

        # Invariant 4: Compression ratio > 0.3
        if (
            stats["compression_ratio_avg"] is not None
            and stats["compression_ratio_avg"] < self.COMPRESSION_RATIO_MIN
        ):
            violation = InvariantViolation(
                invariant_name="COMPRESSION_RATIO_MIN",
                expected=f"> {self.COMPRESSION_RATIO_MIN}",
                actual=f"{stats['compression_ratio_avg']:.2f}",
                severity="warning",
                message=f"Compression ratio {stats['compression_ratio_avg']:.2f} below target {self.COMPRESSION_RATIO_MIN}",
            )
            violations.append(violation)
            logger.warning("INVARIANT VIOLATION: %s", violation.message)

        # Invariant 5: Fallback usage < 10%
        if stats["fallback_rate_pct"] > self.FALLBACK_RATE_MAX_PCT:
            violation = InvariantViolation(
                invariant_name="FALLBACK_RATE_MAX",
                expected=f"< {self.FALLBACK_RATE_MAX_PCT}%",
                actual=f"{stats['fallback_rate_pct']:.1f}%",
                severity="warning",
                message=f"Fallback usage {stats['fallback_rate_pct']:.1f}% exceeds target {self.FALLBACK_RATE_MAX_PCT}%",
            )
            violations.append(violation)
            logger.warning("INVARIANT VIOLATION: %s", violation.message)

        return violations

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive rotation statistics.

        Returns:
            Stats dict with:
                - latency_p50_ms, latency_p95_ms, latency_p99_ms
                - latency_min_ms, latency_max_ms, latency_avg_ms
                - success_rate_pct, failure_rate_pct
                - compression_ratio_avg, compression_ratio_min, compression_ratio_max
                - fallback_rate_pct
                - total_rotations (lifetime)
                - window_size (current)
        """
        if len(self._records) == 0:
            admission_stats = self.get_admission_stats()
            return {
                "latency_p50_ms": 0,
                "latency_p95_ms": 0,
                "latency_p99_ms": 0,
                "latency_min_ms": 0,
                "latency_max_ms": 0,
                "latency_avg_ms": 0,
                "success_rate_pct": 0.0,
                "failure_rate_pct": 0.0,
                "compression_ratio_avg": None,
                "compression_ratio_min": None,
                "compression_ratio_max": None,
                "fallback_rate_pct": 0.0,
                "total_rotations": 0,
                "window_size": 0,
                # Admission control metrics
                "admission_total_attempts": admission_stats["total_attempts"],
                "admission_total_rejections": admission_stats["total_rejections"],
                "admission_rejection_rate_pct": admission_stats["rejection_rate_pct"],
                "admission_rejections_by_type": admission_stats["rejections_by_type"],
            }

        # Extract latencies
        latencies = [r.latency_ms for r in self._records]

        # Compute percentiles
        latency_p50 = int(np.percentile(latencies, 50))
        latency_p95 = int(np.percentile(latencies, 95))
        latency_p99 = int(np.percentile(latencies, 99))

        # Min/max/avg
        latency_min = min(latencies)
        latency_max = max(latencies)
        latency_avg = int(np.mean(latencies))

        # Success rates (rolling window)
        window_successes = sum(1 for r in self._records if r.success)
        window_failures = len(self._records) - window_successes
        success_rate = (window_successes / len(self._records)) * 100
        failure_rate = (window_failures / len(self._records)) * 100

        # Compression ratios
        compression_ratios = [
            r.compression_ratio for r in self._records if r.compression_ratio is not None
        ]
        if compression_ratios:
            compression_avg = float(np.mean(compression_ratios))
            compression_min = min(compression_ratios)
            compression_max = max(compression_ratios)
        else:
            compression_avg = None
            compression_min = None
            compression_max = None

        # Fallback rate (rolling window)
        window_fallbacks = sum(1 for r in self._records if r.fallback_used)
        fallback_rate = (window_fallbacks / len(self._records)) * 100

        # Get admission stats
        admission_stats = self.get_admission_stats()

        return {
            # Latency metrics
            "latency_p50_ms": latency_p50,
            "latency_p95_ms": latency_p95,
            "latency_p99_ms": latency_p99,
            "latency_min_ms": latency_min,
            "latency_max_ms": latency_max,
            "latency_avg_ms": latency_avg,
            # Success metrics
            "success_rate_pct": success_rate,
            "failure_rate_pct": failure_rate,
            # Compression metrics
            "compression_ratio_avg": compression_avg,
            "compression_ratio_min": compression_min,
            "compression_ratio_max": compression_max,
            # Fallback metrics
            "fallback_rate_pct": fallback_rate,
            # Totals
            "total_rotations": self._total_rotations,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_fallbacks": self._total_fallbacks,
            "window_size": len(self._records),
            # Admission control metrics
            "admission_total_attempts": admission_stats["total_attempts"],
            "admission_total_rejections": admission_stats["total_rejections"],
            "admission_rejection_rate_pct": admission_stats["rejection_rate_pct"],
            "admission_rejections_by_type": admission_stats["rejections_by_type"],
        }

    def get_violations(self) -> list[InvariantViolation]:
        """Get all recorded invariant violations.

        Returns:
            List of all violations
        """
        return self._violations

    def clear_violations(self) -> None:
        """Clear all recorded violations.

        Should be called after violations are handled/acknowledged.
        """
        self._violations.clear()

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._records.clear()
        self._total_rotations = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_fallbacks = 0
        self._violations.clear()

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"RotationMetrics(rotations={stats['total_rotations']}, "
            f"p95={stats['latency_p95_ms']}ms, "
            f"success_rate={stats['success_rate_pct']:.1f}%)"
        )


# Global metrics instance (singleton)
_global_metrics: RotationMetrics | None = None


def get_rotation_metrics(window_size: int = RotationMetrics.WINDOW_SIZE) -> RotationMetrics:
    """Get global rotation metrics instance (singleton).

    Args:
        window_size: Window size (only used on first call)

    Returns:
        RotationMetrics instance
    """
    global _global_metrics

    if _global_metrics is None:
        _global_metrics = RotationMetrics(window_size=window_size)

    return _global_metrics
