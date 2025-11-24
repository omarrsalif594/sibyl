# Search Technique

Search and retrieval mechanisms

## Subtechniques

### vector_search
Vector similarity search

**Default Implementations:**
- `faiss` - Faiss implementation
- `duckdb` - Duckdb implementation
- `pgvector` - Pgvector implementation

**Provider Implementations:**
- To be added via MCP servers

### keyword_search
Keyword-based search

**Default Implementations:**
- `bm25` - Bm25 implementation
- `tf_idf` - Tf Idf implementation

**Provider Implementations:**
- To be added via MCP servers

### hybrid_search
Hybrid search strategies

**Default Implementations:**
- `rrf` - Rrf implementation
- `weighted` - Weighted implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.search import SearchTechnique

technique = SearchTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
