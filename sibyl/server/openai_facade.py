"""OpenAI-Compatible Facade for Sibyl Router.

This module provides an OpenAI-compatible HTTP API endpoint that exposes Sibyl's
LLM routing and compression capabilities through the standard OpenAI chat completions
interface.

Features:
- OpenAI-compatible POST /v1/chat/completions endpoint
- Model resolution: direct provider access or routed via profiles
- Compression integration when enabled in profiles
- Metadata conventions for workspace/pipeline configuration
- Debug mode with Sibyl-specific diagnostics

Model Resolution Strategy:
1. Direct provider: model="openai_gpt4o" -> bypass router, call provider directly
2. Profile routing: model="sibyl/<profile>" -> route via LLMRouter using profile
3. If profile has compression enabled, run compression chain before routing

Example usage:
    # Using OpenAI SDK
    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

    # Direct provider access
    response = client.chat.completions.create(
        model="openai_gpt4o",
        messages=[{"role": "user", "content": "Hello"}]
    )

    # Routed via profile
    response = client.chat.completions.create(
        model="sibyl/code-fast",
        messages=[{"role": "user", "content": "Hello"}]
    )

    # With metadata
    response = client.chat.completions.create(
        model="sibyl/code-fast",
        messages=[{"role": "user", "content": "Hello"}],
        extra_body={"sibyl": {"workspace": "dev", "pipeline": "code_assistant"}}
    )
"""

import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sibyl.core.contracts.providers import CompletionOptions, LLMProvider
from sibyl.techniques.infrastructure.llm.router import LLMRouter
from sibyl.techniques.infrastructure.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

# Create router for OpenAI-compatible endpoints
router = APIRouter(prefix="/v1", tags=["openai-compatible"])


# =============================================================================
# OpenAI-Compatible Request/Response Models
# =============================================================================


class ChatMessage(BaseModel):
    """OpenAI-compatible chat message."""

    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    name: str | None = Field(None, description="Optional participant name")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(..., description="Model ID or sibyl/<profile> for routing")
    messages: list[ChatMessage] = Field(..., description="Chat messages")
    temperature: float | None = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(4096, ge=1, description="Maximum tokens to generate")
    top_p: float | None = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    n: int | None = Field(1, description="Number of completions (only 1 supported)")
    stream: bool | None = Field(False, description="Stream responses (not yet supported)")
    stop: list[str] | None = Field(None, description="Stop sequences")
    presence_penalty: float | None = Field(0.0, description="Presence penalty (not used)")
    frequency_penalty: float | None = Field(0.0, description="Frequency penalty (not used)")
    logit_bias: dict[str, float] | None = Field(None, description="Logit bias (not used)")
    user: str | None = Field(None, description="End-user ID for tracking")

    # OpenAI tools/functions (for future extension)
    tools: list[dict[str, Any]] | None = Field(None, description="Tool definitions")
    tool_choice: Any | None = Field(None, description="Tool choice strategy")

    # Sibyl-specific extensions (via extra_body in OpenAI SDK)
    extra: dict[str, Any] | None = Field(
        None, description="Extra metadata: {sibyl: {workspace, pipeline, compression, debug}}"
    )


class ChatCompletionChoice(BaseModel):
    """OpenAI-compatible choice."""

    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Generated message")
    finish_reason: str = Field(..., description="Reason for completion: stop, length, error")


class ChatCompletionUsage(BaseModel):
    """OpenAI-compatible token usage."""

    prompt_tokens: int = Field(..., description="Tokens in prompt")
    completion_tokens: int = Field(..., description="Tokens in completion")
    total_tokens: int = Field(..., description="Total tokens used")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str = Field(..., description="Unique completion ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field(..., description="Model used")
    choices: list[ChatCompletionChoice] = Field(..., description="Generated choices")
    usage: ChatCompletionUsage = Field(..., description="Token usage statistics")

    # Sibyl-specific debug info (when debug=true)
    sibyl_debug: dict[str, Any] | None = Field(None, description="Sibyl routing debug info")


# =============================================================================
# Model Resolution Logic
# =============================================================================


class ModelResolver:
    """Resolve model names to provider/profile routing strategy.

    Resolution logic:
    1. If model matches pattern "<provider>_<model>" (e.g., "openai_gpt4o"), treat as direct provider
    2. If model matches pattern "sibyl/<profile>" (e.g., "sibyl/code-fast"), route via profile
    3. Otherwise, raise error for unknown format
    """

    @staticmethod
    def parse_model(model: str) -> dict[str, Any]:
        """Parse model string and return routing strategy.

        Args:
            model: Model string from request

        Returns:
            Dict with:
            - strategy: "direct" or "profile"
            - provider: Provider name (for direct)
            - model: Model name (for direct)
            - profile: Profile name (for profile routing)

        Raises:
            ValueError: If model format is invalid
        """
        # Check for sibyl/<profile> format
        if model.startswith("sibyl/"):
            profile_name = model[6:]  # Strip "sibyl/" prefix
            if not profile_name:
                msg = "Profile name cannot be empty in sibyl/<profile> format"
                raise ValueError(msg)
            return {"strategy": "profile", "profile": profile_name}

        # Check for <provider>_<model> format (direct provider)
        if "_" in model:
            parts = model.split("_", 1)
            provider = parts[0]
            model_name = parts[1]
            return {"strategy": "direct", "provider": provider, "model": model_name}

        # Unknown format
        msg = (
            f"Invalid model format: '{model}'. "
            "Use 'sibyl/<profile>' for routing or '<provider>_<model>' for direct access. "
            "Examples: 'sibyl/code-fast', 'openai_gpt4o', 'anthropic_claude-opus-4'"
        )
        raise ValueError(msg)


# =============================================================================
# Facade Implementation
# =============================================================================


class OpenAIFacade:
    """OpenAI-compatible facade for Sibyl routing.

    This class handles the translation between OpenAI's chat completion API
    and Sibyl's internal routing and compression infrastructure.
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        provider_registry: ProviderRegistry | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the facade.

        Args:
            llm_router: Optional LLMRouter instance (for profile routing)
            provider_registry: Optional ProviderRegistry (for direct provider access)
            config: Optional configuration dict (routing profiles, compression settings)
        """
        self.llm_router = llm_router
        self.provider_registry = provider_registry
        self.config = config or {}
        self.model_resolver = ModelResolver()

    def _convert_messages_to_prompt(self, messages: list[ChatMessage]) -> tuple[str, str | None]:
        """Convert OpenAI messages to prompt and optional system prompt.

        Args:
            messages: List of chat messages

        Returns:
            Tuple of (prompt, system_prompt)
        """
        system_prompt = None
        user_messages = []

        for msg in messages:
            if msg.role == "system":
                # Concatenate system messages
                if system_prompt:
                    system_prompt += "\n\n" + msg.content
                else:
                    system_prompt = msg.content
            elif msg.role == "user":
                user_messages.append(msg.content)
            elif msg.role == "assistant":
                # For simplicity, we'll append assistant messages to context
                # In a real implementation, you'd maintain conversation history
                user_messages.append(f"[Previous response: {msg.content}]")

        # Join all user messages
        prompt = "\n\n".join(user_messages)

        return prompt, system_prompt

    def _route_via_profile(
        self,
        profile: str,
        prompt: str,
        options: CompletionOptions,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route request via profile with optional compression.

        Args:
            profile: Profile name
            prompt: Input prompt
            options: Completion options
            metadata: Optional Sibyl metadata (workspace, pipeline, etc.)

        Returns:
            Completion result

        Raises:
            HTTPException: If routing fails or profile not found
        """
        if not self.llm_router:
            raise HTTPException(
                status_code=503,
                detail="LLMRouter not initialized. Profile routing is not available.",
            )

        # Get profile configuration
        profiles = self.config.get("routing", {}).get("profiles", {})
        profile_config = profiles.get(profile)

        if not profile_config:
            available_profiles = list(profiles.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Profile '{profile}' not found. Available profiles: {available_profiles}",
            )

        # Check if compression is enabled for this profile
        compression_enabled = profile_config.get("compression", {}).get("enabled", False)
        compressed_prompt = prompt
        compression_info = None

        if compression_enabled:
            # TODO: Integrate with compression chain
            # For now, we'll just log that compression would happen
            logger.info(
                "Profile '%s' has compression enabled (compression integration pending)", profile
            )
            compression_info = {
                "enabled": True,
                "original_length": len(prompt),
                "compressed_length": len(prompt),  # No actual compression yet
                "status": "pending_integration",
            }

        # Get provider and model from profile
        provider = profile_config.get("provider")
        model = profile_config.get("model")

        if not provider or not model:
            raise HTTPException(
                status_code=500,
                detail=f"Profile '{profile}' missing provider or model configuration",
            )

        # Route through LLMRouter
        try:
            # Note: LLMRouter.route() is async, so we need to handle this appropriately
            # For now, we'll use a synchronous wrapper (in practice, the endpoint should be async)
            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                self.llm_router.route(provider, model, compressed_prompt, options)
            )

            # Add compression info to result if applicable
            if compression_info:
                result["compression"] = compression_info

            return result

        except Exception as e:
            logger.exception("Routing failed for profile '%s': %s", profile, e)
            raise HTTPException(status_code=500, detail=f"Routing failed: {e!s}") from e

    def _route_direct(
        self, provider: str, model: str, prompt: str, options: CompletionOptions
    ) -> dict[str, Any]:
        """Route directly to provider, bypassing router.

        Args:
            provider: Provider name
            model: Model name
            prompt: Input prompt
            options: Completion options

        Returns:
            Completion result

        Raises:
            HTTPException: If provider not found or call fails
        """
        if not self.provider_registry:
            raise HTTPException(
                status_code=503,
                detail="ProviderRegistry not initialized. Direct provider access is not available.",
            )

        try:
            # Get provider instance
            llm_provider: LLMProvider = self.provider_registry.create_llm_provider_instance(
                provider
            )

            # Override model in options
            options.model = model

            # Make synchronous call
            # Note: In production, should use async version
            import asyncio

            return asyncio.get_event_loop().run_until_complete(
                llm_provider.complete_async(prompt, options)
            )

        except KeyError:
            raise HTTPException(
                status_code=404, detail=f"Provider '{provider}' not found in registry"
            )
        except Exception as e:
            logger.exception("Direct provider call failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Provider call failed: {e!s}") from e

    def complete(
        self, request: ChatCompletionRequest, debug: bool = False
    ) -> ChatCompletionResponse:
        """Handle chat completion request.

        Args:
            request: OpenAI-compatible chat completion request
            debug: Include Sibyl debug info in response

        Returns:
            OpenAI-compatible chat completion response

        Raises:
            HTTPException: For validation or routing errors
        """
        # Validate request
        if request.n and request.n > 1:
            raise HTTPException(status_code=400, detail="Multiple completions (n>1) not supported")

        if request.stream:
            raise HTTPException(status_code=400, detail="Streaming not yet supported")

        # Parse model to determine routing strategy
        try:
            routing = self.model_resolver.parse_model(request.model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Convert messages to prompt
        prompt, system_prompt = self._convert_messages_to_prompt(request.messages)

        if not prompt:
            raise HTTPException(status_code=400, detail="No user messages found in request")

        # Build completion options
        options = CompletionOptions(
            model=request.model,  # Will be overridden in direct mode
            temperature=request.temperature or 0.7,
            top_p=request.top_p or 1.0,
            max_tokens=request.max_tokens or 4096,
            system_prompt=system_prompt,
            tools=request.tools,
            correlation_id=request.user or str(uuid4()),
        )

        # Extract Sibyl metadata
        sibyl_metadata = request.extra.get("sibyl") if request.extra else None

        # Route based on strategy
        start_time = time.time()

        if routing["strategy"] == "profile":
            result = self._route_via_profile(routing["profile"], prompt, options, sibyl_metadata)
        else:  # direct
            result = self._route_direct(routing["provider"], routing["model"], prompt, options)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Build OpenAI-compatible response
        completion_id = f"chatcmpl-{uuid4().hex[:24]}"

        response = ChatCompletionResponse(
            id=completion_id,
            object="chat.completion",
            created=int(start_time),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=result["text"]),
                    finish_reason=result.get("finish_reason", "stop"),
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=result.get("tokens_in", 0),
                completion_tokens=result.get("tokens_out", 0),
                total_tokens=result.get("tokens_in", 0) + result.get("tokens_out", 0),
            ),
        )

        # Add debug info if requested
        if debug:
            response.sibyl_debug = {
                "routing": routing,
                "metadata": sibyl_metadata,
                "latency_ms": latency_ms,
                "provider_metadata": result.get("provider_metadata", {}),
                "fingerprint": str(result.get("fingerprint", "unknown")),
                "compression": result.get("compression"),
            }

        return response


# =============================================================================
# Global Facade Instance
# =============================================================================

# This will be initialized by the server on startup
_facade: OpenAIFacade | None = None


def init_facade(
    llm_router: LLMRouter | None = None,
    provider_registry: ProviderRegistry | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Initialize the global OpenAI facade instance.

    Args:
        llm_router: LLMRouter instance for profile routing
        provider_registry: ProviderRegistry for direct provider access
        config: Configuration dict with routing profiles
    """
    global _facade
    _facade = OpenAIFacade(llm_router, provider_registry, config)
    logger.info("OpenAI facade initialized")


def get_facade() -> OpenAIFacade:
    """Get the global facade instance.

    Returns:
        OpenAIFacade instance

    Raises:
        HTTPException: If facade not initialized
    """
    if _facade is None:
        raise HTTPException(
            status_code=503,
            detail="OpenAI facade not initialized. Server must be configured with routing.",
        )
    return _facade


# =============================================================================
# FastAPI Endpoints
# =============================================================================


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    debug: bool = Query(False, description="Include Sibyl debug info in response"),
) -> ChatCompletionResponse:
    """OpenAI-compatible chat completion endpoint.

    Supports two model formats:
    1. Direct provider: model="<provider>_<model>" (e.g., "openai_gpt4o")
       - Bypasses router and calls provider directly
    2. Profile routing: model="sibyl/<profile>" (e.g., "sibyl/code-fast")
       - Routes via LLMRouter using the specified profile
       - Applies compression if enabled in profile

    Example requests:
        # Direct provider access
        {
            "model": "openai_gpt4o",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        # Profile routing
        {
            "model": "sibyl/code-fast",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        # With Sibyl metadata
        {
            "model": "sibyl/code-fast",
            "messages": [{"role": "user", "content": "Hello"}],
            "extra": {"sibyl": {"workspace": "dev", "pipeline": "assistant"}}
        }

    Args:
        request: OpenAI-compatible chat completion request
        debug: Include Sibyl debug info in response

    Returns:
        OpenAI-compatible chat completion response

    Raises:
        HTTPException: 400 for invalid requests, 404 for unknown models/profiles,
                      503 if facade not initialized, 500 for execution errors
    """
    facade = get_facade()
    return facade.complete(request, debug=debug)
