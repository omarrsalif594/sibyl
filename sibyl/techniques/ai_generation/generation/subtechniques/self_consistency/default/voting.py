"""
Voting implementation for self_consistency.
"""

from collections import Counter
from pathlib import Path
from typing import Any

import yaml


def _normalize_candidates(input_data: Any) -> tuple[list[str], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    if isinstance(input_data, dict):
        candidates = input_data.get("candidates") or []
        metadata = {k: v for k, v in input_data.items() if k != "candidates"}
    elif isinstance(input_data, list):
        candidates = [str(item) for item in input_data]
    else:
        candidates = [str(input_data)] if input_data is not None else []
    return candidates, metadata


class VotingImplementation:
    """Voting implementation."""

    def __init__(self) -> None:
        self._name = "voting"
        self._description = "Voting implementation"
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
        candidates, metadata = _normalize_candidates(input_data)

        if not candidates:
            return {"content": "", "metadata": {"votes": {}, **metadata}}

        counts = Counter(candidates)
        winner, votes = counts.most_common(1)[0]
        confidence = votes / max(len(candidates), 1)

        metadata.update(
            {
                "votes": dict(counts),
                "winner_confidence": confidence,
            }
        )

        return {"content": winner, "metadata": metadata}

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
