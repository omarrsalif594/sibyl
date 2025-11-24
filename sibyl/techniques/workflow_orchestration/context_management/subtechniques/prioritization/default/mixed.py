"""
Mixed implementation for prioritization.

Combines recency and relevance scores with configurable weights.
"""

import re
import time
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


def calculate_recency_score(timestamp: float, max_timestamp: float, min_timestamp: float) -> float:
    """Calculate recency score normalized between 0.0 and 1.0.

    Args:
        timestamp: Item timestamp
        max_timestamp: Most recent timestamp
        min_timestamp: Oldest timestamp

    Returns:
        Recency score between 0.0 and 1.0
    """
    if max_timestamp == min_timestamp:
        return 1.0

    # Normalize to 0-1 range
    return (timestamp - min_timestamp) / (max_timestamp - min_timestamp)


class MixedImplementation:
    """Mixed prioritization implementation.

    Combines recency and relevance scores with configurable weights
    (default 50/50).
    """

    def __init__(self) -> None:
        self._name = "mixed"
        self._description = "Combine recency and relevance scores with configurable weights"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute mixed prioritization.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and optional "query" (str)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with prioritized context items
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        query: str | None = input_data.get("query")

        # Get weights from config (default 50/50)
        recency_weight: float = config.get("recency_weight", 0.5)
        relevance_weight: float = config.get("relevance_weight", 0.5)

        # Normalize weights to sum to 1.0
        total_weight = recency_weight + relevance_weight
        if total_weight > 0:
            recency_weight /= total_weight
            relevance_weight /= total_weight
        else:
            recency_weight = 0.5
            relevance_weight = 0.5

        # Assign timestamps if not present
        current_time = time.time()
        for item in context_items:
            if item.timestamp is None:
                item.timestamp = current_time

        # Calculate timestamp range
        timestamps = [item.timestamp for item in context_items if item.timestamp is not None]
        if timestamps:
            max_timestamp = max(timestamps)
            min_timestamp = min(timestamps)
        else:
            max_timestamp = current_time
            min_timestamp = current_time

        # Calculate mixed scores
        for item in context_items:
            # Calculate recency score
            recency_score = calculate_recency_score(
                item.timestamp or current_time, max_timestamp, min_timestamp
            )

            # Calculate relevance score
            if query:
                relevance_score = calculate_relevance_score(item.content, query)
            else:
                relevance_score = 0.5  # Neutral score if no query

            # Store individual scores
            item.relevance_score = relevance_score

            # Calculate mixed priority
            mixed_priority = (recency_weight * recency_score) + (relevance_weight * relevance_score)
            item.priority = mixed_priority

        # Sort by mixed priority (highest first)
        sorted_items = sorted(context_items, key=lambda x: x.priority, reverse=True)

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
                "prioritization_strategy": "mixed",
                "sort_order": "highest_priority_first",
                "recency_weight": recency_weight,
                "relevance_weight": relevance_weight,
                "query_provided": query is not None,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="mixed_prioritization",
            items_kept=len(sorted_items),
            items_removed=0,
            tokens_saved=0,
            metadata={
                "strategy": "mixed",
                "items_processed": len(context_items),
                "recency_weight": recency_weight,
                "relevance_weight": relevance_weight,
                "query": query if query else "none",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {
            "recency_weight": 0.5,
            "relevance_weight": 0.5,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "recency_weight" in config:
            weight = config["recency_weight"]
            if not isinstance(weight, (int, float)) or weight < 0:
                return False
        if "relevance_weight" in config:
            weight = config["relevance_weight"]
            if not isinstance(weight, (int, float)) or weight < 0:
                return False
        return True
