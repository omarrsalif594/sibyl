# MCP Requirements for Sibyl Examples

This document lists the Model Context Protocol (MCP) servers required for each example company and scenario.

## Overview

Sibyl examples use MCPs to provide external capabilities like file system access, web browsing, databases, and specialized tools. Not all examples require all MCPs - this guide helps you set up only what you need.

## Quick Reference Table

| Company | Scenario | Required MCPs | Optional MCPs | Setup Complexity |
|---------|----------|---------------|---------------|------------------|
| RiverBank Finance | Compliance Audit | filesystem, sqlite | brave-search, github | Low |
| RiverBank Finance | Transaction Analysis | filesystem, sqlite, graphiti | - | Medium |
| Vertex Foundry | Experiment Tracking | filesystem, sqlite | github | Low |
| Vertex Foundry | Model Analysis | filesystem, sqlite | brave-search | Low |
| Northwind Analytics | RAG Pipeline | filesystem, qdrant | brave-search | Medium |
| Acme Shop | Sales Forecasting | filesystem, sqlite | - | Low |
| TechVentures | Code Analysis | filesystem, github | brave-search | Medium |

## MCP Detailed Setup

### Core MCPs (Most Examples)

#### 1. Filesystem MCP
**Purpose**: Local file access for reading data, writing outputs
**Required by**: All examples
**Setup**: Built into Sibyl - no additional setup required
**Configuration**:
```yaml
mcps:
  filesystem:
    enabled: true
    root_path: ./examples/companies/<company-name>
```

#### 2. SQLite MCP
**Purpose**: Query structured data, transaction history, relational data
**Required by**: RiverBank Finance, Vertex Foundry, Acme Shop
**Setup**: Built into Sibyl - no additional setup required
**Configuration**:
```yaml
mcps:
  sqlite:
    enabled: true
    databases:
      - path: ./examples/companies/<company>/data/<database>.db
        alias: main
```

### Search & Web MCPs

#### 3. Brave Search MCP
**Purpose**: Web search for research, documentation lookup
**Required by**: Optional for most examples
**Setup**:
1. Get API key from https://brave.com/search/api/
2. Set environment variable: `BRAVE_API_KEY=<your-key>`
**Configuration**:
```yaml
mcps:
  brave_search:
    enabled: true
    api_key: ${BRAVE_API_KEY}
```
**Documentation**: https://docs.brave.com/search-api/

### Vector Store MCPs

#### 4. Qdrant MCP
**Purpose**: Vector database for RAG, semantic search
**Required by**: Northwind Analytics (RAG scenarios)
**Setup**:
- **Option A (Docker)**:
  ```bash
  docker run -p 6333:6333 qdrant/qdrant
  ```
- **Option B (Local)**:
  ```bash
  pip install qdrant-client
  # Runs in-memory or persistent mode
  ```
**Configuration**:
```yaml
mcps:
  qdrant:
    enabled: true
    host: localhost
    port: 6333
    collection_name: documents
```
**Documentation**: https://qdrant.tech/documentation/quick-start/

#### 5. Graphiti MCP
**Purpose**: Knowledge graph construction, entity relationships
**Required by**: RiverBank Finance (Transaction Analysis)
**Setup**:
```bash
# Clone and set up Graphiti MCP server
git clone https://github.com/anthropics/graphiti-mcp
cd graphiti-mcp
pip install -e .
```
**Configuration**:
```yaml
mcps:
  graphiti:
    enabled: true
    neo4j_uri: bolt://localhost:7687
    neo4j_user: neo4j
    neo4j_password: ${NEO4J_PASSWORD}
```
**Documentation**: https://github.com/anthropics/graphiti-mcp

### Code & Development MCPs

#### 6. GitHub MCP
**Purpose**: Repository access, code search, issue tracking
**Required by**: TechVentures, optional for Vertex Foundry
**Setup**:
1. Create GitHub personal access token
2. Set environment variable: `GITHUB_TOKEN=<your-token>`
**Configuration**:
```yaml
mcps:
  github:
    enabled: true
    token: ${GITHUB_TOKEN}
    repositories:
      - owner/repo-name
```
**Documentation**: https://github.com/modelcontextprotocol/servers/tree/main/src/github

## Company-Specific Requirements

### RiverBank Finance
**Mission**: Banking compliance, transaction monitoring, regulatory reporting

**Scenario 1: Compliance Audit**
- Required: filesystem, sqlite
- Optional: brave-search (for regulation lookup), github (for code audit)
- Data: Transactions database, compliance documents, interest calculation code

**Scenario 2: Transaction Analysis with Graph**
- Required: filesystem, sqlite, graphiti
- Optional: None
- Data: Transaction network, entity relationships
- Note: Requires Neo4j for Graphiti backend

### Vertex Foundry
**Mission**: ML experiment tracking, model analysis

**Scenario 1: Experiment Tracking**
- Required: filesystem, sqlite
- Optional: github (for code versioning)
- Data: Experiment configs, run logs, model artifacts

**Scenario 2: Model Performance Analysis**
- Required: filesystem, sqlite
- Optional: brave-search (for ML best practices)
- Data: Training logs, evaluation metrics

### Northwind Analytics
**Mission**: Business intelligence, RAG-based document QA

**Scenario: Document QA Pipeline**
- Required: filesystem, qdrant
- Optional: brave-search (for external data enrichment)
- Data: Product catalogs, sales reports, customer data
- Note: Qdrant can run in Docker or local mode

### Acme Shop
**Mission**: Retail analytics, sales forecasting

**Scenario: Sales Forecasting**
- Required: filesystem, sqlite
- Optional: None
- Data: Historical sales, inventory, customer transactions

### TechVentures
**Mission**: Code analysis, technical due diligence

**Scenario: Codebase Analysis**
- Required: filesystem, github
- Optional: brave-search (for library documentation)
- Data: Source code repositories, dependency graphs

## Testing Without MCPs

For quick testing or CI/CD, many examples can run with mocked MCPs:

```yaml
mcps:
  mock_mode: true  # Uses in-memory mocks for all MCPs
```

This allows you to:
- Test example structure without external dependencies
- Run smoke tests in CI
- Develop scenarios before setting up full infrastructure

However, mocked MCPs return synthetic data and won't demonstrate real capabilities.

## Docker Compose Setup

For convenience, we provide a Docker Compose file for MCPs that can run in containers. See `docker-compose.yaml` in this directory.

**Services included:**
- Qdrant (vector store)
- Neo4j (graph database for Graphiti)
- PostgreSQL (optional, for custom scenarios)

**To use:**
```bash
cd examples/shared/mcp
docker-compose up -d
```

## Troubleshooting

### MCP Connection Issues

**Problem**: "Failed to connect to MCP server"
- Check that the MCP server is running (docker ps, process list)
- Verify configuration (host, port, API keys)
- Check firewall/network settings

**Problem**: "Authentication failed"
- Verify API keys and tokens in environment variables
- Check token permissions (GitHub, Brave)
- Ensure credentials are not expired

### Performance Issues

**Problem**: "MCP responses are slow"
- Qdrant: Ensure collection is properly indexed
- Graphiti: Check Neo4j query performance
- SQLite: Add indexes on frequently queried columns

**Problem**: "Out of memory"
- Qdrant: Reduce batch size for vector operations
- Graphiti: Limit graph traversal depth
- SQLite: Use pagination for large result sets

### Data Issues

**Problem**: "No results returned"
- Check that data is properly loaded (run setup scripts)
- Verify file paths in configuration
- Ensure database tables exist and have data

**Problem**: "Stale or incorrect data"
- Re-run data setup scripts
- Clear and rebuild vector indexes
- Reset graph database if needed

## Next Steps

1. Identify which examples you want to run
2. Install only the required MCPs for those examples
3. Follow company-specific setup in each `examples/companies/<company>/README.md`
4. Run smoke tests to verify setup: `pytest examples/companies/<company>/tests/`

## Additional Resources

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [Sibyl MCP Integration Guide](../../../docs/mcp/INDEX.md)
- [Example Workspace Configuration](../../../docs/workspaces/workspace_schema.md)
- [MCP Troubleshooting Guide](../../../docs/examples/MCP_GUIDE.md)
