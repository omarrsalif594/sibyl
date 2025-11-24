"""
File Log implementation for audit_logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class FileLogImplementation:
    """File Log implementation."""

    def __init__(self) -> None:
        self._name = "file_log"
        self._description = "File Log implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._logs: list[dict[str, Any]] = []

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
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": input_data,
        }
        self._logs.append(entry)

        file_path = config.get("file_path")
        if file_path:
            try:
                with open(file_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                # Keep in-memory log even if file write fails
                logger.debug(f"Failed to write audit log to file: {e}")

        return {"logged": True, "count": len(self._logs), "path": file_path}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return isinstance(config, dict)
