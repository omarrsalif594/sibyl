"""
Extractive summarization implementation.

Extracts key sentences and phrases from context using simple text processing
techniques without requiring an LLM. Uses sentence scoring based on:
- Term frequency
- Sentence position
- Keyword presence
- Sentence length
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ExtractiveSummaryResult:
    """Result of extractive summarization."""

    summary: list[dict[str, Any]]
    original_count: int
    summary_count: int
    compression_ratio: float
    extraction_method: str


class ExtractiveImplementation:
    """Extractive summarization implementation.

    Extracts the most important sentences from the context without generating
    new text. Uses heuristic scoring based on term frequency, position, and
    keyword matching.
    """

    def __init__(self) -> None:
        self._name = "extractive"
        self._description = "Extract key sentences/phrases from context (no LLM)"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> ExtractiveSummaryResult:
        """Execute extractive summarization.

        Args:
            input_data: Dict with:
                - messages: List of message dicts with 'content' field
                - context_items: Alternative - list of text items to summarize
            config: Merged configuration with:
                - target_ratio: Target compression ratio (default: 0.3 = keep 30%)
                - min_sentences: Minimum sentences to keep (default: 3)
                - max_sentences: Maximum sentences to keep (default: 20)
                - important_keywords: List of keywords to prioritize (default: [])

        Returns:
            ExtractiveSummaryResult with summarized messages
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
        target_ratio = config.get("target_ratio", 0.3)
        min_sentences = config.get("min_sentences", 3)
        max_sentences = config.get("max_sentences", 20)
        important_keywords = config.get("important_keywords", [])

        logger.debug(
            f"Extractive summarization: {original_count} messages, "
            f"target_ratio={target_ratio}, keywords={len(important_keywords)}"
        )

        # If already small enough, return as-is
        if original_count <= min_sentences:
            return ExtractiveSummaryResult(
                summary=messages,
                original_count=original_count,
                summary_count=original_count,
                compression_ratio=1.0,
                extraction_method="no_compression_needed",
            )

        # Score and rank messages
        scored_messages = self._score_messages(messages, important_keywords)

        # Determine target count
        target_count = max(min_sentences, min(max_sentences, int(original_count * target_ratio)))

        # Select top-scored messages
        sorted_messages = sorted(scored_messages, key=lambda x: x[2], reverse=True)
        top_messages = sorted_messages[:target_count]

        # Restore original order (keep chronological flow)
        selected_indices = sorted([idx for idx, msg, score in top_messages])
        summary = [messages[idx] for idx in selected_indices]

        compression_ratio = len(summary) / original_count if original_count > 0 else 1.0

        logger.debug(
            f"Extractive summary: {original_count} -> {len(summary)} messages "
            f"(ratio={compression_ratio:.2f})"
        )

        return ExtractiveSummaryResult(
            summary=summary,
            original_count=original_count,
            summary_count=len(summary),
            compression_ratio=compression_ratio,
            extraction_method="tf_position_keyword",
        )

    def _score_messages(
        self, messages: list[dict[str, Any]], important_keywords: list[str]
    ) -> list[tuple[int, dict[str, Any], float]]:
        """Score messages based on importance heuristics.

        Returns:
            List of (index, message, score) tuples
        """
        # Extract text content
        texts = []
        for msg in messages:
            if isinstance(msg, dict):
                texts.append(msg.get("content", ""))
            else:
                texts.append(str(msg))

        # Calculate term frequencies across all messages
        all_words = []
        for text in texts:
            words = re.findall(r"\w+", text.lower())
            all_words.extend(words)

        word_freq = Counter(all_words)
        total_words = len(all_words)

        # Score each message
        scored = []
        num_messages = len(messages)

        for idx, (msg, text) in enumerate(zip(messages, texts, strict=False)):
            score = 0.0

            # Tokenize message
            words = re.findall(r"\w+", text.lower())
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # 1. Term frequency score (normalized)
            tf_score = sum(word_freq.get(w, 0) for w in words)
            if total_words > 0:
                score += (tf_score / total_words) * 10

            # 2. Position score (first and last messages are often important)
            if idx == 0:
                score += 5.0  # First message bonus
            elif idx == num_messages - 1:
                score += 3.0  # Last message bonus
            elif idx < num_messages * 0.2:
                score += 2.0  # Early messages bonus

            # 3. Keyword matching score
            if important_keywords:
                keyword_count = sum(
                    1 for keyword in important_keywords if keyword.lower() in text.lower()
                )
                score += keyword_count * 3.0

            # 4. Length score (prefer messages with moderate length)
            word_count = len(words)
            if 10 <= word_count <= 100:
                score += 2.0
            elif word_count > 100:
                score += 1.0  # Long messages might be important but penalize slightly

            # 5. Question bonus (questions often indicate important topics)
            if "?" in text:
                score += 1.5

            # 6. Code/technical content bonus (look for code patterns)
            if "```" in text or re.search(r"def\s+\w+|class\s+\w+|function\s+\w+", text):
                score += 2.0

            scored.append((idx, msg, score))

        return scored

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {
            "target_ratio": 0.3,
            "min_sentences": 3,
            "max_sentences": 20,
            "important_keywords": [],
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        target_ratio = config.get("target_ratio", 0.3)
        min_sentences = config.get("min_sentences", 3)
        max_sentences = config.get("max_sentences", 20)

        if not (0.0 < target_ratio <= 1.0):
            msg = f"target_ratio must be between 0 and 1, got {target_ratio}"
            raise ValueError(msg)

        if not isinstance(min_sentences, int) or min_sentences < 1:
            msg = f"min_sentences must be a positive integer, got {min_sentences}"
            raise ValueError(msg)

        if not isinstance(max_sentences, int) or max_sentences < min_sentences:
            msg = f"max_sentences must be >= min_sentences, got {max_sentences} < {min_sentences}"
            raise ValueError(msg)

        return True
