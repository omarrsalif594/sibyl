# Creating Custom Techniques

Complete guide to developing custom techniques and extending Sibyl's capabilities.

## Overview

Sibyl's technique system is designed for extensibility. You can create custom techniques to:

- Add new AI capabilities
- Integrate custom models or APIs
- Implement domain-specific logic
- Extend existing technique families

## Technique Architecture

### Technique Components

```
Custom Technique
├── Configuration (Pydantic model)
├── Base Technique (abstract class)
├── Subtechniques (concrete implementations)
└── Factory Function (registration)
```

### File Structure

```
sibyl/techniques/my_technique/
├── __init__.py                  # Exports and factory
├── config.py                    # Configuration schema
├── base.py                      # Base technique class
└── subtechniques/
    ├── default/
    │   └── technique.py         # Default implementation
    └── advanced/
        └── technique.py         # Advanced implementation
```

## Step 1: Define Configuration

Create `sibyl/techniques/my_technique/config.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class MyTechniqueConfig(BaseModel):
    """Configuration for my custom technique."""

    # Required parameters
    param1: str = Field(
        description="First parameter",
        min_length=1
    )

    # Optional parameters with defaults
    param2: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Second parameter (1-100)"
    )

    # Enum parameter
    mode: Literal["fast", "balanced", "accurate"] = Field(
        default="balanced",
        description="Processing mode"
    )

    # Provider reference
    provider: str = Field(
        default="default",
        description="Provider to use"
    )

    # Subtechnique selection
    subtechnique: str = Field(
        default="default",
        description="Which subtechnique to use"
    )

    class Config:
        extra = "forbid"             # Reject unknown fields
        schema_extra = {
            "example": {
                "param1": "value",
                "param2": 20,
                "mode": "balanced",
                "provider": "primary",
                "subtechnique": "default"
            }
        }
```

## Step 2: Implement Base Technique

Create `sibyl/techniques/my_technique/base.py`:

```python
from typing import Dict, Any
from sibyl.techniques.base import BaseTechnique
from sibyl.techniques.my_technique.config import MyTechniqueConfig

class MyTechnique(BaseTechnique):
    """My custom technique for [describe purpose]."""

    def __init__(self):
        super().__init__()
        self.subtechniques: Dict[str, Any] = {}

    async def execute(
        self,
        input_data: Dict[str, Any],
        config: MyTechniqueConfig,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the technique.

        Args:
            input_data: Input data dictionary containing required fields
            config: Technique configuration
            **kwargs: Additional runtime parameters

        Returns:
            Result dictionary with output and metadata

        Raises:
            ValueError: If input validation fails
            RuntimeError: If execution fails
        """
        # 1. Validate input
        self._validate_input(input_data)

        # 2. Get subtechnique implementation
        subtechnique = self.get_subtechnique(config.subtechnique)

        # 3. Execute subtechnique
        try:
            result = await subtechnique.process(
                input_data,
                config,
                **kwargs
            )
        except Exception as e:
            raise RuntimeError(
                f"Execution failed: {e}"
            ) from e

        # 4. Return structured result
        return {
            "output": result,
            "metadata": {
                "technique": "my_technique",
                "subtechnique": config.subtechnique,
                "mode": config.mode,
            }
        }

    def _validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate input data structure."""
        required_fields = ["required_field"]

        for field in required_fields:
            if field not in input_data:
                raise ValueError(
                    f"Missing required field: {field}"
                )

        # Additional validation
        if not isinstance(input_data["required_field"], str):
            raise ValueError(
                "required_field must be a string"
            )

    def register_subtechnique(
        self,
        name: str,
        implementation: Any
    ) -> None:
        """Register a subtechnique implementation."""
        self.subtechniques[name] = implementation

    def get_subtechnique(self, name: str) -> Any:
        """Get a subtechnique by name."""
        if name not in self.subtechniques:
            raise ValueError(
                f"Unknown subtechnique: {name}. "
                f"Available: {list(self.subtechniques.keys())}"
            )
        return self.subtechniques[name]
```

## Step 3: Implement Subtechniques

### Default Subtechnique

Create `sibyl/techniques/my_technique/subtechniques/default/technique.py`:

```python
from typing import Dict, Any
import logging
from sibyl.techniques.my_technique.config import MyTechniqueConfig

logger = logging.getLogger(__name__)

class DefaultSubtechnique:
    """Default implementation of my technique."""

    def __init__(self):
        self.name = "default"

    async def process(
        self,
        input_data: Dict[str, Any],
        config: MyTechniqueConfig,
        **kwargs
    ) -> str:
        """
        Process input data.

        Args:
            input_data: Input data
            config: Configuration
            **kwargs: Additional parameters

        Returns:
            Processed result string
        """
        logger.info(
            f"Processing with {self.name} subtechnique"
        )

        # Get input
        data = input_data["required_field"]

        # Process based on mode
        if config.mode == "fast":
            result = self._fast_process(data, config)
        elif config.mode == "balanced":
            result = self._balanced_process(data, config)
        else:  # accurate
            result = self._accurate_process(data, config)

        logger.info(f"Processed {len(result)} characters")

        return result

    def _fast_process(
        self,
        data: str,
        config: MyTechniqueConfig
    ) -> str:
        """Fast but simple processing."""
        # Your implementation
        return f"Fast: {data[:config.param2]}"

    def _balanced_process(
        self,
        data: str,
        config: MyTechniqueConfig
    ) -> str:
        """Balanced processing."""
        # Your implementation
        processed = data.upper()
        return f"Balanced: {processed[:config.param2]}"

    def _accurate_process(
        self,
        data: str,
        config: MyTechniqueConfig
    ) -> str:
        """Accurate but slower processing."""
        # Your implementation
        processed = data.upper().strip()
        return f"Accurate: {processed[:config.param2]}"
```

### Advanced Subtechnique

Create `sibyl/techniques/my_technique/subtechniques/advanced/technique.py`:

```python
from typing import Dict, Any
import asyncio
import logging
from sibyl.techniques.my_technique.config import MyTechniqueConfig
from sibyl.core.protocols import LLMProvider

logger = logging.getLogger(__name__)

class AdvancedSubtechnique:
    """Advanced implementation with LLM integration."""

    def __init__(self, llm_provider: LLMProvider):
        self.name = "advanced"
        self.llm_provider = llm_provider

    async def process(
        self,
        input_data: Dict[str, Any],
        config: MyTechniqueConfig,
        **kwargs
    ) -> str:
        """Advanced processing with LLM."""
        logger.info(
            f"Processing with {self.name} subtechnique"
        )

        data = input_data["required_field"]

        # Use LLM for processing
        prompt = self._build_prompt(data, config)

        result = await self.llm_provider.complete_async(
            prompt=prompt,
            temperature=0.7,
            max_tokens=config.param2
        )

        return result.text

    def _build_prompt(
        self,
        data: str,
        config: MyTechniqueConfig
    ) -> str:
        """Build LLM prompt."""
        return f"""
Process the following data according to these instructions:
- Mode: {config.mode}
- Parameter: {config.param1}

Data:
{data}

Processed output:
"""
```

## Step 4: Register Technique

Create `sibyl/techniques/my_technique/__init__.py`:

```python
"""
My Custom Technique
===================

This technique provides [describe functionality].

Subtechniques:
--------------
- `default`: Basic processing
- `advanced`: LLM-enhanced processing

Configuration:
-------------
```yaml
use: my_shop.my_technique
config:
  subtechnique: default
  param1: "value"
  param2: 10
  mode: balanced
```

Example Usage:
-------------
```python
from sibyl.techniques.my_technique import create_my_technique

technique = create_my_technique(providers)
result = await technique.execute(
    input_data={"required_field": "data"},
    config=MyTechniqueConfig(param1="test")
)
```
"""

from sibyl.techniques.my_technique.base import MyTechnique
from sibyl.techniques.my_technique.config import MyTechniqueConfig
from sibyl.techniques.my_technique.subtechniques.default.technique import (
    DefaultSubtechnique
)
from sibyl.techniques.my_technique.subtechniques.advanced.technique import (
    AdvancedSubtechnique
)

def create_my_technique(providers=None):
    """
    Create technique with all subtechniques registered.

    Args:
        providers: Provider instances for advanced subtechnique

    Returns:
        Configured MyTechnique instance
    """
    technique = MyTechnique()

    # Register default subtechnique (no dependencies)
    technique.register_subtechnique(
        "default",
        DefaultSubtechnique()
    )

    # Register advanced subtechnique (requires LLM provider)
    if providers and "llm" in providers:
        technique.register_subtechnique(
            "advanced",
            AdvancedSubtechnique(
                llm_provider=providers["llm"]
            )
        )

    return technique

__all__ = [
    "MyTechnique",
    "MyTechniqueConfig",
    "create_my_technique",
]
```

## Step 5: Add to Shop

Create or modify `sibyl/shops/my_shop/shop.py`:

```python
from sibyl.techniques.my_technique import create_my_technique
from sibyl.techniques.other_technique import create_other_technique

class MyShop:
    """My custom shop with techniques."""

    def __init__(self, providers):
        self.providers = providers
        self.techniques = {
            "my_technique": create_my_technique(providers),
            "other_technique": create_other_technique(providers),
        }

    async def execute_technique(
        self,
        technique_name: str,
        input_data: dict,
        config: dict
    ) -> dict:
        """Execute a technique from this shop."""
        if technique_name not in self.techniques:
            raise ValueError(
                f"Unknown technique: {technique_name}"
            )

        technique = self.techniques[technique_name]
        return await technique.execute(input_data, config)
```

## Step 6: Write Tests

Create `tests/techniques/test_my_technique.py`:

```python
import pytest
from sibyl.techniques.my_technique import (
    create_my_technique,
    MyTechniqueConfig
)

@pytest.fixture
def technique():
    """Create technique instance for testing."""
    return create_my_technique()

@pytest.mark.asyncio
async def test_default_subtechnique(technique):
    """Test default subtechnique."""
    input_data = {"required_field": "test data"}
    config = MyTechniqueConfig(
        param1="test",
        param2=5,
        mode="balanced",
        subtechnique="default"
    )

    result = await technique.execute(input_data, config)

    assert "output" in result
    assert "Balanced" in result["output"]
    assert result["metadata"]["technique"] == "my_technique"
    assert result["metadata"]["subtechnique"] == "default"

@pytest.mark.asyncio
async def test_fast_mode(technique):
    """Test fast processing mode."""
    input_data = {"required_field": "test data"}
    config = MyTechniqueConfig(
        param1="test",
        mode="fast"
    )

    result = await technique.execute(input_data, config)

    assert "Fast" in result["output"]

@pytest.mark.asyncio
async def test_missing_input_raises_error(technique):
    """Test that missing input raises error."""
    input_data = {}  # Missing required_field
    config = MyTechniqueConfig(param1="test")

    with pytest.raises(ValueError, match="Missing required field"):
        await technique.execute(input_data, config)

@pytest.mark.asyncio
async def test_unknown_subtechnique_raises_error(technique):
    """Test unknown subtechnique error."""
    input_data = {"required_field": "test"}
    config = MyTechniqueConfig(
        param1="test",
        subtechnique="nonexistent"
    )

    with pytest.raises(ValueError, match="Unknown subtechnique"):
        await technique.execute(input_data, config)

@pytest.mark.parametrize("mode,expected", [
    ("fast", "Fast"),
    ("balanced", "Balanced"),
    ("accurate", "Accurate"),
])
@pytest.mark.asyncio
async def test_all_modes(technique, mode, expected):
    """Test all processing modes."""
    input_data = {"required_field": "test"}
    config = MyTechniqueConfig(param1="test", mode=mode)

    result = await technique.execute(input_data, config)

    assert expected in result["output"]
```

**Run tests**:
```bash
pytest tests/techniques/test_my_technique.py -v
```

## Step 7: Add Documentation

Create `sibyl/techniques/my_technique/README.md`:

```markdown
# My Technique

Custom technique for [describe purpose].

## Subtechniques

### `default`

Basic implementation with three modes.

**Configuration**:
```yaml
use: my_shop.my_technique
config:
  subtechnique: default
  param1: "example"
  param2: 20
  mode: balanced
```

**Modes**:
- `fast`: Quick processing, lower quality
- `balanced`: Balance of speed and quality (recommended)
- `accurate`: Slower but more accurate

### `advanced`

LLM-enhanced implementation.

**Configuration**:
```yaml
use: my_shop.my_technique
config:
  subtechnique: advanced
  param1: "example"
  param2: 100
  provider: primary
```

**Requirements**:
- LLM provider must be configured

## Usage Example

```python
from sibyl.techniques.my_technique import create_my_technique

technique = create_my_technique()

result = await technique.execute(
    input_data={
        "required_field": "Sample data to process"
    },
    config=MyTechniqueConfig(
        param1="example",
        param2=50,
        mode="balanced",
        subtechnique="default"
    )
)

print(result["output"])
```

## Pipeline Configuration

```yaml
pipelines:
  my_pipeline:
    shop: my_shop
    steps:
      - use: my_shop.my_technique
        config:
          param1: "value"
          param2: 20
          mode: accurate
          subtechnique: default
```

## Testing

```bash
pytest tests/techniques/test_my_technique.py -v
```
```

## Advanced Patterns

### Stateful Techniques

```python
class StatefulTechnique(BaseTechnique):
    """Technique that maintains state across executions."""

    def __init__(self):
        super().__init__()
        self.state = {}
        self.execution_count = 0

    async def execute(self, input_data, config, **kwargs):
        self.execution_count += 1

        # Use previous state
        previous_result = self.state.get("last_result")

        # Process
        result = await self._process(
            input_data,
            config,
            previous_result
        )

        # Update state
        self.state["last_result"] = result

        return {
            "output": result,
            "metadata": {
                "execution_count": self.execution_count
            }
        }
```

### Techniques with External APIs

```python
import httpx

class APIIntegrationSubtechnique:
    """Subtechnique that calls external API."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def process(self, input_data, config, **kwargs):
        """Call external API."""
        response = await self.client.post(
            f"{self.base_url}/process",
            headers={
                "Authorization": f"Bearer {self.api_key}"
            },
            json={
                "data": input_data["field"],
                "options": {
                    "param1": config.param1,
                    "param2": config.param2
                }
            },
            timeout=30.0
        )

        response.raise_for_status()
        return response.json()["result"]

    async def close(self):
        """Cleanup."""
        await self.client.aclose()
```

### Composable Techniques

```python
class ComposableTechnique(BaseTechnique):
    """Technique that composes other techniques."""

    def __init__(self, techniques):
        super().__init__()
        self.techniques = techniques

    async def execute(self, input_data, config, **kwargs):
        """Execute multiple techniques in sequence."""
        result = input_data

        for technique_name in config.technique_chain:
            technique = self.techniques[technique_name]

            result = await technique.execute(
                result,
                config.technique_configs[technique_name]
            )

            # Pass output as input to next technique
            result = {"input": result["output"]}

        return result
```

## Best Practices

### 1. Configuration Validation

```python
class MyTechniqueConfig(BaseModel):
    param1: str = Field(..., min_length=1, max_length=100)
    param2: int = Field(..., ge=0, le=1000)

    @validator("param1")
    def validate_param1(cls, v):
        """Custom validation."""
        if not v.isalnum():
            raise ValueError("param1 must be alphanumeric")
        return v
```

### 2. Comprehensive Error Handling

```python
async def execute(self, input_data, config, **kwargs):
    try:
        self._validate_input(input_data)
    except ValueError as e:
        raise ValueError(f"Input validation failed: {e}") from e

    try:
        result = await self._process(input_data, config)
    except ExternalAPIError as e:
        raise RuntimeError(
            f"External API call failed: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Unexpected error: {e}"
        ) from e

    return result
```

### 3. Logging and Observability

```python
import logging
from sibyl.core.observability import trace_async

logger = logging.getLogger(__name__)

class ObservableSubtechnique:
    @trace_async("my_technique.process")
    async def process(self, input_data, config, **kwargs):
        logger.info(
            f"Processing with config: {config.dict()}"
        )

        start_time = time.time()

        result = await self._do_process(input_data, config)

        duration = time.time() - start_time
        logger.info(f"Processing took {duration:.2f}s")

        return result
```

### 4. Testing

```python
# Unit tests
@pytest.mark.asyncio
async def test_basic_functionality():
    """Test core functionality."""
    ...

# Integration tests
@pytest.mark.asyncio
@pytest.mark.integration
async def test_with_real_providers():
    """Test with real provider integration."""
    ...

# Parameterized tests
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
])
@pytest.mark.asyncio
async def test_various_inputs(input, expected):
    """Test various input cases."""
    ...
```

## Troubleshooting

### Technique Not Found

```python
# Error: Technique 'my_technique' not found

# Solution: Register technique in shop
shop.techniques["my_technique"] = create_my_technique()
```

### Import Errors

```python
# Error: Cannot import technique

# Solution: Add to __init__.py
__all__ = ["MyTechnique", "create_my_technique"]
```

### Configuration Errors

```python
# Error: Invalid configuration

# Solution: Use Pydantic validation
class MyTechniqueConfig(BaseModel):
    param: int = Field(ge=1)  # Must be >= 1
```

## Further Reading

- **[Technique Catalog](catalog.md)** - All built-in techniques
- **[Developer Guide](../extending/developer-guide.md)** - Development setup
- **[Testing Guide](../extending/testing-guide.md)** - Testing strategies
- **[Code Style](../extending/code-style.md)** - Coding standards

---

**Previous**: [Infrastructure Techniques](infrastructure.md) | **Next**: [MCP Server Setup](../mcp/server-setup.md)
