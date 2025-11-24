"""No expansion implementation for query expansion.

This implementation returns the original query without any expansion.
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class NoExpansion:
    """No-op query expansion implementation."""

    def __init__(self) -> None:
        self._name = "no_expansion"
        self._description = "Pass-through without query expansion"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Return original query without expansion.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration

        Returns:
            QueryProcessingResult with original query only
        """
        query: str = input_data.get("query", "")

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(query=query, method="no_expansion", original_query=query)
            ],
            original_query=query,
            processing_method="query_expansion:no_expansion",
            metadata={},
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
