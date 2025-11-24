"""Single query implementation for multi-query generation.

This implementation returns the original query only without generating variations.
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class SingleQuery:
    """Single query implementation (no multi-query generation)."""

    def __init__(self) -> None:
        self._name = "single"
        self._description = "Return original query only (no multiple queries)"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Return original query without generating variations.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration

        Returns:
            QueryProcessingResult with original query only
        """
        query: str = input_data.get("query", "")

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(query=query, method="single", original_query=query, score=1.0)
            ],
            original_query=query,
            processing_method="multi_query:single",
            metadata={},
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
