# Shared MCP Infrastructure for Sibyl Examples

This directory contains shared infrastructure for running Model Context Protocol (MCP) servers used across Sibyl examples.

## Quick Start

### Option 1: Docker Compose (Recommended)

Run all containerized MCPs at once:

```bash
cd examples/shared/mcp
docker-compose up -d
```

This starts:
- **Qdrant** on port 6333 (vector database)
- **Neo4j** on ports 7474 (HTTP) and 7687 (Bolt) (graph database)
- **PostgreSQL** on port 5432 (relational database)

Check status:
```bash
docker-compose ps
```

Stop services:
```bash
docker-compose down
```

Stop and remove data:
```bash
docker-compose down -v
```

### Option 2: Individual Setup

If you only need specific MCPs, see [mcp_requirements.md](mcp_requirements.md) for per-MCP setup instructions.

## What's Included

### docker-compose.yaml
Orchestrates containerized MCP servers:
- Qdrant: Vector store for RAG examples
- Neo4j: Graph database for Graphiti (knowledge graph examples)
- PostgreSQL: Optional relational database for custom scenarios

### mcp_requirements.md
Comprehensive guide to all MCPs used in examples:
- Which examples require which MCPs
- Setup instructions for each MCP
- Configuration templates
- Troubleshooting tips

### mcp_configs/ (Directory)
Example configuration snippets for workspace.yaml files showing how to connect to each MCP.

## Prerequisites

- **Docker**: For containerized MCPs (Docker Compose option)
- **Python 3.11+**: For Sibyl and examples
- **API Keys** (optional): For Brave Search, GitHub MCPs

## Environment Variables

Create a `.env` file in this directory or export these variables:

```bash
# Optional: For Brave Search MCP
export BRAVE_API_KEY=your-brave-api-key

# Optional: For GitHub MCP
export GITHUB_TOKEN=your-github-token

# Neo4j (if using Graphiti)
export NEO4J_PASSWORD=sibyl-examples-password
```

## Verifying Setup

After starting services, verify they're accessible:

### Qdrant
```bash
curl http://localhost:6333/health
# Expected: {"title":"qdrant - vector search engine","version":"..."}
```

### Neo4j
```bash
curl http://localhost:7474
# Expected: Neo4j browser interface
```

### PostgreSQL
```bash
psql -h localhost -U sibyl -d sibyl_examples
# Password: sibyl-examples-password
```

## Usage in Examples

Once MCPs are running, configure them in your workspace.yaml:

```yaml
mcps:
  qdrant:
    enabled: true
    host: localhost
    port: 6333
    collection_name: my_documents

  graphiti:
    enabled: true
    neo4j_uri: bolt://localhost:7687
    neo4j_user: neo4j
    neo4j_password: ${NEO4J_PASSWORD}
```

See company-specific READMEs for detailed configuration examples.

## Troubleshooting

### Port Conflicts

If ports are already in use, modify `docker-compose.yaml`:

```yaml
ports:
  - "6334:6333"  # Map to different host port
```

### Connection Refused

1. Check services are running: `docker-compose ps`
2. Check logs: `docker-compose logs <service-name>`
3. Verify firewall settings
4. Ensure Docker daemon is running

### Slow Performance

- **Qdrant**: Increase memory limit in docker-compose.yaml
- **Neo4j**: Add memory configuration to environment variables
- **PostgreSQL**: Tune shared_buffers and work_mem

See [mcp_requirements.md](mcp_requirements.md) for more troubleshooting tips.

## Development Mode

For development, you can run services with debug logging:

```bash
docker-compose up  # Without -d to see logs in terminal
```

Or view logs for a specific service:
```bash
docker-compose logs -f qdrant
```

## Production Considerations

These configurations are for **local development and examples only**. For production:

1. Change default passwords
2. Enable authentication and SSL/TLS
3. Configure proper volume mounts for persistence
4. Set resource limits (CPU, memory)
5. Use managed services (e.g., Qdrant Cloud, Neo4j Aura)

## Next Steps

1. Start the services with `docker-compose up -d`
2. Choose an example company from `examples/companies/`
3. Follow the company's README for specific setup
4. Run example scenarios or smoke tests

## Related Documentation

- [MCP Requirements Guide](mcp_requirements.md) - Detailed MCP info
- [Sibyl MCP Integration](../../../docs/mcp/INDEX.md) - Core MCP docs
- [Examples Index](../../../docs/examples/INDEX.md) - All examples
- [MCP Troubleshooting](../../../docs/examples/MCP_GUIDE.md) - Comprehensive guide
