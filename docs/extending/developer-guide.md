# Developer Guide

Complete guide for extending Sibyl with custom providers, techniques, and plugins.

## Overview

Sibyl is designed for extensibility. You can extend it by:

1. **Custom Providers** - Integrate new LLMs, vector stores, data sources
2. **Custom Techniques** - Create new AI processing components
3. **Custom Subtechniques** - Add alternative implementations
4. **Plugins** - Extend workspace capabilities
5. **Custom Pipelines** - Compose techniques in new ways

## Development Setup

### Prerequisites

- Python 3.11+
- pyenv and uv (recommended)
- Git
- IDE (VS Code or PyCharm recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Run setup script
./setup.sh

# Activate virtual environment
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev,vector,monitoring]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
pytest tests/core/unit --maxfail=1

# Check code style
black --check sibyl tests
ruff check sibyl tests

# Type check
mypy sibyl
```

## Project Structure

```
sibyl/
├── sibyl/                      # Main package
│   ├── core/                   # Core infrastructure
│   │   ├── protocols/          # Protocol definitions
│   │   ├── infrastructure/     # State, observability
│   │   └── pipeline/           # Pipeline execution
│   ├── providers/              # Provider implementations
│   │   ├── llm/
│   │   ├── embedding/
│   │   ├── vector_store/
│   │   └── documents/
│   ├── techniques/             # Technique implementations
│   │   ├── rag_pipeline/
│   │   ├── ai_generation/
│   │   ├── workflow_orchestration/
│   │   └── infrastructure/
│   ├── shops/                  # Shop implementations
│   ├── runtime/                # Runtime orchestration
│   ├── server/                 # MCP and HTTP servers
│   └── cli.py                  # CLI entry point
├── config/                     # Configuration files
│   └── workspaces/             # Workspace templates
├── tests/                      # Test suite
│   ├── core/                   # Core tests
│   ├── techniques/             # Technique tests
│   └── providers/              # Provider tests
├── docs/                       # Documentation
├── examples/                   # Example applications
└── pyproject.toml              # Project configuration
```

## Creating Custom Providers

### Step 1: Define the Protocol (if needed)

```python
# sibyl/core/protocols/my_provider.py
from typing import Protocol

class MyProvider(Protocol):
    """Protocol for my custom provider type."""

    def process(self, data: str) -> str:
        """Process data."""
        ...

    async def process_async(self, data: str) -> str:
        """Async processing."""
        ...
```

### Step 2: Implement the Provider

```python
# sibyl/providers/my_provider/implementation.py
from sibyl.core.protocols import MyProvider

class MyCustomProvider:
    """Custom provider implementation."""

    def __init__(self, api_key: str, endpoint: str = "https://api.example.com"):
        self.api_key = api_key
        self.endpoint = endpoint
        self._client = self._initialize_client()

    def _initialize_client(self):
        """Initialize API client."""
        # Your initialization logic
        return CustomClient(self.api_key, self.endpoint)

    def process(self, data: str) -> str:
        """Process data synchronously."""
        response = self._client.call(data)
        return response.result

    async def process_async(self, data: str) -> str:
        """Process data asynchronously."""
        response = await self._client.call_async(data)
        return response.result
```

### Step 3: Add Factory Function

```python
# sibyl/runtime/providers/factories.py

def create_my_provider(config: dict) -> MyProvider:
    """Factory function for creating my provider."""
    return MyCustomProvider(
        api_key=os.getenv("MY_PROVIDER_API_KEY"),
        endpoint=config.get("endpoint", "https://api.example.com"),
        timeout=config.get("timeout", 30),
    )

# Register in provider factory map
PROVIDER_FACTORIES = {
    "my_provider": create_my_provider,
    # ... other providers
}
```

### Step 4: Add Configuration Schema

```python
# sibyl/providers/my_provider/config.py
from pydantic import BaseModel, Field

class MyProviderConfig(BaseModel):
    """Configuration for my custom provider."""

    kind: str = "my_provider"
    endpoint: str = Field(default="https://api.example.com")
    timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
```

### Step 5: Write Tests

```python
# tests/providers/test_my_provider.py
import pytest
from sibyl.providers.my_provider import MyCustomProvider

@pytest.fixture
def provider():
    return MyCustomProvider(
        api_key="test_key",
        endpoint="https://test.example.com"
    )

def test_process(provider):
    """Test synchronous processing."""
    result = provider.process("test data")
    assert result is not None
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_process_async(provider):
    """Test asynchronous processing."""
    result = await provider.process_async("test data")
    assert result is not None
    assert isinstance(result, str)
```

### Step 6: Document the Provider

```python
# sibyl/providers/my_provider/__init__.py
"""
My Custom Provider
==================

This provider integrates with Example API for custom processing.

Configuration:
-------------
```yaml
providers:
  my_provider:
    main:
      kind: my_provider
      endpoint: "https://api.example.com"
      timeout: 30
```

Environment Variables:
--------------------
- MY_PROVIDER_API_KEY: API key for authentication

Example Usage:
-------------
```python
from sibyl.providers.my_provider import MyCustomProvider

provider = MyCustomProvider(api_key="your_key")
result = provider.process("data")
```
"""
```

## Creating Custom Techniques

### Step 1: Define Configuration

```python
# sibyl/techniques/my_technique/config.py
from pydantic import BaseModel, Field

class MyTechniqueConfig(BaseModel):
    """Configuration for my technique."""

    param1: str = Field(description="First parameter")
    param2: int = Field(default=10, ge=1, le=100)
    provider: str = Field(default="default")
```

### Step 2: Implement Base Technique

```python
# sibyl/techniques/my_technique/base.py
from sibyl.techniques.base import BaseTechnique
from sibyl.techniques.my_technique.config import MyTechniqueConfig

class MyTechnique(BaseTechnique):
    """My custom technique."""

    def __init__(self):
        super().__init__()
        self.subtechniques = {}

    async def execute(
        self,
        input_data: dict,
        config: MyTechniqueConfig,
        subtechnique: str = "default"
    ) -> dict:
        """Execute the technique.

        Args:
            input_data: Input data dictionary
            config: Technique configuration
            subtechnique: Subtechnique to use

        Returns:
            Result dictionary

        Raises:
            ValueError: If subtechnique not found
        """
        # Validate input
        self._validate_input(input_data)

        # Get subtechnique implementation
        impl = self.get_subtechnique(subtechnique)

        # Execute
        result = await impl.process(input_data, config)

        # Return result
        return {
            "output": result,
            "metadata": {
                "technique": "my_technique",
                "subtechnique": subtechnique,
            }
        }

    def _validate_input(self, input_data: dict) -> None:
        """Validate input data."""
        if "required_field" not in input_data:
            raise ValueError("Missing required_field in input")
```

### Step 3: Implement Subtechniques

```python
# sibyl/techniques/my_technique/subtechniques/default/technique.py
from sibyl.techniques.my_technique.config import MyTechniqueConfig

class DefaultSubtechnique:
    """Default implementation."""

    async def process(
        self,
        input_data: dict,
        config: MyTechniqueConfig
    ) -> str:
        """Process input data."""
        # Your implementation
        data = input_data["required_field"]
        processed = self._do_processing(data, config)
        return processed

    def _do_processing(self, data: str, config: MyTechniqueConfig) -> str:
        """Internal processing logic."""
        # Your logic here
        return f"Processed: {data} with {config.param1}"
```

```python
# sibyl/techniques/my_technique/subtechniques/advanced/technique.py
class AdvancedSubtechnique:
    """Advanced implementation with more features."""

    async def process(
        self,
        input_data: dict,
        config: MyTechniqueConfig
    ) -> str:
        """Advanced processing."""
        # More sophisticated implementation
        data = input_data["required_field"]
        result = await self._advanced_processing(data, config)
        return result

    async def _advanced_processing(
        self,
        data: str,
        config: MyTechniqueConfig
    ) -> str:
        """Advanced processing with async operations."""
        # Your advanced logic
        return f"Advanced: {data}"
```

### Step 4: Register Subtechniques

```python
# sibyl/techniques/my_technique/__init__.py
from sibyl.techniques.my_technique.base import MyTechnique
from sibyl.techniques.my_technique.subtechniques.default.technique import (
    DefaultSubtechnique
)
from sibyl.techniques.my_technique.subtechniques.advanced.technique import (
    AdvancedSubtechnique
)

def create_my_technique() -> MyTechnique:
    """Create technique with all subtechniques registered."""
    technique = MyTechnique()

    # Register subtechniques
    technique.register_subtechnique("default", DefaultSubtechnique())
    technique.register_subtechnique("advanced", AdvancedSubtechnique())

    return technique
```

### Step 5: Add to Shop

```python
# sibyl/shops/my_shop/shop.py
from sibyl.techniques.my_technique import create_my_technique

class MyShop:
    """My custom shop."""

    def __init__(self):
        self.techniques = {
            "my_technique": create_my_technique(),
            # ... other techniques
        }

    async def execute_technique(
        self,
        technique_name: str,
        input_data: dict,
        config: dict
    ) -> dict:
        """Execute a technique from this shop."""
        if technique_name not in self.techniques:
            raise ValueError(f"Unknown technique: {technique_name}")

        technique = self.techniques[technique_name]
        return await technique.execute(input_data, config)
```

### Step 6: Write Tests

```python
# tests/techniques/test_my_technique.py
import pytest
from sibyl.techniques.my_technique import create_my_technique
from sibyl.techniques.my_technique.config import MyTechniqueConfig

@pytest.fixture
def technique():
    return create_my_technique()

@pytest.mark.asyncio
async def test_default_subtechnique(technique):
    """Test default subtechnique."""
    input_data = {"required_field": "test data"}
    config = MyTechniqueConfig(param1="test", param2=5)

    result = await technique.execute(
        input_data,
        config,
        subtechnique="default"
    )

    assert "output" in result
    assert "Processed" in result["output"]

@pytest.mark.asyncio
async def test_advanced_subtechnique(technique):
    """Test advanced subtechnique."""
    input_data = {"required_field": "test data"}
    config = MyTechniqueConfig(param1="test", param2=10)

    result = await technique.execute(
        input_data,
        config,
        subtechnique="advanced"
    )

    assert "output" in result
    assert "Advanced" in result["output"]

@pytest.mark.asyncio
async def test_missing_input_raises_error(technique):
    """Test that missing input raises error."""
    input_data = {}  # Missing required_field
    config = MyTechniqueConfig(param1="test")

    with pytest.raises(ValueError, match="Missing required_field"):
        await technique.execute(input_data, config)
```

### Step 7: Document the Technique

```markdown
# sibyl/techniques/my_technique/README.md

# My Technique

Custom technique for [describe purpose].

## Subtechniques

### `default`
Basic implementation for [use case].

**Configuration**:
```yaml
use: my_shop.my_technique
config:
  subtechnique: default
  param1: "value"
  param2: 10
```

### `advanced`
Advanced implementation with [features].

**Configuration**:
```yaml
use: my_shop.my_technique
config:
  subtechnique: advanced
  param1: "value"
  param2: 20
```

## Usage Example

```python
from sibyl.techniques.my_technique import create_my_technique

technique = create_my_technique()
result = await technique.execute(
    input_data={"required_field": "data"},
    config=MyTechniqueConfig(param1="test"),
    subtechnique="default"
)
```

## Testing

```bash
pytest tests/techniques/test_my_technique.py -v
```
```

## Creating Plugins

### Step 1: Define Plugin Interface

```python
# sibyl/plugins/base.py
from typing import Protocol

class BasePlugin(Protocol):
    """Base protocol for plugins."""

    def on_workspace_load(self, workspace):
        """Called when workspace is loaded."""
        ...

    def on_pipeline_start(self, pipeline):
        """Called when pipeline starts."""
        ...

    def on_pipeline_complete(self, pipeline, result):
        """Called when pipeline completes."""
        ...

    def on_error(self, error):
        """Called when error occurs."""
        ...
```

### Step 2: Implement Plugin

```python
# plugins/my_plugin/plugin.py
from sibyl.plugins.base import BasePlugin

class MyPlugin:
    """My custom plugin."""

    def __init__(self, config: dict):
        self.config = config
        self.state = {}

    def on_workspace_load(self, workspace):
        """Initialize plugin when workspace loads."""
        print(f"Plugin loaded for workspace: {workspace.name}")
        # Your initialization logic

    def on_pipeline_start(self, pipeline):
        """Hook before pipeline execution."""
        print(f"Pipeline starting: {pipeline.name}")
        self.state["start_time"] = time.time()

    def on_pipeline_complete(self, pipeline, result):
        """Hook after pipeline execution."""
        elapsed = time.time() - self.state.get("start_time", 0)
        print(f"Pipeline {pipeline.name} completed in {elapsed:.2f}s")

    def on_error(self, error):
        """Hook on error."""
        print(f"Error occurred: {error}")
        # Send notification, log to external service, etc.
```

### Step 3: Register Plugin

```yaml
# config/workspaces/my_workspace.yaml
extensions:
  plugins:
    - name: my_plugin
      path: plugins/my_plugin
      config:
        setting1: value1
        setting2: value2
```

## Code Style

### Formatting

```bash
# Format code with Black
black sibyl tests

# Check formatting
black --check sibyl tests
```

### Linting

```bash
# Lint with Ruff
ruff check sibyl tests

# Auto-fix issues
ruff check --fix sibyl tests
```

### Type Checking

```bash
# Type check with mypy
mypy sibyl

# Check specific file
mypy sibyl/techniques/my_technique/base.py
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest -m unit
pytest -m integration

# Run specific file
pytest tests/techniques/test_my_technique.py

# Run with coverage
pytest --cov=sibyl --cov-report=html

# Run with verbose output
pytest -v

# Run in parallel
pytest -n auto
```

### Writing Tests

Follow these guidelines:

1. **Use fixtures** for reusable setup
2. **Mark tests** with appropriate markers
3. **Test edge cases** and error conditions
4. **Mock external services** to avoid dependencies
5. **Aim for 80%+ coverage**

Example:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_llm_provider():
    """Fixture for mocked LLM provider."""
    provider = Mock()
    provider.complete.return_value = "Test response"
    return provider

@pytest.mark.unit
def test_my_function(mock_llm_provider):
    """Test my function with mocked provider."""
    result = my_function(mock_llm_provider)
    assert result == "expected"
    mock_llm_provider.complete.assert_called_once()

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Contribution workflow
- Pull request process
- Code review guidelines

## Further Reading

- **[Custom Providers](custom-providers.md)** - Detailed provider development
- **[Testing Guide](testing-guide.md)** - Comprehensive testing guide
- **[Code Style Guide](code-style.md)** - Coding standards
- **[Architecture](../architecture/overview.md)** - Understanding the architecture

---

**Previous**: [Operations](../operations/deployment.md) | **Next**: [Custom Providers](custom-providers.md)
