"""
LLM Provider protocol interfaces for dependency inversion.

These protocols define the contracts that LLM infrastructure implementations must satisfy.
Application services depend only on these interfaces, not concrete implementations.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol, TypedDict, runtime_checkable
from uuid import uuid4


@dataclass
class ProviderFingerprint:
    """Provider identity for deterministic replay."""

    provider: str  # "anthropic", "openai", "ollama", "litellm"
    model: str  # "claude-sonnet-4-5-20250929", "gpt-4-turbo"
    version: str  # SDK or API version
    revision: str | None = None  # Model revision if available

    def __str__(self) -> str:
        """String representation for logging."""
        parts = [self.provider, self.model, self.version]
        if self.revision:
            parts.append(self.revision)
        return ":".join(parts)


class CompletionResult(TypedDict, total=False):
    """Normalized LLM completion result across all providers."""

    text: str  # Generated text
    tokens_in: int  # Input tokens consumed
    tokens_out: int  # Output tokens generated
    latency_ms: int  # Provider latency in milliseconds
    finish_reason: str  # "stop", "length", "error", "content_filter"
    provider_metadata: dict[str, Any]  # Provider-specific metadata (headers, etc.)
    fingerprint: ProviderFingerprint  # Provider identity


@dataclass
class CompletionOptions:
    """Options for LLM completion requests."""

    model: str
    temperature: float = 0.0  # Default deterministic
    top_p: float = 1.0
    max_tokens: int = 4096
    seed: int | None = None  # For reproducibility (if provider supports)
    timeout_ms: int = 30000  # 30 second default timeout
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    tools: list[dict] | None = None  # For function calling
    system_prompt: str | None = None  # System prompt


@dataclass
class ProviderFeatures:
    """Feature flags for provider capabilities."""

    supports_structured: bool  # JSON mode / tools
    supports_seed: bool  # Reproducibility via seed parameter
    supports_streaming: bool  # Server-sent events streaming
    supports_tools: bool  # Function calling / tools
    max_tokens_limit: int  # Hard limit for this provider
    token_counting_method: str  # "tiktoken" | "claude-tokenizer" | "estimate"


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for LLM completions."""

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Synchronous completion.

        Args:
            prompt: Input prompt text
            options: Completion options (model, temperature, etc.)

        Returns:
            CompletionResult with text, tokens, latency, etc.

        Raises:
            RateLimitError: Provider rate limit hit (429)
            TransientProviderError: Temporary provider error (5xx)
            ProviderError: Permanent provider error (4xx)
            TimeoutError: Request timeout exceeded
        """
        ...

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Async completion.

        Args:
            prompt: Input prompt text
            options: Completion options

        Returns:
            CompletionResult

        Raises:
            Same as complete()
        """
        ...

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Structured completion (JSON mode / tools).

        Args:
            prompt: Input prompt
            schema: JSON schema for output validation
            options: Completion options

        Returns:
            CompletionResult with text containing valid JSON

        Raises:
            Same as complete()
            CapabilityError: If provider doesn't support structured output
        """
        ...

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """Streaming completion.

        Args:
            prompt: Input prompt
            options: Completion options

        Yields:
            Partial completion results (text deltas)

        Raises:
            Same as complete()
            CapabilityError: If provider doesn't support streaming
        """
        ...

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for preflight estimation.

        Args:
            text: Text to count
            model: Model name for tokenizer selection

        Returns:
            Estimated token count (includes 10% safety margin)
        """
        ...

    def get_features(self) -> ProviderFeatures:
        """Get provider capability flags.

        Returns:
            ProviderFeatures describing what this provider supports
        """
        ...
