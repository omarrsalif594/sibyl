"""Provider registry for runtime provider management.

The ProviderRegistry provides a centralized registry for managing providers
at runtime. It handles provider registration, validation, and retrieval based
on configuration.

Example usage:
    # Initialize registry from configuration
    registry = ProviderRegistry.from_config(config.providers)

    # Get a provider configuration
    provider = registry.get_llm_provider("anthropic")

    # Create a provider instance (NEW - uses factory)
    client = registry.create_llm_provider_instance("anthropic")

    # Get a specific model from a provider
    model = registry.get_model("anthropic", "claude-opus-4")

    # List all providers
    llm_providers = registry.list_llm_providers()
"""

import logging

from sibyl.core.protocols.infrastructure.llm import LLMProvider
from sibyl.techniques.rag_pipeline.search.impls.core.vector_index import EmbeddingProvider

from .config import ModelConfig, ProviderConfig, ProvidersConfig
from .factory import ProviderFactory

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Runtime registry for managing providers.

    The registry maintains a runtime view of all configured providers and
    provides methods to register, retrieve, and query providers.

    Attributes:
        _llm_providers: Dictionary of LLM provider name -> ProviderConfig
        _embedding_providers: Dictionary of embedding provider name -> ProviderConfig
        _default_llm_provider: Default LLM provider name
        _default_embedding_provider: Default embedding provider name
    """

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._llm_providers: dict[str, ProviderConfig] = {}
        self._embedding_providers: dict[str, ProviderConfig] = {}
        self._default_llm_provider: str | None = None
        self._default_embedding_provider: str | None = None

    @classmethod
    def from_config(cls, providers_config: ProvidersConfig) -> "ProviderRegistry":
        """Create a ProviderRegistry from ProvidersConfig.

        Args:
            providers_config: ProvidersConfig instance

        Returns:
            Initialized ProviderRegistry

        Example:
            config = load_config()
            registry = ProviderRegistry.from_config(config.providers)
        """
        registry = cls()

        # Register LLM providers
        for name, provider in providers_config.llm.items():
            if provider.enabled:
                registry.register_llm_provider(name, provider)
                logger.info("Registered LLM provider: %s", name)
            else:
                logger.debug("Skipped disabled LLM provider: %s", name)

        # Register embedding providers
        for name, provider in providers_config.embedding.items():
            if provider.enabled:
                registry.register_embedding_provider(name, provider)
                logger.info("Registered embedding provider: %s", name)
            else:
                logger.debug("Skipped disabled embedding provider: %s", name)

        # Set defaults
        registry._default_llm_provider = providers_config.default_llm_provider
        registry._default_embedding_provider = providers_config.default_embedding_provider

        logger.info(
            f"ProviderRegistry initialized with "
            f"{len(registry._llm_providers)} LLM providers, "
            f"{len(registry._embedding_providers)} embedding providers"
        )

        return registry

    def register_llm_provider(self, name: str, provider: ProviderConfig) -> None:
        """Register an LLM provider.

        Args:
            name: Provider name
            provider: ProviderConfig instance

        Raises:
            ValueError: If provider name is empty or provider is invalid
        """
        if not name:
            msg = "Provider name cannot be empty"
            raise ValueError(msg)

        if not isinstance(provider, ProviderConfig):
            msg = f"Expected ProviderConfig, got {type(provider)}"
            raise TypeError(msg)

        self._llm_providers[name] = provider
        logger.debug("Registered LLM provider: %s with %s models", name, len(provider.models))

    def register_embedding_provider(self, name: str, provider: ProviderConfig) -> None:
        """Register an embedding provider.

        Args:
            name: Provider name
            provider: ProviderConfig instance

        Raises:
            ValueError: If provider name is empty or provider is invalid
        """
        if not name:
            msg = "Provider name cannot be empty"
            raise ValueError(msg)

        if not isinstance(provider, ProviderConfig):
            msg = f"Expected ProviderConfig, got {type(provider)}"
            raise TypeError(msg)

        self._embedding_providers[name] = provider
        logger.debug("Registered embedding provider: %s", name)

    def get_llm_provider(self, name: str | None = None) -> ProviderConfig | None:
        """Get an LLM provider by name.

        Args:
            name: Provider name (uses default if None)

        Returns:
            ProviderConfig or None if not found

        Example:
            provider = registry.get_llm_provider("anthropic")
            if provider:
                print(f"Provider type: {provider.type}")
        """
        provider_name = name or self._default_llm_provider

        if not provider_name:
            logger.warning("No LLM provider name specified and no default configured")
            return None

        provider = self._llm_providers.get(provider_name)

        if not provider:
            logger.warning("LLM provider not found: %s", provider_name)

        return provider

    def get_embedding_provider(self, name: str | None = None) -> ProviderConfig | None:
        """Get an embedding provider by name.

        Args:
            name: Provider name (uses default if None)

        Returns:
            ProviderConfig or None if not found
        """
        provider_name = name or self._default_embedding_provider

        if not provider_name:
            logger.warning("No embedding provider name specified and no default configured")
            return None

        provider = self._embedding_providers.get(provider_name)

        if not provider:
            logger.warning("Embedding provider not found: %s", provider_name)

        return provider

    def create_llm_provider_instance(self, name: str | None = None) -> LLMProvider:
        """Create an LLM provider instance using the factory.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Instantiated LLM provider

        Raises:
            ValueError: If provider not found or creation fails

        Example:
            client = registry.create_llm_provider_instance("anthropic")
            result = await client.complete_async(prompt, options)
        """
        provider_config = self.get_llm_provider(name)

        if not provider_config:
            provider_name = name or self._default_llm_provider
            msg = f"LLM provider not found: {provider_name}"
            raise ValueError(msg)

        return ProviderFactory.create_llm_provider(provider_config)

    def create_embedding_provider_instance(self, name: str | None = None) -> EmbeddingProvider:
        """Create an embedding provider instance using the factory.

        Args:
            name: Provider name (uses default if None)

        Returns:
            Instantiated embedding provider

        Raises:
            ValueError: If provider not found or creation fails

        Example:
            embedder = registry.create_embedding_provider_instance("fastembed")
            embeddings = embedder.embed_batch(texts)
        """
        provider_config = self.get_embedding_provider(name)

        if not provider_config:
            provider_name = name or self._default_embedding_provider
            msg = f"Embedding provider not found: {provider_name}"
            raise ValueError(msg)

        return ProviderFactory.create_embedding_provider(provider_config)

    def get_model(self, provider_name: str, model_name: str) -> ModelConfig | None:
        """Get a specific model configuration from a provider.

        Args:
            provider_name: Provider name
            model_name: Model name or alias

        Returns:
            ModelConfig or None if not found

        Example:
            model = registry.get_model("anthropic", "claude-opus-4")
            if model:
                print(f"Model cost: ${model.cost_per_1k_input}/1K tokens")
        """
        # Try LLM providers first
        provider = self._llm_providers.get(provider_name)

        if not provider:
            # Try embedding providers
            provider = self._embedding_providers.get(provider_name)

        if not provider:
            logger.warning("Provider not found: %s", provider_name)
            return None

        return provider.get_model(model_name)

    def list_llm_providers(self) -> list[str]:
        """List all registered LLM provider names.

        Returns:
            List of provider names
        """
        return list(self._llm_providers.keys())

    def list_embedding_providers(self) -> list[str]:
        """List all registered embedding provider names.

        Returns:
            List of provider names
        """
        return list(self._embedding_providers.keys())

    def list_models(self, provider_name: str) -> list[str]:
        """List all models for a given provider.

        Args:
            provider_name: Provider name

        Returns:
            List of model names (empty if provider not found)
        """
        provider = self._llm_providers.get(provider_name) or self._embedding_providers.get(
            provider_name
        )

        if not provider:
            logger.warning("Provider not found: %s", provider_name)
            return []

        return [model.name for model in provider.models]

    def get_default_llm_provider(self) -> str | None:
        """Get default LLM provider name.

        Returns:
            Default provider name or None
        """
        return self._default_llm_provider

    def get_default_embedding_provider(self) -> str | None:
        """Get default embedding provider name.

        Returns:
            Default provider name or None
        """
        return self._default_embedding_provider

    def validate(self) -> list[str]:
        """Validate registry configuration.

        Returns:
            List of validation warnings (empty if valid)

        Example:
            warnings = registry.validate()
            for warning in warnings:
                print(f"Warning: {warning}")
        """
        warnings = []

        # Check if default providers are registered
        if self._default_llm_provider and self._default_llm_provider not in self._llm_providers:
            warnings.append(
                f"Default LLM provider '{self._default_llm_provider}' is not registered"
            )

        if (
            self._default_embedding_provider
            and self._default_embedding_provider not in self._embedding_providers
        ):
            warnings.append(
                f"Default embedding provider '{self._default_embedding_provider}' is not registered"
            )

        # Check if providers have models (for LLM providers)
        for name, provider in self._llm_providers.items():
            if not provider.models:
                warnings.append(f"LLM provider '{name}' has no models configured")

        return warnings

    def __repr__(self) -> str:
        """String representation of registry."""
        return (
            f"ProviderRegistry("
            f"llm_providers={len(self._llm_providers)}, "
            f"embedding_providers={len(self._embedding_providers)}, "
            f"default_llm='{self._default_llm_provider}', "
            f"default_embedding='{self._default_embedding_provider}')"
        )


# Global registry instance (lazy-loaded)
_global_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry instance (singleton pattern).

    Returns:
        ProviderRegistry instance

    Raises:
        RuntimeError: If registry has not been initialized

    Example:
        # Initialize registry first (typically in application startup)
        from sibyl.core.server.config import get_config
        registry = ProviderRegistry.from_config(get_config().providers)
        set_provider_registry(registry)

        # Later, get registry anywhere
        registry = get_provider_registry()
        provider = registry.get_llm_provider("anthropic")
    """
    global _global_registry

    if _global_registry is None:
        msg = (
            "ProviderRegistry not initialized. "
            "Call set_provider_registry() first or use ProviderRegistry.from_config()"
        )
        raise RuntimeError(msg)

    return _global_registry


def set_provider_registry(registry: ProviderRegistry) -> None:
    """Set global provider registry instance.

    Args:
        registry: ProviderRegistry instance

    Example:
        config = load_config()
        registry = ProviderRegistry.from_config(config.providers)
        set_provider_registry(registry)
    """
    global _global_registry
    _global_registry = registry
    logger.info("Global provider registry set")


def reset_provider_registry() -> None:
    """Reset global provider registry (mainly for testing).

    Example:
        # In tests
        reset_provider_registry()
        registry = ProviderRegistry()
        set_provider_registry(registry)
    """
    global _global_registry
    _global_registry = None
    logger.debug("Global provider registry reset")
