"""Local LLM provider for testing and deterministic behavior.

This provider implements the LLMProvider protocol with deterministic,
network-free behavior suitable for testing and development.
"""

import hashlib
import logging
import time
from collections.abc import Iterator
from typing import Any

from sibyl.core.protocols.infrastructure.llm import (
    CompletionOptions,
    CompletionResult,
    ProviderFeatures,
    ProviderFingerprint,
)

logger = logging.getLogger(__name__)


class LocalLLMProvider:
    """Local deterministic LLM provider for testing.

    This provider implements simple deterministic responses without
    requiring network calls or real LLM APIs. It's suitable for:
    - Testing and development
    - CI/CD pipelines
    - Deterministic behavior verification

    Behavior:
    - Generates responses based on prompt hash
    - Deterministic output for same inputs
    - Configurable response patterns
    """

    def __init__(
        self, model: str = "local-deterministic", response_mode: str = "echo", **kwargs
    ) -> None:
        """Initialize local LLM provider.

        Args:
            model: Model identifier (for logging/tracking)
            response_mode: Response generation mode:
                - "echo": Echo back the prompt with prefix
                - "hash": Generate response from prompt hash
                - "simple": Simple rule-based responses
            **kwargs: Additional configuration (ignored)
        """
        self.model = model
        self.response_mode = response_mode
        self.kwargs = kwargs
        logger.info("Initialized LocalLLMProvider: mode=%s, model=%s", response_mode, model)

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Synchronous completion.

        Args:
            prompt: Input prompt text
            options: Completion options

        Returns:
            CompletionResult with deterministic text
        """
        start_time = time.time()

        # Generate response based on mode
        if self.response_mode == "echo":
            response_text = f"[LocalLLM Echo] {prompt[:200]}"
        elif self.response_mode == "hash":
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            response_text = f"Response for prompt hash {prompt_hash}: This is a deterministic response based on the prompt content."
        elif self.response_mode == "simple":
            response_text = self._simple_response(prompt)
        else:
            response_text = f"[LocalLLM] Processed prompt of {len(prompt)} characters"

        # Calculate tokens (rough approximation: 4 chars per token)
        tokens_in = len(prompt) // 4
        tokens_out = len(response_text) // 4

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        return CompletionResult(
            text=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            finish_reason="stop",
            provider_metadata={
                "mode": self.response_mode,
                "model": self.model,
            },
            fingerprint=ProviderFingerprint(
                provider="local",
                model=self.model,
                version="1.0.0",
                revision=self.response_mode,
            ),
        )

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Async completion.

        Args:
            prompt: Input prompt text
            options: Completion options

        Returns:
            CompletionResult
        """
        # For local provider, just call sync version
        return self.complete(prompt, options)

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Structured completion (JSON mode).

        Args:
            prompt: Input prompt
            schema: JSON schema for output validation
            options: Completion options

        Returns:
            CompletionResult with JSON text
        """
        # Generate a simple JSON response based on schema
        start_time = time.time()

        # Extract required fields from schema
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        # Build minimal valid JSON
        json_obj = {}
        for field in required_fields:
            field_schema = properties.get(field, {})
            field_type = field_schema.get("type", "string")

            if field_type == "string":
                json_obj[field] = f"value_for_{field}"
            elif field_type in {"number", "integer"}:
                json_obj[field] = 42
            elif field_type == "boolean":
                json_obj[field] = True
            elif field_type == "array":
                json_obj[field] = []
            elif field_type == "object":
                json_obj[field] = {}

        # Convert to JSON string
        import json  # can be moved to top

        response_text = json.dumps(json_obj, indent=2)

        # Calculate tokens
        tokens_in = len(prompt) // 4
        tokens_out = len(response_text) // 4
        latency_ms = int((time.time() - start_time) * 1000)

        return CompletionResult(
            text=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            finish_reason="stop",
            provider_metadata={
                "mode": "structured",
                "schema": schema,
            },
            fingerprint=ProviderFingerprint(
                provider="local",
                model=self.model,
                version="1.0.0",
                revision="structured",
            ),
        )

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """Streaming completion.

        Args:
            prompt: Input prompt
            options: Completion options

        Yields:
            Partial completion results (text deltas)
        """
        # Generate full response
        result = self.complete(prompt, options)
        response_text = result["text"]

        # Split into chunks and yield
        chunk_size = 10
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i : i + chunk_size]
            yield {
                "delta": chunk,
                "done": i + chunk_size >= len(response_text),
            }

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for preflight estimation.

        Args:
            text: Text to count
            model: Model name (ignored for local provider)

        Returns:
            Estimated token count with 10% safety margin
        """
        # Simple approximation: ~4 chars per token + 10% safety margin
        base_count = len(text) // 4
        return int(base_count * 1.1)

    def get_features(self) -> ProviderFeatures:
        """Get provider capability flags.

        Returns:
            ProviderFeatures describing what this provider supports
        """
        return ProviderFeatures(
            supports_structured=True,
            supports_seed=True,  # Deterministic by nature
            supports_streaming=True,
            supports_tools=False,  # Not implemented yet
            max_tokens_limit=4096,
            token_counting_method="estimate",  # S106 false positive: not a password
        )

    def _simple_response(self, prompt: str) -> str:
        """Generate simple rule-based response.

        Args:
            prompt: Input prompt

        Returns:
            Simple response text
        """
        prompt_lower = prompt.lower()

        if "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! How can I help you today?"
        if "?" in prompt:
            return "That's an interesting question. Let me think about it."
        if "error" in prompt_lower or "bug" in prompt_lower:
            return "I understand you're experiencing an issue. Let's troubleshoot this together."
        if "thank" in prompt_lower:
            return "You're welcome! Is there anything else I can help with?"
        return f"I've processed your input of {len(prompt)} characters. How can I assist further?"
