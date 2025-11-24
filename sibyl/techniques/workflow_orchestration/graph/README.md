# Graph Technique

Graph-based analysis and operations

## Subtechniques

### graph_backend
Graph storage backends

**Default Implementations:**
- `networkx` - Networkx implementation
- `neo4j` - Neo4J implementation
- `igraph` - Igraph implementation

**Provider Implementations:**
- To be added via MCP servers

### analysis_algorithms
Graph analysis algorithms

**Default Implementations:**
- `cycle_detection` - Cycle Detection implementation
- `path_finding` - Path Finding implementation
- `centrality` - Centrality implementation

**Provider Implementations:**
- To be added via MCP servers

### visualization
Graph visualization

**Default Implementations:**
- `graphviz` - Graphviz implementation
- `plotly` - Plotly implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.graph import GraphTechnique

technique = GraphTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.
