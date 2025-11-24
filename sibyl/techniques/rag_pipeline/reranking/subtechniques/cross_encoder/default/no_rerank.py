"""No reranking - pass-through implementation.

This implementation preserves the original ranking without any modifications.
Useful as a baseline or when reranking is not desired.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class NoRerank:
    """Pass-through reranking that preserves original order."""

    def __init__(self) -> None:
        self._name = "no_rerank"
        self._description = "Pass-through implementation that preserves original ranking"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute no-op reranking (preserve original order).

        Args:
            input_data: Dict with 'query', 'items', 'top_k'
            config: Merged configuration

        Returns:
            RerankingResult with items in original order
        """
        query: str = input_data.get("query", "")
        items: list[dict[str, Any]] = input_data.get("items", [])
        top_k: int = input_data.get("top_k", 10)

        if not items:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="cross_encoder:no_rerank",
                total_items=0,
                metadata={"note": "No items to rerank"},
            )

        # Simply preserve original order and take top_k
        ranked_items = []
        for rank, item in enumerate(items[:top_k], start=1):
            ranked_items.append(
                RankedItem(
                    id=item.get("id", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    rank=rank,
                    original_rank=rank,  # Same as new rank since no reranking
                    metadata=item.get("metadata", {}),
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="cross_encoder:no_rerank",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "returned_items": len(ranked_items),
                "note": "Original ranking preserved",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        # No specific configuration needed for pass-through
        return True
