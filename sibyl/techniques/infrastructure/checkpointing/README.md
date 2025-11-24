# Checkpointing Technique

State checkpointing and recovery

## Subtechniques

### checkpoint_storage
Checkpoint storage backends

**Default Implementations:**
- `file_based` - File Based implementation
- `db_based` - Db Based implementation
- `redis` - Redis implementation

**Provider Implementations:**
- To be added via MCP servers

### resume_strategy
Resume strategies

**Default Implementations:**
- `full_resume` - Full Resume implementation
- `partial_resume` - Partial Resume implementation
- `no_resume` - No Resume implementation

**Provider Implementations:**
- To be added via MCP servers

### state_serialization
State serialization formats

**Default Implementations:**
- `json` - Json implementation
- `pickle` - Pickle implementation
- `msgpack` - Msgpack implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.checkpointing import CheckpointingTechnique

technique = CheckpointingTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
