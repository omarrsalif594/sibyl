"""
Keyword Filter implementation for content_filtering.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content") or input_data.get("text") or ""
        metadata = {k: v for k, v in input_data.items() if k not in {"content", "text"}}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class KeywordFilterImplementation:
    """Keyword Filter implementation."""

    def __init__(self) -> None:
        self._name = "keyword_filter"
        self._description = "Keyword Filter implementation"
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
        content, metadata = _normalize_input(input_data)
        blocked: list[str] = [
            kw.lower()
            for kw in (config.get("blocked_keywords") or ["password", "secret", "api_key", "token"])
        ]

        matches = [kw for kw in blocked if kw in content.lower()]
        action = config.get("action", "block")
        sanitized = content

        if matches and action == "mask":
            for kw in matches:
                sanitized = sanitized.replace(kw, "***")

        allowed = len(matches) == 0 or action == "mask"
        metadata["content_filter"] = {"matches": matches, "action": action}
        return {"allowed": allowed, "content": sanitized, "metadata": metadata}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        # TODO: Add validation logic
        return True
