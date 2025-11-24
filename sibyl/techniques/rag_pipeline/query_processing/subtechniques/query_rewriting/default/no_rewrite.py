"""No rewrite implementation for query rewriting.

This implementation returns the original query without any rewriting.
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class NoRewrite:
    """No-op query rewriting implementation."""

    def __init__(self) -> None:
        self._name = "no_rewrite"
        self._description = "Pass-through without query rewriting"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Return original query without rewriting.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration

        Returns:
            QueryProcessingResult with original query only
        """
        query: str = input_data.get("query", "")

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(query=query, method="no_rewrite", original_query=query)
            ],
            original_query=query,
            processing_method="query_rewriting:no_rewrite",
            metadata={},
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
