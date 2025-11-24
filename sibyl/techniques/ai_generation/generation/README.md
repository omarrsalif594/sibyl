# Generation Technique

Response generation strategies

## Subtechniques

### basic_generation
Basic generation methods

**Default Implementations:**
- `prompt_based` - Prompt Based implementation
- `template` - Template implementation

**Provider Implementations:**
- To be added via MCP servers

### chain_of_thought
Chain of thought reasoning

**Default Implementations:**
- `step_by_step` - Step By Step implementation
- `reasoning` - Reasoning implementation

**Provider Implementations:**
- To be added via MCP servers

### react
ReAct pattern implementation

**Default Implementations:**
- `react_pattern` - React Pattern implementation
- `tool_use` - Tool Use implementation

**Provider Implementations:**
- To be added via MCP servers

### tree_of_thought
Tree of thought exploration

**Default Implementations:**
- `tot_exploration` - Tot Exploration implementation

**Provider Implementations:**
- To be added via MCP servers

### self_consistency
Self-consistency methods

**Default Implementations:**
- `multi_path` - Multi Path implementation
- `voting` - Voting implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.generation import GenerationTechnique

technique = GenerationTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
