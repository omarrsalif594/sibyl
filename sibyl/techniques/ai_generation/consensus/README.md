# Consensus Technique

Multi-agent consensus and voting mechanisms

## Subtechniques

### quorum_voting
Quorum-based voting strategies

**Default Implementations:**
- `five_agent` - Five Agent implementation
- `three_agent` - Three Agent implementation
- `single_agent` - Single Agent implementation

**Provider Implementations:**
- To be added via MCP servers

### weighted_voting
Confidence and role-weighted voting

**Default Implementations:**
- `confidence_weighted` - Confidence Weighted implementation
- `role_weighted` - Role Weighted implementation

**Provider Implementations:**
- To be added via MCP servers

### hybrid_consensus
Hybrid voting and heuristic approaches

**Default Implementations:**
- `voting_heuristic_mix` - Voting Heuristic Mix implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.consensus import ConsensusTechnique

technique = ConsensusTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
