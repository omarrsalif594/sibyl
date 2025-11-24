"""
Relevance implementation for prioritization.

Prioritizes context items based on relevance to a query using keyword matching.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.workflow_orchestration.context_management.protocols import (
    ContextItem,
    ContextManagementResult,
    ContextState,
)


def estimate_tokens(text: str) -> int:
    """Estimate token count using simple whitespace splitting with 1.3x multiplier."""
    return int(len(text.split()) * 1.3)


def extract_keywords(text: str) -> set[str]:
    """Extract keywords from text (words longer than 3 chars)."""
    words = re.findall(r"\b\w+\b", text.lower())
    return {w for w in words if len(w) > 3}


def calculate_relevance_score(item_content: str, query: str) -> float:
    """Calculate relevance score based on keyword matching.

    Args:
        item_content: Content to score
        query: Query to match against

    Returns:
        Relevance score between 0.0 and 1.0
    """
    if not query or not item_content:
        return 0.0

    # Extract keywords from query and content
    query_keywords = extract_keywords(query)
    content_keywords = extract_keywords(item_content)

    if not query_keywords:
        return 0.0

    # Calculate overlap
    matching_keywords = query_keywords & content_keywords

    # Score based on percentage of query keywords found
    base_score = len(matching_keywords) / len(query_keywords)

    # Boost score if content has all query keywords
    if matching_keywords == query_keywords:
        base_score = min(1.0, base_score * 1.2)

    # Additional boost for exact phrase matches
    query_lower = query.lower()
    if query_lower in item_content.lower():
        base_score = min(1.0, base_score + 0.2)

    return min(1.0, base_score)


class RelevanceImplementation:
    """Relevance prioritization implementation.

    Prioritizes context items based on relevance to a query using
    simple keyword matching.
    """

    def __init__(self) -> None:
        self._name = "relevance"
        self._description = "Prioritize based on relevance to query using keyword matching"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute relevance-based prioritization.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and optional "query" (str)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with prioritized context items
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        query: str | None = input_data.get("query")

        # Calculate relevance scores
        for item in context_items:
            if query:
                relevance_score = calculate_relevance_score(item.content, query)
                item.relevance_score = relevance_score
                item.priority = relevance_score
            else:
                # No query provided, all items have equal relevance
                item.relevance_score = 0.5
                item.priority = 0.5

        # Sort by relevance score (highest first)
        sorted_items = sorted(context_items, key=lambda x: x.relevance_score or 0.0, reverse=True)

        # Calculate token counts if not present
        for item in sorted_items:
            if item.token_count is None:
                item.token_count = estimate_tokens(item.content)

        # Calculate stats
        total_tokens = sum(item.token_count for item in sorted_items)

        # Create context state
        context_state = ContextState(
            items=sorted_items,
            total_tokens=total_tokens,
            capacity_tokens=total_tokens,
            utilization=1.0,
            metadata={
                "prioritization_strategy": "relevance",
                "sort_order": "most_relevant_first",
                "query_provided": query is not None,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="relevance_prioritization",
            items_kept=len(sorted_items),
            items_removed=0,
            tokens_saved=0,
            metadata={
                "strategy": "relevance",
                "items_processed": len(context_items),
                "query": query if query else "none",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
