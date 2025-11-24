"""Disabled HyDE implementation.

This implementation returns the original query without generating hypothetical documents.
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class DisabledHyDE:
    """Disabled HyDE implementation (no hypothetical document generation)."""

    def __init__(self) -> None:
        self._name = "disabled"
        self._description = "No HyDE generation, return original query"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Return original query without HyDE generation.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration

        Returns:
            QueryProcessingResult with original query only
        """
        query: str = input_data.get("query", "")

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(
                    query=query,
                    method="disabled_hyde",
                    original_query=query,
                    metadata={"is_hypothetical": False},
                )
            ],
            original_query=query,
            processing_method="hyde:disabled",
            metadata={},
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
