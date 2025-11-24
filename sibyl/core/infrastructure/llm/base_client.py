"""Base LLM client with common functionality."""

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from sibyl.core.protocols.infrastructure.llm import (
    CompletionOptions,
    CompletionResult,
    ProviderFeatures,
    ProviderFingerprint,
)

from .errors import CapabilityError


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, provider_name: str, **kwargs) -> None:
        """Initialize base client.

        Args:
            provider_name: Provider identifier ("anthropic", "openai", etc.)
            **kwargs: Provider-specific config (api_key, base_url, etc.)
        """
        self.provider_name = provider_name
        self.config = kwargs
        # Lazy import to avoid circular dependency
        from sibyl.techniques.infrastructure.llm.feature_flags import get_features

        self._features = get_features(provider_name)

    def get_features(self) -> ProviderFeatures:
        """Get provider capability flags.

        Returns:
            ProviderFeatures describing what this provider supports
        """
        return self._features

    @abstractmethod
    def _get_version(self) -> str:
        """Get provider SDK/API version.

        Returns:
            Version string
        """

    @abstractmethod
    async def _complete_impl(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Provider-specific completion implementation.

        Args:
            prompt: Input prompt
            options: Completion options

        Returns:
            CompletionResult

        Raises:
            RateLimitError: On 429
            TransientProviderError: On 5xx
            ProviderError: On other errors
        """

    @abstractmethod
    async def _structured_complete_impl(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Provider-specific structured completion.

        Args:
            prompt: Input prompt
            schema: JSON schema
            options: Completion options

        Returns:
            CompletionResult with JSON text

        Raises:
            Same as _complete_impl
        """

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Synchronous completion (wrapper for async).

        Args:
            prompt: Input prompt
            options: Completion options

        Returns:
            CompletionResult
        """
        import asyncio

        return asyncio.run(self.complete_async(prompt, options))

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Async completion with provider fingerprint.

        Args:
            prompt: Input prompt
            options: Completion options

        Returns:
            CompletionResult with fingerprint attached
        """
        start_time = time.monotonic()

        # Call provider implementation
        result = await self._complete_impl(prompt, options)

        # Add provider fingerprint
        fingerprint = ProviderFingerprint(
            provider=self.provider_name,
            model=options.model,
            version=self._get_version(),
            revision=result.get("provider_metadata", {}).get("model_revision"),
        )

        result["fingerprint"] = fingerprint

        # Ensure latency_ms is set
        if "latency_ms" not in result:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            result["latency_ms"] = elapsed_ms

        return result

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Structured completion with JSON repair.

        Args:
            prompt: Input prompt
            schema: JSON schema for validation
            options: Completion options

        Returns:
            CompletionResult with valid JSON text

        Raises:
            CapabilityError: If provider doesn't support structured output
        """
        # Check capability
        if not self._features.supports_structured:
            # Fallback: try plain completion + JSON repair
            return await self._fallback_structured(prompt, schema, options)

        # Call provider-specific implementation
        result = await self._structured_complete_impl(prompt, schema, options)

        # Validate and repair if needed
        # Lazy import to avoid circular dependency
        from sibyl.techniques.infrastructure.llm.json_repair import JSONRepair

        repaired_json = await JSONRepair.validate_and_repair(
            result["text"], schema, self, prompt, options
        )

        # Update result with repaired JSON
        result["text"] = str(repaired_json)

        return result

    async def _fallback_structured(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Fallback for providers without structured output support.

        Args:
            prompt: Input prompt
            schema: JSON schema
            options: Completion options

        Returns:
            CompletionResult with JSON text (best effort)
        """
        # Add JSON schema to prompt
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
```json
{schema!s}
```

Output ONLY the JSON, no markdown code blocks or explanations."""

        result = await self.complete_async(enhanced_prompt, options)

        # Try to repair JSON
        # Lazy import to avoid circular dependency
        from sibyl.techniques.infrastructure.llm.json_repair import JSONRepair

        repaired_json = await JSONRepair.validate_and_repair(
            result["text"], schema, self, prompt, options
        )

        result["text"] = str(repaired_json)

        return result

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """Streaming completion.

        Args:
            prompt: Input prompt
            options: Completion options

        Yields:
            Partial completion results

        Raises:
            CapabilityError: If provider doesn't support streaming
        """
        if not self._features.supports_streaming:
            msg = f"Provider {self.provider_name} doesn't support streaming"
            raise CapabilityError(msg)

        # Override in subclass if streaming supported
        msg = "Streaming not implemented for this provider"
        raise NotImplementedError(msg)

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens with safety margin.

        Args:
            text: Text to count
            model: Model name

        Returns:
            Token count with 10% safety margin
        """
        # Lazy import to avoid circular dependency
        from sibyl.techniques.infrastructure.token_management.subtechniques.counting.default.token_counter import (
            TokenCounter,
        )

        return TokenCounter.count(text, model, self.provider_name)
