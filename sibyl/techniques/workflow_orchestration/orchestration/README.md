# Orchestration Technique

Workflow orchestration and execution

## Subtechniques

### execution_model
Execution models for workflows

**Default Implementations:**
- `wave_based` - Wave Based implementation
- `sequential` - Sequential implementation
- `dag_based` - Dag Based implementation

**Provider Implementations:**
- To be added via MCP servers

### parallelism
Parallel execution strategies

**Default Implementations:**
- `semaphore` - Semaphore implementation
- `thread_pool` - Thread Pool implementation
- `process_pool` - Process Pool implementation

**Provider Implementations:**
- To be added via MCP servers

### routing
Task routing strategies

**Default Implementations:**
- `expert_routing` - Expert Routing implementation
- `round_robin` - Round Robin implementation
- `load_balanced` - Load Balanced implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.orchestration import OrchestrationTechnique

technique = OrchestrationTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
