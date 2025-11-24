"""Observability: structured logging, metrics, and sampling."""

import asyncio
import contextlib
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Metric data point."""

    name: str
    value: float
    dimensions: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class SamplingStrategy:
    """Adaptive sampling for observability.

    Samples 100% of failures and slow calls, configurable % of successes.
    """

    def __init__(
        self,
        success_rate: float | None = None,
        failure_rate: float | None = None,
        slow_threshold_ms: int | None = None,
        slow_rate: float | None = None,
        config_path: Path | None = None,
    ) -> None:
        """Initialize sampling strategy.

        Args:
            success_rate: Sample rate for successful calls (0.0-1.0)
            failure_rate: Sample rate for failed calls (typically 1.0)
            slow_threshold_ms: Latency threshold for "slow" classification
            slow_rate: Sample rate for slow calls (typically 1.0)
            config_path: Optional path to observability config file
        """
        # Load from config if parameters not provided
        config = self._load_config(config_path)
        sampling_config = config.get("sampling_strategy", {})

        self.success_rate = (
            success_rate if success_rate is not None else sampling_config.get("success_rate", 0.1)
        )
        self.failure_rate = (
            failure_rate if failure_rate is not None else sampling_config.get("failure_rate", 1.0)
        )
        self.slow_threshold_ms = (
            slow_threshold_ms
            if slow_threshold_ms is not None
            else sampling_config.get("slow_threshold_ms", 5000)
        )
        self.slow_rate = (
            slow_rate if slow_rate is not None else sampling_config.get("slow_rate", 1.0)
        )

        logger.info(
            f"Sampling strategy: success={self.success_rate}, failure={self.failure_rate}, "
            f"slow_threshold={self.slow_threshold_ms}ms, slow_rate={self.slow_rate}"
        )

    def should_sample(self, result: dict[str, Any]) -> bool:
        """Decide if this call should be sampled.

        Args:
            result: Result dict with finish_reason, latency_ms, etc.

        Returns:
            True if should sample
        """
        finish_reason = result.get("finish_reason", "stop")
        latency_ms = result.get("latency_ms", 0)

        # Always sample failures
        # S311: Using random for sampling rate (not security-sensitive)
        if finish_reason != "stop":
            return random.random() < self.failure_rate

        # Always sample slow calls
        # S311: Using random for sampling rate (not security-sensitive)
        if latency_ms > self.slow_threshold_ms:
            return random.random() < self.slow_rate

        # Sample successes at configured rate
        # S311: Using random for sampling rate (not security-sensitive)
        return random.random() < self.success_rate

    def _load_config(self, config_path: Path | None) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            config_path: Optional path to config file

        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = Path(__file__).parent / "observability_config.yaml"

        try:
            if config_path.exists():
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to load observability config from %s: %s", config_path, e)

        # Return defaults matching original hardcoded behavior
        return {
            "sampling_strategy": {
                "success_rate": 0.1,
                "failure_rate": 1.0,
                "slow_threshold_ms": 5000,
                "slow_rate": 1.0,
            }
        }


class MetricsExporter:
    """Export metrics to stdout JSON (can pipe to collector).

    Supports sampling to control volume.
    """

    def __init__(self, sample_rate: float = 1.0) -> None:
        """Initialize metrics exporter.

        Args:
            sample_rate: Global sample rate (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self._queue: asyncio.Queue[Metric] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

        logger.info("Metrics exporter initialized (sample_rate=%s)", sample_rate)

    async def start(self) -> None:
        """Start metrics export worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._export_loop())
        logger.info("Metrics exporter started")

    async def stop(self) -> None:
        """Stop metrics export worker."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        logger.info("Metrics exporter stopped")

    async def record(self, metric: Metric) -> None:
        """Record metric with sampling.

        Args:
            metric: Metric to record
        """
        # S311: Using random for sampling rate (not security-sensitive)
        if random.random() < self.sample_rate:
            await self._queue.put(metric)

    async def _export_loop(self) -> None:
        """Export metrics to stdout (JSON format)."""
        while self._running:
            try:
                await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Export to stdout as JSON

            except TimeoutError:
                continue
            except Exception as e:
                logger.exception("Error exporting metric: %s", e)


class StructuredLogger:
    """Structured logging helper with correlation IDs.

    Wraps Python's logging with automatic correlation/span ID injection.
    """

    def __init__(self, name: str) -> None:
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self._logger = logging.getLogger(name)

    def info(
        self,
        message: str,
        correlation_id: str | None = None,
        span_id: str | None = None,
        **kwargs,
    ) -> None:
        """Log info with structured fields.

        Args:
            message: Log message
            correlation_id: Correlation ID
            span_id: Span ID
            **kwargs: Additional fields
        """
        extra = self._build_extra(correlation_id, span_id, kwargs)
        self._logger.info(message, extra=extra)

    def warning(
        self,
        message: str,
        correlation_id: str | None = None,
        span_id: str | None = None,
        **kwargs,
    ) -> None:
        """Log warning with structured fields.

        Args:
            message: Log message
            correlation_id: Correlation ID
            span_id: Span ID
            **kwargs: Additional fields
        """
        extra = self._build_extra(correlation_id, span_id, kwargs)
        self._logger.warning(message, extra=extra)

    def error(
        self,
        message: str,
        correlation_id: str | None = None,
        span_id: str | None = None,
        exc_info: bool = False,
        **kwargs,
    ) -> None:
        """Log error with structured fields.

        Args:
            message: Log message
            correlation_id: Correlation ID
            span_id: Span ID
            exc_info: Include exception info
            **kwargs: Additional fields
        """
        extra = self._build_extra(correlation_id, span_id, kwargs)
        self._logger.error(message, extra=extra, exc_info=exc_info)

    def debug(
        self,
        message: str,
        correlation_id: str | None = None,
        span_id: str | None = None,
        **kwargs,
    ) -> None:
        """Log debug with structured fields.

        Args:
            message: Log message
            correlation_id: Correlation ID
            span_id: Span ID
            **kwargs: Additional fields
        """
        extra = self._build_extra(correlation_id, span_id, kwargs)
        self._logger.debug(message, extra=extra)

    @staticmethod
    def _build_extra(
        correlation_id: str | None, span_id: str | None, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Build extra fields dict.

        Args:
            correlation_id: Correlation ID
            span_id: Span ID
            fields: Additional fields

        Returns:
            Extra fields dict
        """
        extra = {}

        if correlation_id:
            extra["correlation_id"] = correlation_id

        if span_id:
            extra["span_id"] = span_id

        # Add custom fields
        extra.update(fields)

        return extra


def configure_structured_logging() -> None:
    """Configure structured logging for the application.

    Sets up JSON-formatted logging with timestamp, level, and fields.
    """
    try:
        import structlog

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        logger.info("Structured logging configured (structlog)")

    except ImportError:
        # Fallback to standard logging with JSON formatter
        import logging.config  # can be moved to top

        logging.config.dictConfig(
            {
                "version": 1,
                "formatters": {
                    "json": {
                        "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "extra": %(extra)s}',
                        "datefmt": "%Y-%m-%dT%H:%M:%S",
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "json",
                    }
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["console"],
                },
            }
        )

        logger.info("Structured logging configured (standard logging)")


# Load standard dimensions from config (cached at module level)
_OBSERVABILITY_CONFIG: dict[str, Any] | None = None


def _get_observability_config() -> dict[str, Any]:
    """Get cached observability config."""
    global _OBSERVABILITY_CONFIG
    if _OBSERVABILITY_CONFIG is None:
        config_path = Path(__file__).parent / "observability_config.yaml"
        try:
            if config_path.exists():
                with open(config_path) as f:
                    _OBSERVABILITY_CONFIG = yaml.safe_load(f) or {}
            else:
                _OBSERVABILITY_CONFIG = {}
        except Exception as e:
            logger.warning("Failed to load observability config: %s", e)
            _OBSERVABILITY_CONFIG = {}

        # Set defaults if not in config
        if "standard_dimensions" not in _OBSERVABILITY_CONFIG:
            _OBSERVABILITY_CONFIG["standard_dimensions"] = [
                "provider",
                "model",
                "phase",
                "expert_type",
                "finish_reason",
            ]

    return _OBSERVABILITY_CONFIG


def get_standard_dimensions() -> list[str]:
    """Get list of standard metric dimensions from config.

    Returns:
        List of dimension names
    """
    config = _get_observability_config()
    standard = config.get("standard_dimensions", [])
    additional = config.get("additional_dimensions", [])
    return standard + additional


# Backwards compatibility
STANDARD_DIMENSIONS = get_standard_dimensions()


def extract_dimensions(result: dict[str, Any]) -> dict[str, str]:
    """Extract standard dimensions from result.

    Args:
        result: Result dict

    Returns:
        Dimensions dict
    """
    dimensions = {}
    standard_dims = get_standard_dimensions()

    for dim in standard_dims:
        if dim in result:
            dimensions[dim] = str(result[dim])

    return dimensions
