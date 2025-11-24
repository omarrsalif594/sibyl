"""Token counting with safety margin for preflight estimation."""

import logging

from sibyl.techniques.infrastructure.llm.feature_flags import get_features

logger = logging.getLogger(__name__)


class TokenCounter:
    """Provider-specific token counting with safety margin."""

    SAFETY_MARGIN = 1.10  # 10% buffer for estimation error

    @staticmethod
    def count(text: str, model: str, provider: str) -> int:
        """Count tokens with safety margin.

        Args:
            text: Text to count
            model: Model name for tokenizer selection
            provider: Provider name ("anthropic", "openai", etc.)

        Returns:
            Estimated token count (includes 10% safety margin)

        Raises:
            ImportError: If required tokenizer library not installed
        """
        try:
            features = get_features(provider)
        except KeyError:
            logger.warning("Unknown provider %s, using rough estimate", provider)
            return TokenCounter._rough_estimate(text)

        method = features.token_counting_method

        if method == "tiktoken":
            raw_count = TokenCounter._count_tiktoken(text, model)
        elif method == "claude-tokenizer":
            raw_count = TokenCounter._count_anthropic(text)
        elif method == "estimate":
            raw_count = TokenCounter._rough_estimate(text)
        else:
            logger.warning("Unknown token counting method: %s", method)
            raw_count = TokenCounter._rough_estimate(text)

        # Apply safety margin
        with_margin = int(raw_count * TokenCounter.SAFETY_MARGIN)

        logger.debug(
            "Token count for %s/%s: %s → %s (with margin)", provider, model, raw_count, with_margin
        )

        return with_margin

    @staticmethod
    def _count_tiktoken(text: str, model: str) -> int:
        """Count tokens using tiktoken (OpenAI)."""
        try:
            import tiktoken

            try:
                enc = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base for unknown models
                logger.warning("Model %s not found in tiktoken, using cl100k_base", model)
                enc = tiktoken.get_encoding("cl100k_base")

            return len(enc.encode(text))

        except ImportError:
            logger.exception("tiktoken not installed, falling back to rough estimate")
            return TokenCounter._rough_estimate(text)

    @staticmethod
    def _count_anthropic(text: str) -> int:
        """Count tokens using Anthropic's tokenizer."""
        try:
            from anthropic import Anthropic

            client = Anthropic()  # Uses ANTHROPIC_API_KEY from env
            return client.count_tokens(text)

        except ImportError:
            logger.exception("anthropic SDK not installed, falling back to rough estimate")
            return TokenCounter._rough_estimate(text)
        except Exception as e:
            logger.exception("Error counting tokens with Anthropic: %s", e)
            return TokenCounter._rough_estimate(text)

    @staticmethod
    def _rough_estimate(text: str) -> int:
        """Rough token estimate: ~4 characters per token.

        This is a conservative estimate that works reasonably well for English text.
        For non-English or code-heavy text, this may underestimate.
        """
        return len(text) // 4


# Convenience functions
def count_tokens(text: str, model: str, provider: str) -> int:
    """Count tokens with safety margin (convenience function)."""
    return TokenCounter.count(text, model, provider)


def count_messages_tokens(messages: list[dict[str, str]], model: str, provider: str) -> int:
    """Count tokens for a list of messages.

    Args:
        messages: List of {"role": "user", "content": "..."} dicts
        model: Model name
        provider: Provider name

    Returns:
        Total token count with safety margin
    """
    # Concatenate all message content
    full_text = "\n".join(msg.get("content", "") for msg in messages)

    # Add overhead for message formatting (~4 tokens per message)
    message_overhead = len(messages) * 4

    content_tokens = TokenCounter.count(full_text, model, provider)

    return content_tokens + message_overhead
