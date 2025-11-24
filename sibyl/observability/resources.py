"""Resource utilization monitoring helpers."""

import logging
import statistics
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources."""

    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float


class ResourceMonitor:
    """Monitor resource utilization during technique execution."""

    def __init__(self, sample_interval_s: float = 1.0) -> None:
        self.sample_interval_s = sample_interval_s
        self.snapshots: list[ResourceSnapshot] = []
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None

    def start_monitoring(self) -> None:
        """Start background resource monitoring."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> dict[str, Any]:
        """Stop monitoring and return summary."""
        if not self._monitor_thread:
            return {}

        self._stop_event.set()
        self._monitor_thread.join(timeout=self.sample_interval_s * 2)
        return self._summarize()

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        process = psutil.Process()

        while not self._stop_event.is_set():
            try:
                snapshot = ResourceSnapshot(
                    timestamp=datetime.utcnow(),
                    cpu_percent=process.cpu_percent(),
                    memory_mb=process.memory_info().rss / 1024 / 1024,
                    memory_percent=process.memory_percent(),
                    disk_io_read_mb=psutil.disk_io_counters().read_bytes / 1024 / 1024,
                    disk_io_write_mb=psutil.disk_io_counters().write_bytes / 1024 / 1024,
                    network_io_sent_mb=psutil.net_io_counters().bytes_sent / 1024 / 1024,
                    network_io_recv_mb=psutil.net_io_counters().bytes_recv / 1024 / 1024,
                )
                self.snapshots.append(snapshot)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Resource monitoring sample failed: %s", exc)
            finally:
                time.sleep(self.sample_interval_s)

    def _summarize(self) -> dict[str, Any]:
        """Summarize resource usage."""
        if not self.snapshots:
            return {"duration_s": 0.0, "samples": 0}

        if len(self.snapshots) == 1:
            return {
                "duration_s": 0.0,
                "samples": 1,
                "cpu_percent_avg": self.snapshots[0].cpu_percent,
                "cpu_percent_max": self.snapshots[0].cpu_percent,
                "memory_mb_avg": self.snapshots[0].memory_mb,
                "memory_mb_max": self.snapshots[0].memory_mb,
                "memory_leaked": 0.0,
            }

        start, end = self.snapshots[0], self.snapshots[-1]
        duration = (end.timestamp - start.timestamp).total_seconds()

        return {
            "duration_s": duration,
            "samples": len(self.snapshots),
            "cpu_percent_avg": statistics.mean(s.cpu_percent for s in self.snapshots),
            "cpu_percent_max": max(s.cpu_percent for s in self.snapshots),
            "memory_mb_avg": statistics.mean(s.memory_mb for s in self.snapshots),
            "memory_mb_max": max(s.memory_mb for s in self.snapshots),
            "memory_leaked": end.memory_mb - start.memory_mb,
            "disk_io_read_mb": max(0.0, end.disk_io_read_mb - start.disk_io_read_mb),
            "disk_io_write_mb": max(0.0, end.disk_io_write_mb - start.disk_io_write_mb),
            "network_io_sent_mb": max(0.0, end.network_io_sent_mb - start.network_io_sent_mb),
            "network_io_recv_mb": max(0.0, end.network_io_recv_mb - start.network_io_recv_mb),
        }


class MetricsCollector:
    """Placeholder metrics collector for resource usage."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("sibyl.metrics.resource")

    def record_resource_usage(
        self,
        resource_summary: dict[str, Any],
        *,
        technique: str | None = None,
        execution_id: str | None = None,
    ) -> None:
        """Record or log resource usage summary."""
        payload = dict(resource_summary)
        if technique:
            payload["technique"] = technique
        if execution_id:
            payload["execution_id"] = execution_id

        try:
            self.logger.info("resource_usage", extra={"resource_usage": payload})
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to record resource usage: %s", exc)
