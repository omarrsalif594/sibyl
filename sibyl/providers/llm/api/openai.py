"""OpenAI LLM client implementation."""

import contextlib
import logging
import os
import time
from typing import Any

from sibyl.core.contracts.providers import CompletionOptions, CompletionResult
from sibyl.core.infrastructure.llm.base_client import BaseLLMClient
from sibyl.core.infrastructure.llm.errors import (
    ProviderError,
    RateLimitError,
    TransientProviderError,
)

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gpt-4-turbo-preview",
        base_url: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (or from OPENAI_API_KEY env)
            default_model: Default model to use
            base_url: Optional custom API base URL
            **kwargs: Additional config
        """
        super().__init__("openai", **kwargs)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            msg = "OpenAI API key required (pass api_key or set OPENAI_API_KEY)"
            raise ValueError(msg)

        self.default_model = default_model
        self.base_url = base_url

        # Lazy-initialize client
        self._client = None

    def _get_client(self) -> Any:
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                msg = "openai SDK not installed. Install with: pip install openai"
                raise ImportError(msg) from None

        return self._client

    def _get_version(self) -> str:
        """Get OpenAI SDK version."""
        try:
            import openai

            return openai.__version__
        except (ImportError, AttributeError):
            return "unknown"

    async def _complete_impl(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """OpenAI-specific completion implementation.

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
        client = self._get_client()
        start_time = time.monotonic()

        try:
            # Build messages
            messages = []
            if options.system_prompt:
                messages.append({"role": "system", "content": options.system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call API
            response = await client.chat.completions.create(
                model=options.model,
                messages=messages,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p,
                timeout=options.timeout_ms / 1000.0,  # Convert to seconds
            )

            # Extract text
            text = ""
            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content or ""

            # Calculate latency
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Build result
            result: CompletionResult = {
                "text": text,
                "tokens_in": response.usage.prompt_tokens if response.usage else 0,
                "tokens_out": response.usage.completion_tokens if response.usage else 0,
                "latency_ms": latency_ms,
                "finish_reason": response.choices[0].finish_reason if response.choices else "stop",
                "provider_metadata": {
                    "model": response.model,
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                },
            }

            return result

        except Exception as e:
            # Handle OpenAI-specific errors
            error_type = type(e).__name__

            if "RateLimitError" in error_type or "429" in str(e):
                # Extract retry_after if available
                retry_after = None
                if hasattr(e, "response") and hasattr(e.response, "headers"):
                    retry_after_header = e.response.headers.get("retry-after")
                    if retry_after_header:
                        with contextlib.suppress(ValueError):
                            retry_after = int(retry_after_header)

                raise RateLimitError(str(e), retry_after=retry_after) from e

            if "APIError" in error_type and hasattr(e, "status_code"):
                status = e.status_code
                if 500 <= status < 600:
                    raise TransientProviderError(str(e), status_code=status) from e
                msg = f"OpenAI API error (status {status}): {e}"
                raise ProviderError(msg) from None

            # Generic error
            msg = f"OpenAI error: {e}"
            raise ProviderError(msg) from None

    async def _structured_complete_impl(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """OpenAI structured completion using JSON mode or response_format.

        Args:
            prompt: Input prompt
            schema: JSON schema
            options: Completion options

        Returns:
            CompletionResult with JSON text
        """
        client = self._get_client()
        start_time = time.monotonic()

        try:
            # Build messages
            messages = []
            if options.system_prompt:
                messages.append({"role": "system", "content": options.system_prompt})
            messages.append({"role": "user", "content": prompt})

            # OpenAI supports structured output via response_format
            # For GPT-4 and later models
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": schema,
                    "strict": True,
                },
            }

            # Call API with structured output
            response = await client.chat.completions.create(
                model=options.model,
                messages=messages,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p,
                response_format=response_format,
                timeout=options.timeout_ms / 1000.0,
            )

            # Extract JSON text
            text = ""
            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content or ""

            latency_ms = int((time.monotonic() - start_time) * 1000)

            result: CompletionResult = {
                "text": text,
                "tokens_in": response.usage.prompt_tokens if response.usage else 0,
                "tokens_out": response.usage.completion_tokens if response.usage else 0,
                "latency_ms": latency_ms,
                "finish_reason": response.choices[0].finish_reason if response.choices else "stop",
                "provider_metadata": {
                    "model": response.model,
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                },
            }

            return result

        except Exception as e:
            # Same error handling as _complete_impl
            error_type = type(e).__name__

            if "RateLimitError" in error_type or "429" in str(e):
                retry_after = None
                if hasattr(e, "response") and hasattr(e.response, "headers"):
                    retry_after_header = e.response.headers.get("retry-after")
                    if retry_after_header:
                        with contextlib.suppress(ValueError):
                            retry_after = int(retry_after_header)

                raise RateLimitError(str(e), retry_after=retry_after) from e

            if "APIError" in error_type and hasattr(e, "status_code"):
                status = e.status_code
                if 500 <= status < 600:
                    raise TransientProviderError(str(e), status_code=status) from e
                msg = f"OpenAI API error (status {status}): {e}"
                raise ProviderError(msg) from e

            msg = f"OpenAI error: {e}"
            raise ProviderError(msg) from None
