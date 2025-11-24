"""
Entity Compression implementation for compression.

Compresses content by extracting and preserving entities while removing filler words.
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


# Common filler words to remove
FILLER_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "there",
    "here",
    "very",
}


def extract_entities(text: str) -> set[str]:
    """Extract entities (capitalized words, likely nouns/named entities)."""
    # Find capitalized words that are likely entities
    words = text.split()
    entities = set()

    for word in words:
        # Remove punctuation
        clean_word = re.sub(r"[^\w]", "", word)
        # Check if starts with capital and is not at sentence start
        if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
            entities.add(clean_word)

    return entities


def compress_entities(content: str, target_ratio: float) -> str:
    """Compress content by preserving entities and removing filler words.

    Args:
        content: Content to compress
        target_ratio: Target compression ratio (0.0 to 1.0)

    Returns:
        Compressed content
    """
    if not content:
        return ""

    # Extract entities
    entities = extract_entities(content)

    # Split into sentences
    sentences = re.split(r"[.!?]+", content)
    compressed_sentences = []

    for sentence in sentences:
        if not sentence.strip():
            continue

        words = sentence.split()
        # Keep entities and significant words (non-filler, longer words)
        kept_words = []

        for word in words:
            clean_word = re.sub(r"[^\w]", "", word)
            lower_word = clean_word.lower()

            # Keep if it's an entity or a significant word
            if clean_word in entities or (lower_word not in FILLER_WORDS and len(clean_word) > 3):
                kept_words.append(word)

        if kept_words:
            compressed_sentences.append(" ".join(kept_words))

    compressed = ". ".join(compressed_sentences)
    if compressed and not compressed.endswith("."):
        compressed += "."

    # Further compress if needed to meet target ratio
    current_ratio = len(compressed) / len(content) if content else 1.0
    if current_ratio > target_ratio and compressed:
        # Trim to target length
        target_length = int(len(content) * target_ratio)
        if len(compressed) > target_length:
            compressed = compressed[:target_length].rsplit(" ", 1)[0] + "..."

    return compressed


class EntityCompressionImplementation:
    """Entity Compression implementation.

    Compresses content by extracting and preserving entities (nouns, named entities)
    while removing filler words and redundancy.
    """

    def __init__(self) -> None:
        self._name = "entity_compression"
        self._description = "Compress by preserving entities and removing filler words"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute entity compression.

        Args:
            input_data: Dict with "content" (str) and "target_ratio" (float)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with compressed content
        """
        content: str = input_data.get("content", "")
        target_ratio: float = input_data.get("target_ratio", 0.5)

        # Compress content
        compressed_content = compress_entities(content, target_ratio)

        # Calculate token savings
        original_tokens = estimate_tokens(content)
        compressed_tokens = estimate_tokens(compressed_content)

        # Create compressed context item
        compressed_item = ContextItem(
            id="compressed",
            content=compressed_content,
            priority=1.0,
            token_count=compressed_tokens,
            metadata={
                "compression_type": "entity_compression",
                "original_length": len(content),
                "compressed_length": len(compressed_content),
            },
        )

        # Create context state
        context_state = ContextState(
            items=[compressed_item],
            total_tokens=compressed_tokens,
            capacity_tokens=original_tokens,
            utilization=compressed_tokens / original_tokens if original_tokens > 0 else 0.0,
            metadata={
                "compression_strategy": "entity_compression",
                "original_tokens": original_tokens,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="entity_compression",
            items_kept=1,
            items_removed=0,
            tokens_saved=original_tokens - compressed_tokens,
            metadata={
                "target_ratio": target_ratio,
                "actual_ratio": compressed_tokens / original_tokens if original_tokens > 0 else 0.0,
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {
            "default_target_ratio": 0.5,
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "target_ratio" in config:
            ratio = config["target_ratio"]
            if not isinstance(ratio, (int, float)) or ratio <= 0 or ratio > 1:
                return False
        return True
