"""
Inline Citations implementation for citation_injection.
"""

from itertools import count
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


class InlineCitationsImplementation:
    """Inline Citations implementation."""

    def __init__(self) -> None:
        self._name = "inline_citations"
        self._description = "Inline Citations implementation"
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
        citations: list[dict[str, Any]] = metadata.get("citations") or config.get("citations") or []

        marker_counter = count(1)
        inline_markers = []
        for citation in citations:
            idx = next(marker_counter)
            ref = citation.get("ref") or citation.get("source") or f"source-{idx}"
            inline_markers.append(f"[{idx}]")
            citation["marker"] = idx
            citation["ref"] = ref

        if inline_markers:
            content = f"{content} {' '.join(inline_markers)}".strip()

        metadata["citations"] = citations
        return {"content": content, "metadata": metadata}

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
