# Custom Technique Example: Simple Reranker

This example demonstrates how to create a custom technique in Sibyl.

## Overview

The `SimpleRerankingTechnique` is a custom technique that provides two reranking strategies:

1. **Score-based reranking**: Filters results by minimum score and sorts by relevance
2. **Diversity reranking**: Maximizes diversity in top results by penalizing similar consecutive items

## Files

- `simple_reranker.py` - Custom technique implementation
- `workspace.yaml` - Workspace configuration using the custom technique
- `README.md` - This file
- `run_example.py` - Standalone example demonstrating usage

## Installation

No additional dependencies required beyond Sibyl's core dependencies.

## Usage

### 1. Register the Technique

Before using the technique, register it with Sibyl:

```python
from sibyl.techniques.registry import register_technique

register_technique(
    "simple_reranking",
    "examples.extensions.custom_technique.simple_reranker.SimpleRerankingTechnique"
)
```

Or use the provided helper:

```python
from examples.extensions.custom_technique.simple_reranker import register
register()
```

### 2. Use in Code

```python
from sibyl.techniques.registry import get_technique

# Get technique instance
reranker = get_technique("simple_reranking")

# Prepare search results
results = [
    {"text": "Python is a great programming language", "score": 0.92},
    {"text": "Python is excellent for data science", "score": 0.88},
    {"text": "Java is a statically typed language", "score": 0.65},
    {"text": "JavaScript runs in browsers", "score": 0.58},
]

# Rerank with score-based strategy
reranked = reranker.execute(
    input_data=results,
    subtechnique="score_based",
    config={"min_score": 0.8, "max_results": 5}
)

print(f"Reranked results: {len(reranked)} items")
for item in reranked:
    print(f"  - {item['text'][:50]}... (score: {item['score']})")
```

### 3. Use in Workspace

Configure in `workspace.yaml`:

```yaml
shops:
  rag:
    techniques:
      reranker: "simple_reranking:score_based"
    config:
      min_score: 0.75
      max_results: 5
```

Then use in pipelines:

```yaml
pipelines:
  search_pipeline:
    shop: "rag"
    steps:
      - use: "rag.retriever"
        config:
          top_k: 20
      - use: "rag.reranker"
        config:
          min_score: 0.8
```

## Running the Example

Run the standalone example:

```bash
# From the repository root
python examples/extensions/custom_technique/run_example.py
```

This will:
1. Register the custom technique
2. Create sample search results
3. Demonstrate both reranking strategies
4. Show configuration options

## Extending the Example

### Add a New Subtechnique

Create a new subtechnique class:

```python
class MyCustomReranker(BaseSubtechnique):
    @property
    def name(self) -> str:
        return "my_custom"

    @property
    def description(self) -> str:
        return "My custom reranking logic"

    def execute(self, input_data, config):
        # Your reranking logic here
        return reranked_results

    def get_config(self):
        return {"my_param": "default_value"}

    def validate_config(self, config):
        # Validate your config
        return True
```

Register it with the technique:

```python
technique = SimpleRerankingTechnique()
technique.register_subtechnique(MyCustomReranker())
```

### Customize Configuration

Override configuration at different levels:

```python
# Default config (from technique)
default_config = reranker.get_config()

# Override in execute call
reranked = reranker.execute(
    input_data=results,
    subtechnique="score_based",
    config={**default_config, "min_score": 0.9}  # Override specific values
)
```

## Testing

Run tests for the custom technique:

```python
import pytest
from examples.extensions.custom_technique.simple_reranker import (
    SimpleRerankingTechnique
)

def test_score_based_reranking():
    technique = SimpleRerankingTechnique()

    results = [
        {"text": "High score", "score": 0.9},
        {"text": "Low score", "score": 0.5},
    ]

    reranked = technique.execute(
        input_data=results,
        subtechnique="score_based",
        config={"min_score": 0.7, "max_results": 10}
    )

    assert len(reranked) == 1
    assert reranked[0]["score"] == 0.9

def test_diversity_reranking():
    technique = SimpleRerankingTechnique()

    results = [
        {"text": "Python programming", "score": 0.9},
        {"text": "Python coding", "score": 0.85},  # Similar to first
        {"text": "Java development", "score": 0.8},  # Different topic
    ]

    reranked = technique.execute(
        input_data=results,
        subtechnique="diversity",
        config={"diversity_weight": 0.5, "max_results": 3}
    )

    # Should prefer diverse results
    assert len(reranked) == 3
    # Java should rank higher due to diversity despite lower score
    assert any("Java" in r["text"] for r in reranked[:2])

def test_config_validation():
    technique = SimpleRerankingTechnique()

    with pytest.raises(ValueError):
        technique.execute(
            input_data=[],
            subtechnique="score_based",
            config={"min_score": 1.5}  # Invalid: > 1.0
        )
```

## Architecture Notes

### Design Patterns

1. **Protocol-based**: Implements `BaseTechnique` and `BaseSubtechnique` protocols
2. **Strategy pattern**: Multiple subtechniques for different reranking strategies
3. **Configuration cascade**: Config merging from defaults to overrides
4. **Lazy loading**: Technique loaded on first use via registry

### Extension Points

- Add new subtechniques via `register_subtechnique()`
- Override configuration at technique or subtechnique level
- Customize validation logic in `validate_config()`
- Load configuration from files via `load_config()`

## Related Documentation

- [Custom Techniques Guide](../../../docs/extending/custom_techniques.md)
- [Extension Points Overview](../../../docs/extending/overview.md)
- [Technique Registry](../../../sibyl/techniques/registry.py)

## Next Steps

1. Study the implementation in `simple_reranker.py`
2. Run the example to see it in action
3. Create your own custom technique
4. Share your technique with the community
