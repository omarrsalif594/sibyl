# Providers Infrastructure (Internal)

**⚠️ This is an internal infrastructure library, not a full technique family.**

## Overview

The providers infrastructure manages LLM provider configuration, instantiation, and registration. It provides a factory pattern for creating provider instances and a registry for discovering available providers.

## Components

### Provider Config (`config.py`)
- **ProviderConfig**: Configuration schema for LLM providers
- Manages API keys, endpoints, model settings, and quotas
- Supports environment variable interpolation
- Validates provider configurations

### Provider Factory (`factory.py`)
- **ProviderFactory**: Creates provider instances from configurations
- Implements factory pattern for provider instantiation
- Handles dependency injection and initialization
- Supports custom provider registration

### Provider Registry (`registry.py`)
- **ProviderRegistry**: Central registry of available providers
- Discovers and catalogs LLM providers
- Provides lookup and enumeration capabilities
- Manages provider lifecycle and caching

## Usage

```python
from sibyl.techniques.infrastructure.providers import (
    ProviderConfig,
    ProviderFactory,
    ProviderRegistry
)

# Create a provider configuration
config = ProviderConfig(
    name="anthropic",
    api_key="...",
    default_model="claude-3-sonnet-20240229"
)

# Create provider instance
factory = ProviderFactory()
provider = factory.create(config)

# Register and discover providers
registry = ProviderRegistry()
registry.register("anthropic", provider)
available = registry.list_providers()
```

## Provider Configuration Schema

```yaml
provider:
  name: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  base_url: https://api.anthropic.com
  default_model: claude-3-sonnet-20240229
  max_tokens: 4096
  timeout: 60
  rate_limit:
    requests_per_minute: 50
    tokens_per_minute: 40000
```

## Extension Points

Users can extend the providers infrastructure by:

1. Implementing custom provider classes following the provider protocol
2. Registering custom providers with the factory
3. Adding custom configuration validators
4. Implementing custom provider discovery mechanisms

## Not a Technique

Unlike other directories in `infrastructure/`, the `providers/` library:
- Does NOT follow the technique template structure
- Does NOT have subtechniques or implementations hierarchy
- IS a utility library for internal framework use
- Provides core provider management used throughout the framework

## Related

- See `sibyl/runtime/providers/` for runtime provider implementations
- See `sibyl/techniques/infrastructure/llm/` for LLM client infrastructure
- See `sibyl/core/contracts/providers.py` for provider protocol definitions
