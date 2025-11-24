# LLM Infrastructure (Internal)

**⚠️ This is an internal infrastructure library, not a full technique family.**

## Overview

The LLM infrastructure provides core utilities for interacting with language models throughout the Sibyl framework. It includes client implementations, routing logic, JSON repair utilities, lifecycle management, and token counting.

## Components

### Anthropic Client (`anthropic_client.py`)
- **AnthropicClient**: Official client wrapper for Anthropic's Claude API
- Handles authentication, request formatting, and response parsing
- Implements retry logic and error handling

### LLM Router (`router.py`)
- **LLMRouter**: Routes requests to appropriate LLM providers or specialists
- Supports fallback strategies and load balancing
- Integrates with the routing decision system

### JSON Repair (`json_repair.py`)
- **JSONRepair**: Utilities for fixing malformed JSON from LLM outputs
- Handles common JSON formatting errors
- Preserves intent while ensuring valid JSON structure

### Lifecycle Manager (`lifecycle.py`)
- **LifecycleManager**: Manages LLM request lifecycle
- Tracks request state, retries, and timeouts
- Provides hooks for monitoring and debugging

### Token Counter (`token_counter.py`)
- **TokenCounter**: Counts tokens for various LLM providers
- Supports different tokenization schemes
- Used for budget management and cost tracking

### Feature Flags (`feature_flags.py`)
- **get_features()**: Retrieves feature flag configuration
- Enables/disables experimental LLM features
- Runtime configuration without code changes

## Usage

```python
from sibyl.techniques.infrastructure.llm import (
    AnthropicClient,
    LLMRouter,
    TokenCounter
)

# Initialize client
client = AnthropicClient(api_key="...")

# Route a request
router = LLMRouter()
response = router.route(prompt, config)

# Count tokens
counter = TokenCounter()
token_count = counter.count(text, model="claude-3-sonnet")
```

## Extension Points

Users can extend the LLM infrastructure by:

1. Implementing custom LLM clients following the client protocol
2. Registering custom providers with the router
3. Adding custom token counting schemes
4. Implementing custom JSON repair strategies

## Not a Technique

Unlike other directories in `infrastructure/`, the `llm/` library:
- Does NOT follow the technique template structure
- Does NOT have subtechniques or implementations hierarchy
- IS a utility library for internal framework use
- Provides core LLM functionality used by all techniques

## Related

- See `sibyl/runtime/providers/` for provider implementations
- See `sibyl/techniques/infrastructure/rate_limiting/` for rate limiting techniques
- See `sibyl/techniques/infrastructure/token_management/` for token budget techniques
