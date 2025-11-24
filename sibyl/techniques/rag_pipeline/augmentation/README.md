# Augmentation Technique

Context augmentation and enrichment

## Subtechniques

### metadata_injection
Metadata injection strategies

**Default Implementations:**
- `schema_metadata` - Schema Metadata implementation
- `source_metadata` - Source Metadata implementation

**Provider Implementations:**
- To be added via MCP servers

### citation_injection
Citation injection methods

**Default Implementations:**
- `inline_citations` - Inline Citations implementation
- `footnotes` - Footnotes implementation

**Provider Implementations:**
- To be added via MCP servers

### cross_reference
Cross-referencing strategies

**Default Implementations:**
- `entity_links` - Entity Links implementation
- `doc_links` - Doc Links implementation

**Provider Implementations:**
- To be added via MCP servers

### temporal_context
Temporal context injection

**Default Implementations:**
- `timestamp` - Timestamp implementation
- `recency` - Recency implementation

**Provider Implementations:**
- To be added via MCP servers

### entity_linking
Entity linking approaches

**Default Implementations:**
- `spacy` - Spacy implementation
- `llm` - Llm implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.augmentation import AugmentationTechnique

technique = AugmentationTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
