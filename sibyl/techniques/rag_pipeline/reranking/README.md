# Reranking Technique

Result reranking and fusion

## Subtechniques

### cross_encoder
Cross-encoder reranking

**Default Implementations:**
- `sentence_transformer` - Sentence Transformer implementation
- `no_rerank` - No Rerank implementation

**Provider Implementations:**
- To be added via MCP servers

### llm_rerank
LLM-based reranking

**Default Implementations:**
- `prompt_based` - Prompt Based implementation

**Provider Implementations:**
- To be added via MCP servers

### diversity_rerank
Diversity-aware reranking

**Default Implementations:**
- `mmr` - Mmr implementation
- `cluster_based` - Cluster Based implementation

**Provider Implementations:**
- To be added via MCP servers

### bm25_rerank
BM25 reranking

**Default Implementations:**
- `bm25_scorer` - Bm25 Scorer implementation

**Provider Implementations:**
- To be added via MCP servers

### fusion
Result fusion strategies

**Default Implementations:**
- `rrf` - Rrf implementation
- `weighted_fusion` - Weighted Fusion implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.reranking import RerankingTechnique

technique = RerankingTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
