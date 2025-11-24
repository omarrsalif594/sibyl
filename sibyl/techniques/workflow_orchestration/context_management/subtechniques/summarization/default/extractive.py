"""
Extractive implementation for summarization.

Extracts key sentences/phrases from context based on term frequency.
"""

import re
from collections import Counter
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


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple heuristics."""
    # Simple sentence splitting on period, exclamation, question mark
    sentences = re.split(r"[.!?]+\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def score_sentences(sentences: list[str]) -> list[tuple]:
    """Score sentences based on term frequency.

    Returns:
        List of (sentence, score) tuples
    """
    # Tokenize all sentences and count term frequency
    all_words = []
    for sentence in sentences:
        words = re.findall(r"\b\w+\b", sentence.lower())
        all_words.extend(words)

    # Count word frequency (excluding very short words)
    word_freq = Counter(w for w in all_words if len(w) > 3)

    # Score each sentence based on sum of word frequencies
    scored_sentences = []
    for sentence in sentences:
        words = re.findall(r"\b\w+\b", sentence.lower())
        score = sum(word_freq.get(w, 0) for w in words if len(w) > 3)
        # Normalize by sentence length to avoid bias toward long sentences
        if words:
            score = score / len(words)
        scored_sentences.append((sentence, score))

    return scored_sentences


class ExtractiveImplementation:
    """Extractive summarization implementation.

    Extracts key sentences/phrases from context based on term frequency,
    selecting the most important content.
    """

    def __init__(self) -> None:
        self._name = "extractive"
        self._description = "Extract key sentences based on term frequency"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute extractive summarization.

        Args:
            input_data: Dict with "context_items" (List[ContextItem]) and "target_tokens" (int)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with summarized context
        """
        context_items: list[ContextItem] = input_data.get("context_items", [])
        target_tokens: int = input_data.get("target_tokens", 1000)

        # Combine all content
        combined_content = "\n\n".join(item.content for item in context_items)

        # Split into sentences
        sentences = split_sentences(combined_content)

        if not sentences:
            # No content to summarize
            empty_item = ContextItem(id="summary", content="", priority=1.0, token_count=0)
            context_state = ContextState(
                items=[empty_item],
                total_tokens=0,
                capacity_tokens=target_tokens,
                utilization=0.0,
                metadata={"summarization_strategy": "extractive"},
            )
            return ContextManagementResult(
                context_state=context_state,
                operation="extractive_summarization",
                items_kept=1,
                items_removed=len(context_items),
                tokens_saved=sum(estimate_tokens(item.content) for item in context_items),
                metadata={"target_tokens": target_tokens},
            )

        # Score sentences
        scored_sentences = score_sentences(sentences)

        # Sort by score (highest first)
        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        # Select sentences until we reach target tokens
        selected_sentences = []
        current_tokens = 0

        for sentence, _score in scored_sentences:
            sentence_tokens = estimate_tokens(sentence)
            if current_tokens + sentence_tokens <= target_tokens:
                selected_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break

        # Create summary content (maintain original order)
        summary_sentences = []
        for sentence in sentences:
            if sentence in selected_sentences:
                summary_sentences.append(sentence)

        summary_content = ". ".join(summary_sentences)
        if summary_content and not summary_content.endswith("."):
            summary_content += "."

        # Calculate token savings
        original_tokens = sum(estimate_tokens(item.content) for item in context_items)
        summary_tokens = estimate_tokens(summary_content)

        # Create summarized context item
        summary_item = ContextItem(
            id="summary",
            content=summary_content,
            priority=1.0,
            token_count=summary_tokens,
            metadata={
                "original_items": len(context_items),
                "sentences_selected": len(selected_sentences),
                "sentences_total": len(sentences),
            },
        )

        # Create context state
        context_state = ContextState(
            items=[summary_item],
            total_tokens=summary_tokens,
            capacity_tokens=target_tokens,
            utilization=summary_tokens / target_tokens if target_tokens > 0 else 0.0,
            metadata={
                "summarization_strategy": "extractive",
                "original_tokens": original_tokens,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="extractive_summarization",
            items_kept=1,
            items_removed=len(context_items),
            tokens_saved=original_tokens - summary_tokens,
            metadata={
                "target_tokens": target_tokens,
                "compression_ratio": summary_tokens / original_tokens
                if original_tokens > 0
                else 0.0,
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {
            "default_target_tokens": 1000,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "target_tokens" in config:
            if not isinstance(config["target_tokens"], int) or config["target_tokens"] <= 0:
                return False
        return True
