"""Anthropic (Claude) LLM client implementation."""

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


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-sonnet-4-5-20250929",
        **kwargs,
    ) -> None:
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env)
            default_model: Default model to use
            **kwargs: Additional config
        """
        super().__init__("anthropic", **kwargs)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            msg = "Anthropic API key required (pass api_key or set ANTHROPIC_API_KEY)"
            raise ValueError(msg)

        self.default_model = default_model

        # Lazy-initialize client
        self._client = None

    def _get_client(self) -> Any:
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic  # optional dependency

                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                msg = "anthropic SDK not installed. Install with: pip install anthropic"
                raise ImportError(msg) from None

        return self._client

    def _get_version(self) -> str:
        """Get Anthropic SDK version."""
        try:
            import anthropic

            return anthropic.__version__
        except (ImportError, AttributeError):
            return "unknown"

    async def _complete_impl(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Anthropic-specific completion implementation.

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
            messages = [{"role": "user", "content": prompt}]

            # Add system prompt if provided
            system_prompt = options.system_prompt

            # Call API
            response = await client.messages.create(
                model=options.model,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p,
                messages=messages,
                system=system_prompt if system_prompt else None,
                timeout=options.timeout_ms / 1000.0,  # Convert to seconds
            )

            # Extract text
            text = ""
            if response.content:
                # Claude returns list of content blocks
                text = "".join(block.text for block in response.content if hasattr(block, "text"))

            # Calculate latency
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Extract rate limit headers (if available)
            rate_limit_headers = {}
            if hasattr(response, "headers"):
                headers = response.headers
                if "x-ratelimit-requests-remaining" in headers:
                    rate_limit_headers["remaining_requests"] = int(
                        headers["x-ratelimit-requests-remaining"]
                    )
                if "x-ratelimit-tokens-remaining" in headers:
                    rate_limit_headers["remaining_tokens"] = int(
                        headers["x-ratelimit-tokens-remaining"]
                    )

            # Build result
            result: CompletionResult = {
                "text": text,
                "tokens_in": response.usage.input_tokens,
                "tokens_out": response.usage.output_tokens,
                "latency_ms": latency_ms,
                "finish_reason": response.stop_reason or "stop",
                "provider_metadata": {
                    "model": response.model,
                    "rate_limit_headers": rate_limit_headers,
                },
            }

            return result

        except Exception as e:
            # Handle Anthropic-specific errors
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
                msg = f"Anthropic API error (status {status}): {e}"
                raise ProviderError(msg) from None

            # Generic error
            msg = f"Anthropic error: {e}"
            raise ProviderError(msg) from None

    async def _structured_complete_impl(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Anthropic structured completion using tools.

        Claude doesn't have native JSON mode, but we can use tools to enforce schema.

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
            # Convert JSON schema to Claude tool format
            tool = {
                "name": "respond_with_json",
                "description": "Respond with structured JSON matching the schema",
                "input_schema": schema,
            }

            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Call API with tools
            response = await client.messages.create(
                model=options.model,
                max_tokens=options.max_tokens,
                temperature=options.temperature,
                top_p=options.top_p,
                messages=messages,
                system=options.system_prompt,
                tools=[tool],
                tool_choice={"type": "tool", "name": "respond_with_json"},
                timeout=options.timeout_ms / 1000.0,
            )

            # Extract tool use
            tool_use = None
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    tool_use = block
                    break

            if not tool_use:
                msg = "No tool use in Claude response"
                raise ProviderError(msg)

            # Tool input is the structured JSON
            import json  # can be moved to top

            text = json.dumps(tool_use.input)

            latency_ms = int((time.monotonic() - start_time) * 1000)

            result: CompletionResult = {
                "text": text,
                "tokens_in": response.usage.input_tokens,
                "tokens_out": response.usage.output_tokens,
                "latency_ms": latency_ms,
                "finish_reason": response.stop_reason or "stop",
                "provider_metadata": {
                    "model": response.model,
                    "tool_use_id": tool_use.id,
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
                msg = f"Anthropic API error (status {status}): {e}"
                raise ProviderError(msg) from e

            msg = f"Anthropic error: {e}"
            raise ProviderError(msg) from None
