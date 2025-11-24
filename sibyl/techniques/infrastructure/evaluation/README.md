# Evaluation Technique

Response evaluation and quality metrics

## Subtechniques

### faithfulness
Faithfulness evaluation

**Default Implementations:**
- `context_check` - Context Check implementation
- `source_attribution` - Source Attribution implementation

**Provider Implementations:**
- To be added via MCP servers

### relevance
Relevance scoring

**Default Implementations:**
- `semantic_similarity` - Semantic Similarity implementation
- `keyword_match` - Keyword Match implementation

**Provider Implementations:**
- To be added via MCP servers

### groundedness
Groundedness verification

**Default Implementations:**
- `fact_check` - Fact Check implementation
- `hallucination_detect` - Hallucination Detect implementation

**Provider Implementations:**
- To be added via MCP servers

### completeness
Completeness assessment

**Default Implementations:**
- `coverage_check` - Coverage Check implementation

**Provider Implementations:**
- To be added via MCP servers

### coherence
Coherence evaluation

**Default Implementations:**
- `flow_check` - Flow Check implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.evaluation import EvaluationTechnique

technique = EvaluationTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
