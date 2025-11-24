"""MCP adapter for LLM providers.

This adapter enables communication with MCP servers that provide LLM services.
"""

import logging
import time
from collections.abc import Iterator
from typing import Any

from sibyl.core.contracts.providers import (
    CompletionOptions,
    CompletionResult,
    ProviderFeatures,
    ProviderFingerprint,
)
from sibyl.providers.mcp.base import BaseMCPAdapter, MCPRequestError, MCPTimeoutError
from sibyl.providers.mcp.utils import MCPClient

logger = logging.getLogger(__name__)


class MCPLLMAdapter(BaseMCPAdapter):
    """MCP adapter for LLM providers.

    This adapter implements the LLMProvider protocol to communicate with
    MCP servers providing LLM services.
    """

    def __init__(
        self,
        provider_name: str,
        endpoint: str,
        timeout_seconds: int = 30,
        **kwargs,
    ) -> None:
        """Initialize MCP LLM adapter.

        Args:
            provider_name: Provider identifier
            endpoint: MCP server endpoint URL
            timeout_seconds: Request timeout
            **kwargs: Additional configuration
        """
        super().__init__(provider_name, endpoint, timeout_seconds, **kwargs)
        self._client = MCPClient(endpoint, timeout_seconds)
        self._features = ProviderFeatures(
            supports_structured=True,  # Assume MCP servers support structured output
            supports_seed=False,
            supports_streaming=False,  # TODO: Implement streaming support
            supports_tools=True,
        )

    async def connect(self) -> None:
        """Establish connection to MCP server."""
        try:
            # Perform health check to verify connection
            await self.health_check()
            self._connected = True
            logger.info("Connected to MCP server: %s", self.endpoint)
        except Exception as e:
            logger.exception("Failed to connect to MCP server: %s", e)
            raise

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if self._client:
            await self._client.close()
        self._connected = False
        logger.info("Disconnected from MCP server: %s", self.endpoint)

    async def health_check(self) -> bool:
        """Check if MCP server is healthy.

        Returns:
            True if server is healthy

        Raises:
            MCPConnectionError: If health check fails
        """
        try:
            response = await self._client.request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.exception("MCP health check failed: %s", e)
            raise

    def get_features(self) -> ProviderFeatures:
        """Get provider capability flags.

        Returns:
            ProviderFeatures
        """
        return self._features

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        """Async completion with MCP server.

        Args:
            prompt: Input prompt
            options: Completion options

        Returns:
            CompletionResult

        Raises:
            MCPRequestError: If request fails
            MCPTimeoutError: If request times out
        """
        start_time = time.monotonic()

        # Build MCP request
        request_data = {
            "prompt": prompt,
            "model": options.model,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p,
        }

        if options.system_prompt:
            request_data["system"] = options.system_prompt

        try:
            # Make request to MCP server
            response = await self._client.request("POST", "/v1/completions", data=request_data)

            # Extract completion data
            text = response.get("text", "")
            tokens_in = response.get("usage", {}).get("prompt_tokens", 0)
            tokens_out = response.get("usage", {}).get("completion_tokens", 0)
            finish_reason = response.get("finish_reason", "stop")

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Build result
            result: CompletionResult = {
                "text": text,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "finish_reason": finish_reason,
                "provider_metadata": {
                    "mcp_endpoint": self.endpoint,
                    "model": options.model,
                },
                "fingerprint": ProviderFingerprint(
                    provider=self.provider_name,
                    model=options.model,
                    version="mcp",
                    revision=None,
                ),
            }

            return result

        except (MCPRequestError, MCPTimeoutError):
            raise
        except Exception as e:
            logger.exception("MCP completion failed: %s", e)
            msg = f"Completion failed: {e}"
            raise MCPRequestError(msg) from e

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

    async def structured_complete(
        self, prompt: str, schema: dict[str, Any], options: CompletionOptions
    ) -> CompletionResult:
        """Structured completion with JSON schema.

        Args:
            prompt: Input prompt
            schema: JSON schema
            options: Completion options

        Returns:
            CompletionResult with JSON text
        """
        start_time = time.monotonic()

        # Build MCP request with schema
        request_data = {
            "prompt": prompt,
            "model": options.model,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": schema,
                },
            },
        }

        if options.system_prompt:
            request_data["system"] = options.system_prompt

        try:
            # Make request to MCP server
            response = await self._client.request(
                "POST", "/v1/completions/structured", data=request_data
            )

            # Extract completion data
            text = response.get("text", "")
            tokens_in = response.get("usage", {}).get("prompt_tokens", 0)
            tokens_out = response.get("usage", {}).get("completion_tokens", 0)
            finish_reason = response.get("finish_reason", "stop")

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Build result
            result: CompletionResult = {
                "text": text,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "finish_reason": finish_reason,
                "provider_metadata": {
                    "mcp_endpoint": self.endpoint,
                    "model": options.model,
                },
                "fingerprint": ProviderFingerprint(
                    provider=self.provider_name,
                    model=options.model,
                    version="mcp",
                    revision=None,
                ),
            }

            return result

        except (MCPRequestError, MCPTimeoutError):
            raise
        except Exception as e:
            logger.exception("MCP structured completion failed: %s", e)
            msg = f"Structured completion failed: {e}"
            raise MCPRequestError(msg) from e

    def complete_stream(self, prompt: str, options: CompletionOptions) -> Iterator[dict[str, Any]]:
        """Streaming completion (not yet implemented).

        Args:
            prompt: Input prompt
            options: Completion options

        Yields:
            Partial completion results

        Raises:
            NotImplementedError: Streaming not yet supported
        """
        msg = "Streaming not yet supported for MCP adapters"
        raise NotImplementedError(msg)

    def count_tokens(self, text: str, model: str) -> int:
        """Count tokens (estimate).

        Args:
            text: Text to count
            model: Model name

        Returns:
            Estimated token count with safety margin
        """
        # Simple estimation: ~4 characters per token
        char_count = len(text)
        estimated_tokens = char_count // 4

        # Add 10% safety margin
        return int(estimated_tokens * 1.1)
