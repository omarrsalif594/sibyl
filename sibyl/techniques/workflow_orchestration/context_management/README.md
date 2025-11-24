# ContextManagement Technique

Context window and memory management

## Subtechniques

### rotation_strategy
Context rotation strategies

**Default Implementations:**
- `threshold_based` - Threshold Based implementation
- `token_based` - Token Based implementation
- `no_rotation` - No Rotation implementation

**Provider Implementations:**
- To be added via MCP servers

### summarization
Context summarization

**Default Implementations:**
- `extractive` - Extractive implementation
- `abstractive_simple` - Abstractive Simple implementation
- `no_summarize` - No Summarize implementation

**Provider Implementations:**
- To be added via MCP servers

### compression
Context compression techniques

**Default Implementations:**
- `entity_compression` - Entity Compression implementation
- `gist` - Gist implementation
- `no_compression` - No Compression implementation

**Provider Implementations:**
- To be added via MCP servers

### prioritization
Context prioritization

**Default Implementations:**
- `recency` - Recency implementation
- `relevance` - Relevance implementation
- `mixed` - Mixed implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.context_management import ContextManagementTechnique

technique = ContextManagementTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
