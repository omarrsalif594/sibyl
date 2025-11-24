"""Provider feature flags and capabilities."""

import logging

from sibyl.core.contracts.providers import ProviderFeatures

logger = logging.getLogger(__name__)


def _build_provider_features_from_config() -> dict[str, ProviderFeatures]:
    """Build provider features dictionary from configuration.

    Returns:
        Dictionary of provider_name -> ProviderFeatures

    Note:
        This function dynamically loads provider features from the configuration
        file, making it easy to add or modify provider capabilities without code changes.
    """
    from sibyl.core.server.config import get_config

    try:
        config = get_config()

        if not config.providers:
            logger.warning("No provider configuration found, using empty provider features")
            return {}

        provider_features = {}

        # Build features from all LLM providers
        for provider_name, provider_config in config.providers.llm.items():
            features = ProviderFeatures(
                supports_structured=provider_config.capabilities.supports_structured,
                supports_seed=provider_config.capabilities.supports_seed,
                supports_streaming=provider_config.capabilities.supports_streaming,
                supports_tools=provider_config.capabilities.supports_tools,
                max_tokens_limit=provider_config.capabilities.max_tokens_limit,
                token_counting_method=provider_config.capabilities.token_counting_method,
            )
            provider_features[provider_name] = features

        logger.info(
            "Built provider features for %s providers from configuration", len(provider_features)
        )
        return provider_features

    except Exception as e:
        logger.exception("Failed to build provider features from config: %s", e)
        return {}


# Global provider features cache (lazy-loaded from config)
_PROVIDER_FEATURES: dict[str, ProviderFeatures] | None = None


def get_provider_features_dict() -> dict[str, ProviderFeatures]:
    """Get provider features dictionary (lazy-loaded from configuration).

    Returns:
        Dictionary of provider_name -> ProviderFeatures
    """
    global _PROVIDER_FEATURES

    if _PROVIDER_FEATURES is None:
        _PROVIDER_FEATURES = _build_provider_features_from_config()

    return _PROVIDER_FEATURES


# Note: Lazy-loaded to avoid circular imports during module initialization
_PROVIDER_FEATURES_INITIALIZED = False


def _ensure_provider_features_loaded() -> None:
    """Ensure PROVIDER_FEATURES is loaded (call this before accessing it)."""
    global _PROVIDER_FEATURES_INITIALIZED, PROVIDER_FEATURES
    if not _PROVIDER_FEATURES_INITIALIZED:
        PROVIDER_FEATURES = get_provider_features_dict()
        _PROVIDER_FEATURES_INITIALIZED = True


# Initialize as empty dict, will be populated on first access
PROVIDER_FEATURES = {}


def get_features(provider: str) -> ProviderFeatures:
    """Get feature flags for a provider.

    Args:
        provider: Provider name ("anthropic", "openai", etc.)

    Returns:
        ProviderFeatures describing capabilities

    Raises:
        KeyError: If provider not found
    """
    _ensure_provider_features_loaded()
    features_dict = get_provider_features_dict()
    if provider not in features_dict:
        msg = f"Unknown provider: {provider}"
        raise KeyError(msg)
    return features_dict[provider]


def supports_capability(provider: str, capability: str) -> bool:
    """Check if provider supports a specific capability.

    Args:
        provider: Provider name
        capability: Capability name ("structured", "seed", "streaming", "tools")

    Returns:
        True if supported, False otherwise
    """
    try:
        features = get_features(provider)
        return getattr(features, f"supports_{capability}", False)
    except (KeyError, AttributeError):
        return False
