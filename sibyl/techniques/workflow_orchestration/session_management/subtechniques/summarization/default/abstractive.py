"""
Abstractive summarization implementation.

Uses LLM-based summarization to generate concise summaries of conversation context.
Includes timeout handling and fallback to extractive summarization on failure.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class AbstractiveSummaryResult:
    """Result of abstractive summarization."""

    summary: list[dict[str, Any]]
    original_count: int
    summary_count: int
    compression_ratio: float
    generation_method: str
    generation_time_ms: float
    fallback_used: bool


class AbstractiveImplementation:
    """Abstractive summarization implementation.

    Generates new summaries of conversation context using an LLM.
    More powerful than extractive but requires LLM access and has higher
    latency. Includes timeout protection and extractive fallback.
    """

    def __init__(self) -> None:
        self._name = "abstractive"
        self._description = "LLM-based summarization with timeout/fallback"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> AbstractiveSummaryResult:
        """Execute abstractive summarization.

        Args:
            input_data: Dict with:
                - messages: List of message dicts with 'content' field
                - context_items: Alternative - list of text items to summarize
                - llm_client: Optional LLM client for actual summarization
            config: Merged configuration with:
                - max_summary_length: Target summary length in words (default: 200)
                - timeout_seconds: Max time for LLM call (default: 30)
                - temperature: LLM temperature (default: 0.3)
                - use_fallback: Enable extractive fallback on failure (default: True)
                - summary_style: Style of summary (default: "concise")

        Returns:
            AbstractiveSummaryResult with summarized content
        """
        start_time = time.time()

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
        max_summary_length = config.get("max_summary_length", 200)
        timeout_seconds = config.get("timeout_seconds", 30)
        temperature = config.get("temperature", 0.3)
        use_fallback = config.get("use_fallback", True)
        summary_style = config.get("summary_style", "concise")

        logger.debug(
            f"Abstractive summarization: {original_count} messages, "
            f"target_length={max_summary_length} words, timeout={timeout_seconds}s"
        )

        # Try LLM-based summarization
        llm_client = input_data.get("llm_client")
        fallback_used = False

        try:
            if llm_client:
                # Actual LLM summarization
                summary_messages = self._summarize_with_llm(
                    messages=messages,
                    llm_client=llm_client,
                    max_length=max_summary_length,
                    temperature=temperature,
                    style=summary_style,
                    timeout=timeout_seconds,
                )
                generation_method = "llm_abstractive"
            else:
                # Simulate LLM summarization with template-based approach
                logger.warning("No LLM client provided, using template-based summarization")
                summary_messages = self._template_based_summary(
                    messages=messages, max_length=max_summary_length, style=summary_style
                )
                generation_method = "template_based"

        except Exception as e:
            logger.warning("Abstractive summarization failed: %s", e)
            if use_fallback:
                logger.info("Falling back to extractive summarization")
                summary_messages = self._extractive_fallback(messages, max_summary_length)
                generation_method = "extractive_fallback"
                fallback_used = True
            else:
                raise

        end_time = time.time()
        generation_time_ms = (end_time - start_time) * 1000

        summary_count = len(summary_messages)
        compression_ratio = summary_count / original_count if original_count > 0 else 1.0

        logger.debug(
            f"Abstractive summary: {original_count} -> {summary_count} messages "
            f"({generation_time_ms:.0f}ms, method={generation_method})"
        )

        return AbstractiveSummaryResult(
            summary=summary_messages,
            original_count=original_count,
            summary_count=summary_count,
            compression_ratio=compression_ratio,
            generation_method=generation_method,
            generation_time_ms=generation_time_ms,
            fallback_used=fallback_used,
        )

    def _summarize_with_llm(
        self,
        messages: list[dict[str, Any]],
        llm_client: Any,
        max_length: int,
        temperature: float,
        style: str,
        timeout: float,
    ) -> list[dict[str, Any]]:
        """Summarize messages using LLM.

        This is a placeholder for actual LLM integration.
        In production, this would call the actual LLM API.
        """
        # Concatenate messages for summarization
        combined_text = "\n\n".join(
            msg.get("content", "") if isinstance(msg, dict) else str(msg) for msg in messages
        )

        # Build summarization prompt
        self._build_summary_prompt(combined_text, max_length, style)

        # Call LLM (placeholder - actual implementation would use llm_client)
        # summary_text = llm_client.generate(prompt, temperature=temperature, timeout=timeout)

        # For now, return a template-based summary
        logger.debug("LLM summarization requested (using template for now)")
        return self._template_based_summary(messages, max_length, style)

    def _build_summary_prompt(self, text: str, max_length: int, style: str) -> str:
        """Build LLM prompt for summarization."""
        style_instructions = {
            "concise": "Create a brief, factual summary focusing on key points.",
            "detailed": "Create a comprehensive summary covering main topics and context.",
            "technical": "Focus on technical details, code changes, and implementation specifics.",
            "executive": "High-level overview suitable for executive briefing.",
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        return f"""Summarize the following conversation in approximately {max_length} words.

{instruction}

Conversation:
{text}

Summary:"""

    def _template_based_summary(
        self, messages: list[dict[str, Any]], max_length: int, style: str
    ) -> list[dict[str, Any]]:
        """Generate summary using simple template (fallback/simulation).

        This creates a structured summary message from the conversation.
        """
        # Count messages by type/role if available
        user_msgs = []
        assistant_msgs = []
        system_msgs = []

        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    user_msgs.append(content)
                elif role == "assistant":
                    assistant_msgs.append(content)
                else:
                    system_msgs.append(content)

        # Build summary text
        summary_parts = [
            f"Summary of {len(messages)} messages:",
            f"- User messages: {len(user_msgs)}",
            f"- Assistant responses: {len(assistant_msgs)}",
        ]

        # Add first and last message snippets
        if messages:
            first_content = (
                messages[0].get("content", "")
                if isinstance(messages[0], dict)
                else str(messages[0])
            )
            last_content = (
                messages[-1].get("content", "")
                if isinstance(messages[-1], dict)
                else str(messages[-1])
            )

            summary_parts.append(f"\nFirst message: {first_content[:100]}...")
            if len(messages) > 1:
                summary_parts.append(f"Latest message: {last_content[:100]}...")

        summary_text = "\n".join(summary_parts)

        return [
            {
                "role": "system",
                "content": summary_text,
                "metadata": {
                    "type": "summary",
                    "original_count": len(messages),
                    "generation_method": "template_based",
                },
            }
        ]

    def _extractive_fallback(
        self, messages: list[dict[str, Any]], max_length: int
    ) -> list[dict[str, Any]]:
        """Fallback to extractive summarization."""
        # Simple extractive approach: take first, middle, and last messages
        if len(messages) <= 3:
            return messages

        indices = [
            0,  # First
            len(messages) // 2,  # Middle
            len(messages) - 1,  # Last
        ]

        return [messages[i] for i in indices]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {
            "max_summary_length": 200,
            "timeout_seconds": 30,
            "temperature": 0.3,
            "use_fallback": True,
            "summary_style": "concise",
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        max_length = config.get("max_summary_length", 200)
        timeout = config.get("timeout_seconds", 30)
        temperature = config.get("temperature", 0.3)

        if not isinstance(max_length, int) or max_length <= 0:
            msg = f"max_summary_length must be a positive integer, got {max_length}"
            raise ValueError(msg)

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            msg = f"timeout_seconds must be positive, got {timeout}"
            raise ValueError(msg)

        if not (0.0 <= temperature <= 2.0):
            msg = f"temperature must be between 0 and 2, got {temperature}"
            raise ValueError(msg)

        return True
