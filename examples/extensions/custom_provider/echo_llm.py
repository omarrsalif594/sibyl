"""
Echo LLM Provider - A simple custom provider for testing.

This provider echoes back the prompt with a configurable prefix.
Useful for testing pipelines without external API calls or costs.
"""

from collections.abc import Iterator
from typing import Any

from sibyl.core.protocols.infrastructure.llm import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    ProviderFeatures,
    ProviderFingerprint,
)


class EchoLLMProvider:
    """
    Echo LLM provider for testing and development.

    This provider simply echoes back the prompt with a configurable prefix.
    It simulates token usage and latency for realistic testing.

    Features:
    - Synchronous and async completion
    - Streaming support
    - Token counting
    - No external API required

    Example:
        >>> provider = EchoLLMProvider(model="echo-1", prefix="[ECHO] ")
        >>> options = CompletionOptions(model="echo-1", temperature=0.0)
        >>> result = provider.complete("Hello", options)
        >>> print(result["text"])
        [ECHO] Hello
    """

    def __init__(
        self,
        model: str = "echo-1",
        prefix: str = "[ECHO] ",
        simulate_latency_ms: int = 10,
    ) -> None:
        """
        Initialize Echo LLM provider.

        Args:
            model: Model identifier (e.g., "echo-1")
            prefix: Prefix to add to echoed text
            simulate_latency_ms: Simulated API latency in milliseconds
        """
        self.model = model
        self.prefix = prefix
        self.simulate_latency_ms = simulate_latency_ms

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """
        Echo the prompt back with prefix.

        Args:
            prompt: Input prompt text
            options: Completion options (mostly ignored for echo)

        Returns:
            CompletionResult with echoed text
        """
        import time  # noqa: PLC0415

        start_time = time.time()

        # Simulate API latency
        if self.simulate_latency_ms > 0:
            time.sleep(self.simulate_latency_ms / 1000.0)

        # Echo prompt with prefix
        response_text = f"{self.prefix}{prompt}"

        # Calculate token counts (simple word-based estimation)
        tokens_in = len(prompt.split())
        tokens_out = len(response_text.split())

        latency_ms = int((time.time() - start_time) * 1000)

        return CompletionResult(
            text=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            finish_reason="stop",
            provider_metadata={
                "model": self.model,
                "prefix": self.prefix,
                "simulated": True,
            },
            fingerprint=ProviderFingerprint(provider="echo", model=self.model, version="1.0.0"),
        )

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """
        Async version of complete.

        Args:
            prompt: Input prompt text
            options: Completion options

        Returns:
            CompletionResult with echoed text
        """
        import asyncio  # noqa: PLC0415

        # Simulate async API call
        if self.simulate_latency_ms > 0:
            await asyncio.sleep(self.simulate_latency_ms / 1000.0)

        # Reuse sync implementation
        return self.complete(prompt, options)

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """
        Structured completion (not supported by echo provider).

        Args:
            prompt: Input prompt
            schema: JSON schema
            options: Completion options

        Raises:
            NotImplementedError: Echo provider doesn't support structured output
        """
        msg = (
            "EchoLLMProvider does not support structured completion. "
            "This is a simple echo provider for testing."
        )
        raise NotImplementedError(msg)

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """
        Stream response word by word.

        Args:
            prompt: Input prompt
            options: Completion options

        Yields:
            Chunks with delta text and is_final flag
        """
        import time  # noqa: PLC0415

        response_text = f"{self.prefix}{prompt}"
        words = response_text.split()

        for i, word in enumerate(words):
            # Simulate streaming delay
            if self.simulate_latency_ms > 0:
                time.sleep(self.simulate_latency_ms / 1000.0 / len(words))

            yield {"delta": word + " ", "is_final": i == len(words) - 1}

    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens using simple word-based estimation.

        Args:
            text: Text to count
            model: Model name (ignored)

        Returns:
            Estimated token count (words / 0.75)
        """
        # Rough approximation: 1 token ≈ 0.75 words
        # Add 10% safety margin
        return int(len(text.split()) / 0.75 * 1.1)

    def get_features(self) -> ProviderFeatures:
        """
        Get provider capability flags.

        Returns:
            ProviderFeatures describing echo provider capabilities
        """
        return ProviderFeatures(
            supports_structured=False,
            supports_seed=False,
            supports_streaming=True,
            supports_tools=False,
            max_tokens_limit=100000,  # No real limit for echo
            token_counting_method="estimate",  # S106 false positive: not a password
        )


class TransformLLMProvider:
    """
    Transform LLM provider - Applies transformations to prompts.

    This provider demonstrates a more complex custom provider that
    performs text transformations (uppercase, lowercase, reverse, etc.)
    instead of calling an actual LLM.
    """

    def __init__(self, model: str = "transform-1", transform: str = "uppercase") -> None:
        """
        Initialize Transform LLM provider.

        Args:
            model: Model identifier
            transform: Transformation to apply ("uppercase", "lowercase", "reverse", "title")
        """
        self.model = model
        self.transform = transform

        self.transforms = {
            "uppercase": str.upper,
            "lowercase": str.lower,
            "reverse": lambda x: x[::-1],
            "title": str.title,
            "capitalize": str.capitalize,
        }

        if transform not in self.transforms:
            msg = f"Unknown transform: {transform}. Available: {list(self.transforms.keys())}"
            raise ValueError(msg)

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Apply transformation to prompt"""
        import time  # noqa: PLC0415

        start_time = time.time()

        # Apply transformation
        transform_func = self.transforms[self.transform]
        response_text = transform_func(prompt)

        latency_ms = int((time.time() - start_time) * 1000)

        return CompletionResult(
            text=response_text,
            tokens_in=len(prompt.split()),
            tokens_out=len(response_text.split()),
            latency_ms=latency_ms,
            finish_reason="stop",
            provider_metadata={
                "model": self.model,
                "transform": self.transform,
                "simulated": True,
            },
            fingerprint=ProviderFingerprint(
                provider="transform", model=self.model, version="1.0.0"
            ),
        )

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Async transformation"""
        return self.complete(prompt, options)

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Not supported"""
        msg = "TransformLLMProvider does not support structured output"
        raise NotImplementedError(msg)

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """Stream transformation result"""
        result = self.complete(prompt, options)
        yield {"delta": result["text"], "is_final": True}

    def count_tokens(self, text: str, model: str) -> int:
        """Simple token counting"""
        return len(text.split())

    def get_features(self) -> ProviderFeatures:
        """Get capabilities"""
        return ProviderFeatures(
            supports_structured=False,
            supports_seed=False,
            supports_streaming=True,
            supports_tools=False,
            max_tokens_limit=100000,
            token_counting_method="estimate",  # S106 false positive: not a password
        )


# Factory function for creating providers
def create_echo_provider(config: dict) -> LLMProvider:
    """
    Factory function to create Echo provider from config.

    Args:
        config: Configuration dict with:
               - model (str): Model name
               - prefix (str): Echo prefix
               - simulate_latency_ms (int): Simulated latency

    Returns:
        EchoLLMProvider instance

    Example:
        >>> config = {"model": "echo-1", "prefix": "[TEST] "}
        >>> provider = create_echo_provider(config)
    """
    return EchoLLMProvider(
        model=config.get("model", "echo-1"),
        prefix=config.get("prefix", "[ECHO] "),
        simulate_latency_ms=config.get("simulate_latency_ms", 10),
    )


def create_transform_provider(config: dict) -> LLMProvider:
    """
    Factory function to create Transform provider from config.

    Args:
        config: Configuration dict with:
               - model (str): Model name
               - transform (str): Transformation type

    Returns:
        TransformLLMProvider instance
    """
    return TransformLLMProvider(
        model=config.get("model", "transform-1"),
        transform=config.get("transform", "uppercase"),
    )
