# Custom Provider Example: Echo LLM

This example demonstrates how to create a custom LLM provider in Sibyl.

## Overview

The `EchoLLMProvider` is a simple custom provider that:

- Echoes back the input prompt with a configurable prefix
- Simulates token usage and latency
- Supports synchronous, async, and streaming completions
- Requires no external API or API keys

This is useful for:
- Testing pipelines without API costs
- Development and debugging
- Unit testing
- Demonstrating custom provider patterns

## Files

- `echo_llm.py` - Custom provider implementations (Echo and Transform)
- `workspace.yaml` - Workspace configuration using custom providers
- `README.md` - This file
- `run_example.py` - Standalone example demonstrating usage

## Installation

No additional dependencies required beyond Sibyl's core dependencies.

## Usage

### 1. Integrate Provider into Factory

To use the custom provider, you need to add it to the provider factory.

**Option A: Modify existing factory (sibyl/runtime/providers/factories.py)**

```python
def create_llm_provider(config: LLMProviderConfig) -> LLMProvider:
    """Create an LLM provider instance from configuration."""

    # Add custom providers
    if config.provider == "echo":
        from examples.extensions.custom_provider.echo_llm import EchoLLMProvider
        return EchoLLMProvider(
            model=config.model,
            prefix=config.get("prefix", "[ECHO] "),
            simulate_latency_ms=config.get("simulate_latency_ms", 10)
        )

    elif config.provider == "transform":
        from examples.extensions.custom_provider.echo_llm import TransformLLMProvider
        return TransformLLMProvider(
            model=config.model,
            transform=config.get("transform", "uppercase")
        )

    # ... existing providers
```

**Option B: Create custom factory wrapper**

```python
# my_factories.py
from sibyl.runtime.providers.factories import create_llm_provider as _create_llm_provider
from examples.extensions.custom_provider.echo_llm import EchoLLMProvider

def create_llm_provider(config):
    """Extended factory with custom providers"""
    if config.provider == "echo":
        return EchoLLMProvider(
            model=config.model,
            prefix=config.get("prefix", "[ECHO] ")
        )

    # Fall back to original factory
    return _create_llm_provider(config)
```

### 2. Configure in Workspace

Add your provider to workspace configuration:

```yaml
providers:
  llm:
    echo:
      provider: "echo"
      model: "echo-1"
      prefix: "[ECHO] "
      simulate_latency_ms: 10
```

### 3. Use in Code

```python
from sibyl.workspace import load_workspace
from sibyl.runtime.providers.registry import build_providers
from sibyl.core.protocols.infrastructure.llm import CompletionOptions

# Load workspace and build providers
workspace = load_workspace("examples/extensions/custom_provider/workspace.yaml")
registry = build_providers(workspace)

# Get echo provider
echo_provider = registry.get_llm("echo")

# Use provider
options = CompletionOptions(
    model="echo-1",
    temperature=0.0,
    max_tokens=100
)

result = echo_provider.complete("Hello, world!", options)
print(result["text"])  # Output: [ECHO] Hello, world!

# Streaming
for chunk in echo_provider.complete_stream("Test stream", options):
    print(chunk["delta"], end="", flush=True)
```

## Running the Example

Run the standalone example:

```bash
# From the repository root
python examples/extensions/custom_provider/run_example.py
```

This will:
1. Create provider instances
2. Demonstrate synchronous completions
3. Show async completions
4. Test streaming
5. Show token counting
6. Display provider features

## Provider Features

### Echo Provider

**Features:**
- Synchronous and async completion
- Streaming support
- Configurable prefix
- Simulated latency
- No external dependencies

**Configuration:**
```yaml
provider: "echo"
model: "echo-1"
prefix: "[ECHO] "  # Prefix for echoed text
simulate_latency_ms: 10  # Simulated API latency
```

**Use Cases:**
- Unit testing pipelines
- Development without API costs
- Debugging prompt templates
- Integration testing

### Transform Provider

**Features:**
- Text transformations (uppercase, lowercase, reverse, etc.)
- Deterministic output
- Fast execution

**Configuration:**
```yaml
provider: "transform"
model: "transform-1"
transform: "uppercase"  # Options: uppercase, lowercase, reverse, title, capitalize
```

**Use Cases:**
- Testing text processing pipelines
- Debugging workflows
- Demonstrating provider patterns

## Creating Your Own Provider

### Step 1: Implement the Protocol

```python
from sibyl.core.protocols.infrastructure.llm import (
    LLMProvider,
    CompletionOptions,
    CompletionResult,
    ProviderFingerprint,
    ProviderFeatures
)

class MyCustomProvider:
    def __init__(self, model: str, **kwargs):
        self.model = model
        # Initialize your provider

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        # Implement completion logic
        return CompletionResult(
            text="...",
            tokens_in=0,
            tokens_out=0,
            latency_ms=0,
            finish_reason="stop",
            provider_metadata={},
            fingerprint=ProviderFingerprint(
                provider="my_provider",
                model=self.model,
                version="1.0.0"
            )
        )

    async def complete_async(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        # Implement async completion
        pass

    async def structured_complete(self, prompt: str, schema: dict, options: CompletionOptions) -> CompletionResult:
        # Implement structured output (optional)
        raise NotImplementedError()

    def complete_stream(self, prompt: str, options: CompletionOptions):
        # Implement streaming (optional)
        yield {"delta": "...", "is_final": False}

    def count_tokens(self, text: str, model: str) -> int:
        # Implement token counting
        return len(text.split())

    def get_features(self) -> ProviderFeatures:
        # Declare capabilities
        return ProviderFeatures(
            supports_structured=False,
            supports_seed=False,
            supports_streaming=False,
            supports_tools=False,
            max_tokens_limit=4096,
            token_counting_method="estimate"
        )
```

### Step 2: Add to Factory

See "Integrate Provider into Factory" section above.

### Step 3: Test

```python
import pytest
from my_provider import MyCustomProvider
from sibyl.core.protocols.infrastructure.llm import CompletionOptions

def test_custom_provider():
    provider = MyCustomProvider(model="custom-1")

    options = CompletionOptions(
        model="custom-1",
        temperature=0.0,
        max_tokens=100
    )

    result = provider.complete("Test", options)

    assert result["text"] is not None
    assert result["finish_reason"] == "stop"
    assert result["fingerprint"]["provider"] == "my_provider"
```

## Advanced Examples

### Provider with External API

```python
class APIBasedProvider:
    """Provider that calls external API"""

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        import requests

        response = requests.post(
            f"{self.base_url}/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": options.temperature,
                "max_tokens": options.max_tokens,
            },
            timeout=options.timeout_ms / 1000.0
        )

        response.raise_for_status()
        data = response.json()

        return CompletionResult(
            text=data["text"],
            tokens_in=data.get("tokens_in", 0),
            tokens_out=data.get("tokens_out", 0),
            latency_ms=int(response.elapsed.total_seconds() * 1000),
            finish_reason=data.get("finish_reason", "stop"),
            provider_metadata={"api_response": data},
            fingerprint=ProviderFingerprint(
                provider="my_api",
                model=self.model,
                version="1.0.0"
            )
        )
```

### Provider with Caching

```python
class CachedProvider:
    """Provider with response caching"""

    def __init__(self, base_provider: LLMProvider):
        self.base_provider = base_provider
        self.cache = {}

    def complete(self, prompt: str, options: CompletionOptions) -> CompletionResult:
        # Create cache key
        cache_key = (prompt, options.temperature, options.max_tokens)

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Call base provider
        result = self.base_provider.complete(prompt, options)

        # Cache result
        self.cache[cache_key] = result

        return result
```

## Testing

Run tests for the custom provider:

```python
import pytest
from examples.extensions.custom_provider.echo_llm import EchoLLMProvider
from sibyl.core.protocols.infrastructure.llm import CompletionOptions

def test_echo_completion():
    provider = EchoLLMProvider(model="echo-1", prefix="[TEST] ")

    options = CompletionOptions(model="echo-1", temperature=0.0, max_tokens=100)
    result = provider.complete("Hello", options)

    assert result["text"] == "[TEST] Hello"
    assert result["tokens_in"] == 1
    assert result["finish_reason"] == "stop"

def test_echo_streaming():
    provider = EchoLLMProvider(model="echo-1", prefix="")

    options = CompletionOptions(model="echo-1", temperature=0.0, max_tokens=100)
    chunks = list(provider.complete_stream("Hello world", options))

    assert len(chunks) == 2
    assert chunks[-1]["is_final"] is True

@pytest.mark.asyncio
async def test_echo_async():
    provider = EchoLLMProvider(model="echo-1", prefix="[ASYNC] ")

    options = CompletionOptions(model="echo-1", temperature=0.0, max_tokens=100)
    result = await provider.complete_async("Test", options)

    assert result["text"] == "[ASYNC] Test"
```

## Best Practices

1. **Implement All Protocol Methods**: Even if some aren't used, provide implementations or raise `NotImplementedError`

2. **Handle Errors Gracefully**: Wrap provider-specific errors in standard exceptions

3. **Support Configuration**: Accept configuration in `__init__` and validate it

4. **Test Thoroughly**: Test sync, async, streaming, error cases

5. **Document Capabilities**: Accurately report features in `get_features()`

6. **Token Counting**: Provide accurate token estimates with safety margin

## Related Documentation

- [Custom Providers Guide](../../../docs/extending/custom_providers.md)
- [Extension Points Overview](../../../docs/extending/overview.md)
- [LLM Provider Protocol](../../../sibyl/core/protocols/infrastructure/llm.py)

## Next Steps

1. Study the implementation in `echo_llm.py`
2. Run the example to see it in action
3. Create your own custom provider (e.g., for Ollama, vLLM, etc.)
4. Share your provider with the community
