# Learning Technique

Adaptive learning and pattern discovery

## Subtechniques

### learning_algorithm
Learning algorithm types

**Default Implementations:**
- `pattern_based` - Pattern Based implementation
- `ml_based` - Ml Based implementation
- `rule_based` - Rule Based implementation

**Provider Implementations:**
- To be added via MCP servers

### pattern_discovery
Pattern discovery methods

**Default Implementations:**
- `frequency_based` - Frequency Based implementation
- `correlation` - Correlation implementation

**Provider Implementations:**
- To be added via MCP servers

### feedback_loop
Feedback loop strategies

**Default Implementations:**
- `online` - Online implementation
- `batch` - Batch implementation
- `no_feedback` - No Feedback implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.learning import LearningTechnique

technique = LearningTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
