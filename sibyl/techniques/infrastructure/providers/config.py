"""Provider configuration models for hyper-modular architecture.

This module defines the configuration structure for providers in the Sibyl framework.
Providers can be configured at multiple levels with a clear cascade mechanism:
- Global level: Default provider settings
- Technique level: Provider settings for specific techniques (e.g., embedding, chunking)
- Subtechnique level: Provider settings for specific subtechniques

Configuration example:
    providers:
      llm:
        anthropic:
          type: api
          connection:
            api_key_env: ANTHROPIC_API_KEY
          capabilities:
            supports_structured: true
            supports_tools: true
          rate_limits:
            requests_per_minute: 50
          models:
            - name: claude-opus-4
              cost_per_1k_input: 0.015
              cost_per_1k_output: 0.075
              max_tokens: 200000
              quality_score: 10
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionConfig:
    """Connection configuration for a provider.

    Attributes:
        api_key_env: Environment variable name for API key
        endpoint: Optional custom endpoint URL
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum number of retry attempts
    """

    api_key_env: str | None = None
    endpoint: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate connection configuration."""
        if self.timeout_seconds <= 0:
            msg = f"timeout_seconds must be > 0, got {self.timeout_seconds}"
            raise ValueError(msg)
        if self.max_retries < 0:
            msg = f"max_retries must be >= 0, got {self.max_retries}"
            raise ValueError(msg)


@dataclass(frozen=True)
class CapabilitiesConfig:
    """Provider capabilities configuration.

    Attributes:
        supports_structured: Whether provider supports structured output (JSON mode)
        supports_seed: Whether provider supports reproducibility via seed
        supports_streaming: Whether provider supports streaming responses
        supports_tools: Whether provider supports tool/function calling
        max_tokens_limit: Maximum context window size
        embedding_dim: Embedding dimension (for embedding providers)
        token_counting_method: Method for counting tokens ("tiktoken", "claude-tokenizer", "estimate")
    """

    supports_structured: bool = False
    supports_seed: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    max_tokens_limit: int = 4096
    embedding_dim: int | None = None
    token_counting_method: str = "estimate"

    def __post_init__(self) -> None:
        """Validate capabilities configuration."""
        valid_methods = ["tiktoken", "claude-tokenizer", "estimate"]
        if self.token_counting_method not in valid_methods:
            msg = (
                f"token_counting_method must be one of {valid_methods}, "
                f"got '{self.token_counting_method}'"
            )
            raise ValueError(msg)
        if self.max_tokens_limit <= 0:
            msg = f"max_tokens_limit must be > 0, got {self.max_tokens_limit}"
            raise ValueError(msg)
        if self.embedding_dim is not None and self.embedding_dim <= 0:
            msg = f"embedding_dim must be > 0, got {self.embedding_dim}"
            raise ValueError(msg)


@dataclass(frozen=True)
class RateLimitsConfig:
    """Rate limiting configuration for a provider.

    Attributes:
        requests_per_minute: Maximum requests per minute
        tokens_per_minute: Maximum tokens per minute
        concurrent_requests: Maximum concurrent requests
    """

    requests_per_minute: int | None = None
    tokens_per_minute: int | None = None
    concurrent_requests: int = 10

    def __post_init__(self) -> None:
        """Validate rate limits configuration."""
        if self.requests_per_minute is not None and self.requests_per_minute <= 0:
            msg = f"requests_per_minute must be > 0, got {self.requests_per_minute}"
            raise ValueError(msg)
        if self.tokens_per_minute is not None and self.tokens_per_minute <= 0:
            msg = f"tokens_per_minute must be > 0, got {self.tokens_per_minute}"
            raise ValueError(msg)
        if self.concurrent_requests <= 0:
            msg = f"concurrent_requests must be > 0, got {self.concurrent_requests}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ModelConfig:
    """Model configuration within a provider.

    Attributes:
        name: Model name/identifier
        cost_per_1k_input: Cost per 1K input tokens (USD)
        cost_per_1k_output: Cost per 1K output tokens (USD)
        max_tokens: Maximum context window for this model
        quality_score: Quality score (1-10, higher is better)
        aliases: Alternative names for this model
    """

    name: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_tokens: int = 4096
    quality_score: int = 5
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate model configuration."""
        if not self.name:
            msg = "Model name cannot be empty"
            raise ValueError(msg)
        if self.cost_per_1k_input < 0:
            msg = f"cost_per_1k_input must be >= 0, got {self.cost_per_1k_input}"
            raise ValueError(msg)
        if self.cost_per_1k_output < 0:
            msg = f"cost_per_1k_output must be >= 0, got {self.cost_per_1k_output}"
            raise ValueError(msg)
        if self.max_tokens <= 0:
            msg = f"max_tokens must be > 0, got {self.max_tokens}"
            raise ValueError(msg)
        if not (1 <= self.quality_score <= 10):
            msg = f"quality_score must be 1-10, got {self.quality_score}"
            raise ValueError(msg)

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost for token usage.

        Args:
            tokens_in: Input tokens
            tokens_out: Output tokens

        Returns:
            Estimated cost in USD
        """
        cost_in = (tokens_in / 1000.0) * self.cost_per_1k_input
        cost_out = (tokens_out / 1000.0) * self.cost_per_1k_output
        return cost_in + cost_out


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single provider.

    Attributes:
        name: Provider name/identifier
        type: Provider type ("api", "local", "hybrid")
        connection: Connection configuration
        capabilities: Provider capabilities
        rate_limits: Rate limiting configuration
        models: List of available models
        enabled: Whether this provider is enabled
    """

    name: str
    type: str
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    capabilities: CapabilitiesConfig = field(default_factory=CapabilitiesConfig)
    rate_limits: RateLimitsConfig = field(default_factory=RateLimitsConfig)
    models: tuple[ModelConfig, ...] = field(default_factory=tuple)
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate provider configuration."""
        if not self.name:
            msg = "Provider name cannot be empty"
            raise ValueError(msg)

        valid_types = ["api", "local", "hybrid"]
        if self.type not in valid_types:
            msg = f"Provider type must be one of {valid_types}, got '{self.type}'"
            raise ValueError(msg)

    def get_model(self, name: str) -> ModelConfig | None:
        """Get model configuration by name or alias.

        Args:
            name: Model name or alias

        Returns:
            ModelConfig or None if not found
        """
        for model in self.models:
            if model.name == name or name in model.aliases:
                return model
        return None

    def get_best_model(self) -> ModelConfig | None:
        """Get highest quality model.

        Returns:
            ModelConfig with highest quality_score or None if no models
        """
        if not self.models:
            return None
        return max(self.models, key=lambda m: m.quality_score)

    def get_cheapest_model(self) -> ModelConfig | None:
        """Get lowest cost model.

        Returns:
            ModelConfig with lowest cost or None if no models
        """
        if not self.models:
            return None
        return min(self.models, key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)


@dataclass(frozen=True)
class ProvidersConfig:
    """Root provider configuration.

    Attributes:
        version: Configuration schema version
        llm: LLM provider configurations (dict of provider_name -> ProviderConfig)
        embedding: Embedding provider configurations
        default_llm_provider: Default LLM provider name
        default_embedding_provider: Default embedding provider name
    """

    version: str = "1.0.0"
    llm: dict[str, ProviderConfig] = field(default_factory=dict)
    embedding: dict[str, ProviderConfig] = field(default_factory=dict)
    default_llm_provider: str = "anthropic"
    default_embedding_provider: str = "sentence-transformer"

    def get_llm_provider(self, name: str | None = None) -> ProviderConfig | None:
        """Get LLM provider configuration.

        Args:
            name: Provider name (uses default if None)

        Returns:
            ProviderConfig or None if not found
        """
        provider_name = name or self.default_llm_provider
        return self.llm.get(provider_name)

    def get_embedding_provider(self, name: str | None = None) -> ProviderConfig | None:
        """Get embedding provider configuration.

        Args:
            name: Provider name (uses default if None)

        Returns:
            ProviderConfig or None if not found
        """
        provider_name = name or self.default_embedding_provider
        return self.embedding.get(provider_name)

    def list_llm_providers(self) -> list[str]:
        """List all LLM provider names.

        Returns:
            List of provider names
        """
        return list(self.llm.keys())

    def list_embedding_providers(self) -> list[str]:
        """List all embedding provider names.

        Returns:
            List of provider names
        """
        return list(self.embedding.keys())
