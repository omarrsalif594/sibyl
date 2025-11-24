"""
Recency implementation for temporal_context.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def _normalize(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        metadata = {k: v for k, v in input_data.items() if k != "content"}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


def _parse_timestamp(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class RecencyImplementation:
    """Recency implementation."""

    def __init__(self) -> None:
        self._name = "recency"
        self._description = "Recency implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """Execute the implementation.

        Args:
            input_data: Input data to process
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            Implementation-specific output
        """
        content, metadata = _normalize(input_data)
        now = datetime.now(UTC)
        freshness_window = config.get("freshness_seconds", 3600)

        raw_timestamp = (
            metadata.get("timestamp", {}).get("value")
            if isinstance(metadata.get("timestamp"), dict)
            else metadata.get("timestamp")
        )
        ts = _parse_timestamp(raw_timestamp)

        if ts:
            delta = (now - ts).total_seconds()
            freshness = "fresh" if delta <= freshness_window else "stale"
        else:
            freshness = "unknown"

        metadata["recency"] = {
            "status": freshness,
            "evaluated_at": now.isoformat(),
            "window_seconds": freshness_window,
        }

        return {"content": content, "metadata": metadata}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if not isinstance(config.get("freshness_seconds", 0), (int, float)):
            msg = "freshness_seconds must be numeric"
            raise TypeError(msg)
        return True
