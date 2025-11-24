"""
Schema Metadata implementation for metadata_injection.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def _extract_content(input_data: Any) -> tuple[str, dict[str, Any]]:
    """Normalize input into content string and metadata dictionary."""
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        metadata = {k: v for k, v in input_data.items() if k != "content"}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class SchemaMetadataImplementation:
    """Schema Metadata implementation."""

    def __init__(self) -> None:
        self._name = "schema_metadata"
        self._description = "Schema Metadata implementation"
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
        content, metadata = _extract_content(input_data)

        schema_fields = config.get("schema_fields") or list(metadata.keys())
        schema_version = config.get("schema_version", "v1")
        schema_source = config.get("schema_source", "inferred")

        metadata["schema"] = {
            "fields": schema_fields,
            "version": schema_version,
            "source": schema_source,
            "generated_at": datetime.utcnow().isoformat() + "Z",
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
        if not isinstance(config, dict):
            msg = "Config must be a dictionary"
            raise TypeError(msg)
        return True
