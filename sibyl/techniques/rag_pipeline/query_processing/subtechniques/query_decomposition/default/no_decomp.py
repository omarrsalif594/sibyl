"""No decomposition implementation for query decomposition.

This implementation returns the original query without decomposing it.
"""

from pathlib import Path
from typing import Any

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class NoDecomposition:
    """No decomposition implementation (returns original query)."""

    def __init__(self) -> None:
        self._name = "no_decomp"
        self._description = "No decomposition, return original query"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Return original query without decomposition.

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
                    query=query, method="no_decomposition", original_query=query, score=1.0
                )
            ],
            original_query=query,
            processing_method="query_decomposition:no_decomp",
            metadata={"decomposed": False},
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
