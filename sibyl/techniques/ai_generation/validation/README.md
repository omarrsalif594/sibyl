# Validation Technique

Quality validation and control

## Subtechniques

### validator_composition
Validator composition patterns

**Default Implementations:**
- `composite` - Composite implementation
- `first_pass` - First Pass implementation
- `single` - Single implementation

**Provider Implementations:**
- To be added via MCP servers

### retry_strategy
Retry and backoff strategies

**Default Implementations:**
- `exponential_backoff` - Exponential Backoff implementation
- `fixed_retry` - Fixed Retry implementation
- `no_retry` - No Retry implementation

**Provider Implementations:**
- To be added via MCP servers

### quality_scoring
Quality scoring methods

**Default Implementations:**
- `rule_based` - Rule Based implementation
- `threshold_based` - Threshold Based implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.validation import ValidationTechnique

technique = ValidationTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
