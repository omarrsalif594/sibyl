# QueryProcessing Technique

Query transformation and enhancement

## Subtechniques

### query_expansion
Query expansion techniques

**Default Implementations:**
- `synonym` - Synonym implementation
- `embedding` - Embedding implementation
- `no_expansion` - No Expansion implementation

**Provider Implementations:**
- To be added via MCP servers

### query_rewriting
Query rewriting strategies

**Default Implementations:**
- `template` - Template implementation
- `llm` - Llm implementation
- `no_rewrite` - No Rewrite implementation

**Provider Implementations:**
- To be added via MCP servers

### multi_query
Multi-query generation

**Default Implementations:**
- `perspective_variation` - Perspective Variation implementation
- `single` - Single implementation

**Provider Implementations:**
- To be added via MCP servers

### hyde
Hypothetical Document Embeddings

**Default Implementations:**
- `simple_hyde` - Simple Hyde implementation
- `disabled` - Disabled implementation

**Provider Implementations:**
- To be added via MCP servers

### query_decomposition
Query decomposition strategies

**Default Implementations:**
- `recursive` - Recursive implementation
- `no_decomp` - No Decomp implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.query_processing import QueryProcessingTechnique

technique = QueryProcessingTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
