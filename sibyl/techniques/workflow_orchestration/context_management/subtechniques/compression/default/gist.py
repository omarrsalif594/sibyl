"""
Gist implementation for compression.

Extracts the gist/core meaning by keeping main points and removing details.
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


def extract_gist(content: str, target_ratio: float) -> str:
    """Extract the gist/core meaning from content.

    Args:
        content: Content to extract gist from
        target_ratio: Target compression ratio (0.0 to 1.0)

    Returns:
        Gist of the content
    """
    if not content:
        return ""

    # Split into sentences
    sentences = re.split(r"[.!?]+\s+", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return ""

    # Score sentences based on information density
    # Use word count and presence of significant words
    scored_sentences = []

    for sentence in sentences:
        words = re.findall(r"\b\w+\b", sentence.lower())
        # Filter short/common words
        significant_words = [w for w in words if len(w) > 4]

        # Score based on number of significant words and sentence position
        # (first and last sentences often contain important info)
        score = len(significant_words)

        # Boost score for sentences with certain keywords
        keywords = [
            "important",
            "key",
            "main",
            "primary",
            "essential",
            "critical",
            "summary",
            "conclusion",
            "therefore",
            "thus",
            "result",
        ]
        for keyword in keywords:
            if keyword in sentence.lower():
                score += 2

        scored_sentences.append((sentence, score))

    # Sort by score
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    # Select top sentences to meet target ratio
    target_length = int(len(content) * target_ratio)
    selected_sentences = []
    current_length = 0

    for sentence, score in scored_sentences:
        if current_length + len(sentence) <= target_length:
            selected_sentences.append(sentence)
            current_length += len(sentence)
        else:
            break

    # Reorder selected sentences to maintain flow
    # (preserve original order where possible)
    ordered_sentences = []
    for sentence in sentences:
        if sentence in selected_sentences:
            ordered_sentences.append(sentence)

    gist = ". ".join(ordered_sentences)
    if gist and not gist.endswith("."):
        gist += "."

    return gist


class GistImplementation:
    """Gist compression implementation.

    Extracts the gist/core meaning by keeping main points and
    removing details.
    """

    def __init__(self) -> None:
        self._name = "gist"
        self._description = "Extract gist/core meaning, removing details"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ContextManagementResult:
        """Execute gist compression.

        Args:
            input_data: Dict with "content" (str) and "target_ratio" (float)
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            ContextManagementResult with compressed content
        """
        content: str = input_data.get("content", "")
        target_ratio: float = input_data.get("target_ratio", 0.5)

        # Extract gist
        gist_content = extract_gist(content, target_ratio)

        # Calculate token savings
        original_tokens = estimate_tokens(content)
        gist_tokens = estimate_tokens(gist_content)

        # Create compressed context item
        gist_item = ContextItem(
            id="gist",
            content=gist_content,
            priority=1.0,
            token_count=gist_tokens,
            metadata={
                "compression_type": "gist",
                "original_length": len(content),
                "gist_length": len(gist_content),
            },
        )

        # Create context state
        context_state = ContextState(
            items=[gist_item],
            total_tokens=gist_tokens,
            capacity_tokens=original_tokens,
            utilization=gist_tokens / original_tokens if original_tokens > 0 else 0.0,
            metadata={
                "compression_strategy": "gist",
                "original_tokens": original_tokens,
            },
        )

        # Create result
        return ContextManagementResult(
            context_state=context_state,
            operation="gist_compression",
            items_kept=1,
            items_removed=0,
            tokens_saved=original_tokens - gist_tokens,
            metadata={
                "target_ratio": target_ratio,
                "actual_ratio": gist_tokens / original_tokens if original_tokens > 0 else 0.0,
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
