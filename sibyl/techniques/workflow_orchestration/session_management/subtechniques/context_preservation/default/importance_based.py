"""
Importance-based context preservation implementation.

Scores messages by importance and keeps the top-K most important ones.
More sophisticated than sliding window, preserving critical context
while dropping less important messages.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ImportanceBasedResult:
    """Result of importance-based context preservation."""

    preserved_messages: list[dict[str, Any]]
    original_count: int
    preserved_count: int
    dropped_count: int
    min_importance_score: float
    scoring_method: str


class ImportanceBasedImplementation:
    """Importance-based context preservation.

    Scores each message based on multiple importance factors:
    - Message role (user questions, system messages)
    - Content length and complexity
    - Presence of keywords or technical terms
    - References to code, errors, or decisions
    - Recency (recent messages get a slight boost)

    Keeps top-K messages by importance score, or all messages above
    a threshold score.
    """

    def __init__(self) -> None:
        self._name = "importance_based"
        self._description = "Score messages by importance, keep top-K"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> ImportanceBasedResult:
        """Execute importance-based context preservation.

        Args:
            input_data: Dict with:
                - messages: List of message dicts with 'content' field
                - context_items: Alternative - list of items to filter
            config: Merged configuration with:
                - top_k: Number of top messages to keep (default: 15)
                - importance_threshold: Minimum importance score (default: 0.0)
                - recency_weight: Weight for recency bonus (default: 0.2)
                - preserve_first: Always keep first message (default: True)
                - preserve_last: Always keep last N messages (default: 2)

        Returns:
            ImportanceBasedResult with most important messages preserved
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        # Extract messages
        messages = input_data.get("messages", [])
        if not messages:
            context_items = input_data.get("context_items", [])
            if isinstance(context_items, list):
                messages = [{"content": str(item)} for item in context_items]

        if not isinstance(messages, list):
            msg = "messages must be a list"
            raise TypeError(msg)

        original_count = len(messages)

        # Get configuration
        top_k = config.get("top_k", 15)
        importance_threshold = config.get("importance_threshold", 0.0)
        recency_weight = config.get("recency_weight", 0.2)
        preserve_first = config.get("preserve_first", True)
        preserve_last = config.get("preserve_last", 2)

        logger.debug(
            f"Importance-based filtering: {original_count} messages, "
            f"top_k={top_k}, threshold={importance_threshold}"
        )

        # If count is already low, keep all
        if original_count <= top_k:
            return ImportanceBasedResult(
                preserved_messages=messages,
                original_count=original_count,
                preserved_count=original_count,
                dropped_count=0,
                min_importance_score=0.0,
                scoring_method="no_filtering_needed",
            )

        # Score all messages
        scored_messages = self._score_messages(messages, recency_weight)

        # Separate preserved messages (first/last) from scoreable ones
        preserved_indices = set()

        if preserve_first and original_count > 0:
            preserved_indices.add(0)

        if preserve_last > 0:
            for i in range(max(0, original_count - preserve_last), original_count):
                preserved_indices.add(i)

        # Filter out preserved messages from scoring
        scoreable = [
            (idx, msg, score) for idx, msg, score in scored_messages if idx not in preserved_indices
        ]

        # Sort by importance score
        scoreable.sort(key=lambda x: x[2], reverse=True)

        # Determine how many more we can select
        slots_remaining = max(0, top_k - len(preserved_indices))

        # Select top-K from scoreable messages
        selected_scoreable = scoreable[:slots_remaining]

        # Apply importance threshold filter
        if importance_threshold > 0:
            selected_scoreable = [
                (idx, msg, score)
                for idx, msg, score in selected_scoreable
                if score >= importance_threshold
            ]

        # Combine preserved and selected indices
        selected_indices = preserved_indices | {idx for idx, _, _ in selected_scoreable}

        # Sort indices to maintain chronological order
        selected_indices = sorted(selected_indices)

        # Build final message list
        preserved_messages = [messages[idx] for idx in selected_indices]

        preserved_count = len(preserved_messages)
        dropped_count = original_count - preserved_count

        # Calculate minimum importance score
        min_score = min(score for _, _, score in selected_scoreable) if selected_scoreable else 0.0

        logger.debug(
            f"Importance filtering: kept {preserved_count}, dropped {dropped_count}, "
            f"min_score={min_score:.2f}"
        )

        return ImportanceBasedResult(
            preserved_messages=preserved_messages,
            original_count=original_count,
            preserved_count=preserved_count,
            dropped_count=dropped_count,
            min_importance_score=min_score,
            scoring_method="multi_factor",
        )

    def _score_messages(
        self, messages: list[dict[str, Any]], recency_weight: float
    ) -> list[tuple[int, dict[str, Any], float]]:
        """Score messages based on importance heuristics.

        Returns:
            List of (index, message, score) tuples
        """
        scored = []
        num_messages = len(messages)

        for idx, msg in enumerate(messages):
            score = 0.0

            # Extract content and role
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "user")
            else:
                content = str(msg)
                role = "user"

            # 1. Role-based scoring
            if role == "system":
                score += 5.0  # System messages often contain important context
            elif role == "user":
                score += 3.0  # User messages contain questions/requests
            elif role == "assistant":
                score += 2.0  # Assistant responses

            # 2. Question detection (important for context)
            if "?" in content:
                score += 4.0

            # 3. Length score (moderate length often indicates substance)
            word_count = len(content.split())
            if 20 <= word_count <= 150:
                score += 3.0
            elif word_count > 150:
                score += 2.0  # Very long might be important
            elif word_count >= 10:
                score += 1.0

            # 4. Technical content detection
            code_patterns = [
                r"```",  # Code blocks
                r"def\s+\w+",  # Python functions
                r"class\s+\w+",  # Class definitions
                r"function\s+\w+",  # JS functions
                r"import\s+",  # Imports
                r"from\s+\w+\s+import",  # Python imports
            ]
            for pattern in code_patterns:
                if re.search(pattern, content):
                    score += 2.0
                    break

            # 5. Error/warning detection
            error_keywords = ["error", "exception", "traceback", "warning", "failed", "issue"]
            if any(keyword in content.lower() for keyword in error_keywords):
                score += 3.0

            # 6. Decision/action keywords
            action_keywords = ["decided", "implemented", "changed", "updated", "fixed", "created"]
            if any(keyword in content.lower() for keyword in action_keywords):
                score += 2.5

            # 7. Reference keywords (indicates important context)
            reference_keywords = ["because", "therefore", "however", "note that", "important"]
            if any(keyword in content.lower() for keyword in reference_keywords):
                score += 1.5

            # 8. Recency bonus (more recent = slightly more important)
            if recency_weight > 0:
                recency_score = (idx / num_messages) * recency_weight * 5.0
                score += recency_score

            # 9. Metadata importance (if provided)
            if isinstance(msg, dict):
                metadata = msg.get("metadata", {})
                if metadata.get("important", False):
                    score += 5.0
                if "importance_score" in metadata:
                    score += metadata["importance_score"]

            scored.append((idx, msg, score))

        return scored

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {
            "top_k": 15,
            "importance_threshold": 0.0,
            "recency_weight": 0.2,
            "preserve_first": True,
            "preserve_last": 2,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        top_k = config.get("top_k", 15)
        importance_threshold = config.get("importance_threshold", 0.0)
        recency_weight = config.get("recency_weight", 0.2)
        preserve_last = config.get("preserve_last", 2)

        if not isinstance(top_k, int) or top_k < 1:
            msg = f"top_k must be a positive integer, got {top_k}"
            raise ValueError(msg)

        if not isinstance(importance_threshold, (int, float)):
            msg = f"importance_threshold must be numeric, got {type(importance_threshold)}"
            raise TypeError(msg)

        if not (0.0 <= recency_weight <= 1.0):
            msg = f"recency_weight must be between 0 and 1, got {recency_weight}"
            raise ValueError(msg)

        if not isinstance(preserve_last, int) or preserve_last < 0:
            msg = f"preserve_last must be a non-negative integer, got {preserve_last}"
            raise ValueError(msg)

        if top_k > 100:
            logger.warning("top_k %s is very large. Consider using full_history instead.", top_k)

        return True
