"""Structured logging for technique execution."""

import json
import logging
from datetime import datetime
from typing import Any


class StructuredLogger:
    """Structured logging for techniques."""

    def __init__(self, technique_name: str) -> None:
        self.logger = logging.getLogger(f"sibyl.techniques.{technique_name}")
        self.technique_name = technique_name

        # Configure ELK/Datadog style JSON output
        handler = logging.StreamHandler()
        handler.setFormatter(self._get_formatter())

        # Avoid duplicating handlers when multiple instances are created
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _get_formatter(self) -> Any:
        """JSON formatter for structured logging."""

        class JSONFormatter(logging.Formatter):
            def format(self, record: Any) -> Any:  # type: ignore[override]
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "technique": getattr(record, "technique", None),
                    "subtechnique": getattr(record, "subtechnique", None),
                    "implementation": getattr(record, "implementation", None),
                    "execution_id": getattr(record, "execution_id", None),
                    "user_id": getattr(record, "user_id", None),
                    "session_id": getattr(record, "session_id", None),
                }

                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_data)

        return JSONFormatter()

    def log_execution(
        self,
        subtechnique: str,
        implementation: str,
        input_data: Any,
        config: dict[str, Any],
        **extra: Any,
    ) -> None:
        """Log technique execution."""
        try:
            config_hash = hash(json.dumps(config, sort_keys=True, default=str))
        except Exception:
            config_hash = None

        self.logger.info(
            f"Executing {self.technique_name}.{subtechnique}:{implementation}",
            extra={
                "technique": self.technique_name,
                "subtechnique": subtechnique,
                "implementation": implementation,
                "input_size": len(str(input_data)),
                "config_hash": config_hash,
                **extra,
            },
        )

    def log_error(self, error: Exception, context: dict[str, Any]) -> None:
        """Log error with context."""
        self.logger.error(
            f"Error in {self.technique_name}: {error!s}",
            extra={
                "technique": self.technique_name,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context,
            },
            exc_info=True,
        )
