# Caching Technique

Multi-level caching strategies

## Subtechniques

### embedding_cache
Embedding caching

**Default Implementations:**
- `lru` - Lru implementation
- `ttl` - Ttl implementation

**Provider Implementations:**
- To be added via MCP servers

### retrieval_cache
Retrieval result caching

**Default Implementations:**
- `query_hash` - Query Hash implementation
- `semantic` - Semantic implementation

**Provider Implementations:**
- To be added via MCP servers

### semantic_cache
Semantic similarity caching

**Default Implementations:**
- `similarity_threshold` - Similarity Threshold implementation

**Provider Implementations:**
- To be added via MCP servers

### query_cache
Query caching

**Default Implementations:**
- `exact_match` - Exact Match implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.caching import CachingTechnique

technique = CachingTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
