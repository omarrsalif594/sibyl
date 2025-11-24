"""
Abstractive Simple implementation for summarization.

Simple abstractive summarization using templates to create condensed versions.
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


def extract_key_phrases(text: str, max_phrases: int = 10) -> list[str]:
    """Extract key phrases from text using simple word frequency."""
    # Tokenize and count words
    words = re.findall(r"\b\w+\b", text.lower())
    # Filter out short words
    meaningful_words = [w for w in words if len(w) > 4]

    # Get most common words
    word_freq = Counter(meaningful_words)
    return [word for word, count in word_freq.most_common(max_phrases)]


def create_abstractive_summary(content: str, target_tokens: int) -> str:
    """Create a simple abstractive summary using templates.

    Args:
        content: Content to summarize
        target_tokens: Target token count

    Returns:
        Abstractive summary
    """
    # Extract key phrases
    key_phrases = extract_key_phrases(content, max_phrases=15)

    if not key_phrases:
        return "No significant content found."

    # Create a templated summary
    summary_parts = []

    # Build summary based on key phrases
    if len(key_phrases) >= 3:
        summary_parts.append(
            f"This content discusses {key_phrases[0]}, {key_phrases[1]}, and {key_phrases[2]}."
        )
    elif len(key_phrases) >= 2:
        summary_parts.append(f"This content discusses {key_phrases[0]} and {key_phrases[1]}.")
    elif len(key_phrases) >= 1:
        summary_parts.append(f"This content discusses {key_phrases[0]}.")

    # Add more key topics if we have room
    if len(key_phrases) > 3:
        remaining_phrases = key_phrases[3 : min(8, len(key_phrases))]
        if remaining_phrases:
            topics_list = ", ".join(remaining_phrases)
            summary_parts.append(f"Key topics include: {topics_list}.")

    # Combine summary parts
    summary = " ".join(summary_parts)

    # Trim to target tokens if needed
    current_tokens = estimate_tokens(summary)
    if current_tokens > target_tokens:
        # Truncate to fit
        words = summary.split()
        target_words = int(target_tokens / 1.3)
        summary = " ".join(words[:target_words]) + "..."

    return summary


class AbstractiveSimpleImplementation:
    """Abstractive Simple summarization implementation.

    Simple abstractive summarization using templates to create condensed
    versions of content without external API calls.
    """

    def __init__(self) -> None:
        self._name = "abstractive_simple"
        self._description = "Simple abstractive summarization using templates"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute abstractive summarization.

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

        # Create abstractive summary
        summary_content = create_abstractive_summary(combined_content, target_tokens)

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
                "summarization_type": "abstractive",
            },
        )

        # Create context state
        context_state = ContextState(
            items=[summary_item],
            total_tokens=summary_tokens,
            capacity_tokens=target_tokens,
            utilization=summary_tokens / target_tokens if target_tokens > 0 else 0.0,
            metadata={
                "summarization_strategy": "abstractive_simple",
                "original_tokens": original_tokens,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="abstractive_summarization",
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
            "max_key_phrases": 15,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "target_tokens" in config:
            if not isinstance(config["target_tokens"], int) or config["target_tokens"] <= 0:
                return False
        if "max_key_phrases" in config:
            if not isinstance(config["max_key_phrases"], int) or config["max_key_phrases"] <= 0:
                return False
        return True
