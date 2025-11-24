# MCP Integration Overview

Learn how to use Sibyl as a Model Context Protocol (MCP) server to expose AI capabilities to Claude Desktop and other MCP clients.

## What is MCP?

The Model Context Protocol (MCP) is an open protocol developed by Anthropic that enables AI assistants to securely connect to external tools and data sources.

**Key Benefits**:
- **Standardized Interface**: One protocol for all integrations
- **Security**: Controlled tool exposure
- **Flexibility**: Works with any MCP-compatible client
- **Simplicity**: Easy to configure and use

## Sibyl as an MCP Server

Sibyl can act as an MCP server, exposing its RAG pipelines and AI capabilities as tools that Claude Desktop (or other MCP clients) can use.

```
┌─────────────────────┐
│   Claude Desktop    │
│   (MCP Client)      │
└──────────┬──────────┘
           │ MCP Protocol
           ↓
┌─────────────────────┐
│   Sibyl MCP Server  │
│   - search_docs     │
│   - index_docs      │
│   - custom_tools    │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│   Your Data         │
│   - Documents       │
│   - Vector Store    │
│   - Databases       │
└─────────────────────┘
```

## Quick Start

### 1. Configure Workspace

Add MCP configuration to your workspace:

```yaml
# config/workspaces/my_workspace.yaml
name: my_docs_workspace

providers:
  llm:
    primary:
      kind: openai
      model: gpt-4

  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

  vector_store:
    docs:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"

pipelines:
  index_documents:
    shop: rag
    steps:
      - use: rag.chunking
      - use: rag.embedding
      - use: data.store_vectors

  search_documents:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: rag.reranking
      - use: ai_generation.generation

# MCP Configuration
mcp:
  enabled: true
  transport: stdio              # stdio for Claude Desktop
  tools:
    - name: search_documents
      description: "Search indexed documents and answer questions"
      pipeline: search_documents
      parameters:
        query:
          type: string
          description: "Question to answer"
          required: true
        top_k:
          type: integer
          description: "Number of results"
          default: 3
```

### 2. Start MCP Server

```bash
# Start MCP server in stdio mode
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

### 3. Configure Claude Desktop

Add to Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/path/to/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/path/to/sibyl/config/workspaces/my_workspace.yaml"
      ]
    }
  }
}
```

### 4. Use in Claude Desktop

Restart Claude Desktop. You'll see Sibyl's tools available:

```
User: Use the search_documents tool to find information about machine learning

Claude: I'll search your documents for information about machine learning.
[Uses search_documents tool]

Based on your documents, machine learning is...
```

## MCP Features

### Supported Transports

#### stdio (Standard Input/Output)

For desktop applications like Claude Desktop.

```yaml
mcp:
  transport: stdio
```

**Start Server**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

#### HTTP

For web integrations and REST APIs.

```yaml
mcp:
  transport: http
  port: 8000
  host: "0.0.0.0"
```

**Start Server**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml \
  --transport http \
  --port 8000
```

**Test**:
```bash
curl http://localhost:8000/mcp/tools
```

### Tool Exposure

Expose pipelines as MCP tools:

```yaml
mcp:
  tools:
    # Simple tool
    - name: search_documents
      description: "Search documents"
      pipeline: qa_over_docs
      parameters:
        query:
          type: string
          required: true

    # Tool with multiple parameters
    - name: advanced_search
      description: "Advanced document search with filters"
      pipeline: advanced_qa
      parameters:
        query:
          type: string
          description: "Search query"
          required: true
        top_k:
          type: integer
          description: "Number of results"
          default: 5
          minimum: 1
          maximum: 20
        date_from:
          type: string
          description: "Filter by date (YYYY-MM-DD)"
          required: false
        category:
          type: string
          description: "Document category"
          enum: ["technical", "business", "general"]

    # Tool with complex parameters
    - name: multi_query_search
      description: "Search with multiple queries"
      pipeline: multi_query_pipeline
      parameters:
        queries:
          type: array
          description: "List of search queries"
          items:
            type: string
          minItems: 1
          maxItems: 5
```

### Tool Discovery

MCP clients can discover available tools:

```bash
# List available tools
sibyl-mcp --workspace config/workspaces/my_workspace.yaml list-tools

# Output:
# Available tools:
#  - search_documents: Search indexed documents
#  - index_documents: Index new documents
#  - advanced_search: Advanced search with filters
```

### Tool Execution

When a tool is called:

1. MCP client sends tool request
2. Sibyl validates parameters
3. Sibyl executes mapped pipeline
4. Results returned to MCP client

## Use Cases

### Document Q&A

```yaml
mcp:
  tools:
    - name: qa_documents
      description: "Answer questions about your documents"
      pipeline: qa_pipeline
      parameters:
        question:
          type: string
          description: "Your question"
          required: true
```

**Usage in Claude**:
> "Use qa_documents to answer: What are the key features of our product?"

### Code Analysis

```yaml
mcp:
  tools:
    - name: analyze_code
      description: "Analyze code and answer questions"
      pipeline: code_analysis_pipeline
      parameters:
        query:
          type: string
          description: "Question about the code"
          required: true
        language:
          type: string
          description: "Programming language"
          enum: ["python", "javascript", "java"]
```

### Data Retrieval

```yaml
mcp:
  tools:
    - name: get_customer_data
      description: "Retrieve customer information"
      pipeline: customer_data_pipeline
      parameters:
        customer_id:
          type: string
          description: "Customer ID"
          required: true
        fields:
          type: array
          description: "Fields to retrieve"
          items:
            type: string
```

### Multi-Step Workflows

```yaml
mcp:
  tools:
    - name: research_topic
      description: "Comprehensive topic research"
      pipeline: research_workflow
      parameters:
        topic:
          type: string
          description: "Research topic"
          required: true
        depth:
          type: string
          description: "Research depth"
          enum: ["quick", "standard", "deep"]
          default: "standard"
```

## Advanced Configuration

### Multiple Workspaces

Run multiple MCP servers for different domains:

```bash
# Documentation server
sibyl-mcp \
  --workspace config/workspaces/docs_workspace.yaml \
  --port 8000

# Code analysis server
sibyl-mcp \
  --workspace config/workspaces/code_workspace.yaml \
  --port 8001

# Customer data server
sibyl-mcp \
  --workspace config/workspaces/customer_workspace.yaml \
  --port 8002
```

Configure in Claude Desktop:

```json
{
  "mcpServers": {
    "docs": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/docs_workspace.yaml"]
    },
    "code": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/code_workspace.yaml"]
    },
    "customer": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/customer_workspace.yaml"]
    }
  }
}
```

### Authentication

Add authentication to HTTP transport:

```yaml
mcp:
  transport: http
  port: 8000
  authentication:
    type: api_key
    header: X-API-Key
    keys:
      - "${API_KEY_1}"
      - "${API_KEY_2}"
```

### Rate Limiting

```yaml
mcp:
  transport: http
  rate_limiting:
    enabled: true
    requests_per_minute: 60
    burst: 10
```

### CORS Configuration

For web integrations:

```yaml
mcp:
  transport: http
  cors:
    enabled: true
    origins:
      - "http://localhost:3000"
      - "https://myapp.com"
    methods: ["GET", "POST"]
```

## Monitoring and Observability

### Logging

```yaml
mcp:
  logging:
    level: INFO
    format: json
    log_requests: true
    log_responses: false       # Don't log full responses (privacy)
```

### Metrics

```yaml
mcp:
  metrics:
    enabled: true
    port: 9090
    path: /metrics
```

**Available Metrics**:
- `sibyl_mcp_tool_calls_total` - Total tool calls
- `sibyl_mcp_tool_duration_seconds` - Tool execution time
- `sibyl_mcp_tool_errors_total` - Tool errors
- `sibyl_mcp_pipeline_duration_seconds` - Pipeline execution time

### Health Checks

```yaml
mcp:
  health:
    enabled: true
    port: 8001
    path: /health
```

**Check Health**:
```bash
curl http://localhost:8001/health

# Response:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "workspace": "my_workspace",
#   "tools": 3,
#   "uptime_seconds": 3600
# }
```

## Troubleshooting

### MCP Server Won't Start

```bash
# Check workspace validity
sibyl workspace validate config/workspaces/my_workspace.yaml

# Check MCP configuration
sibyl-mcp --workspace config/workspaces/my_workspace.yaml --validate

# Start with debug logging
export SIBYL_LOG_LEVEL=DEBUG
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

### Claude Desktop Can't Connect

**Check Configuration Path**:
```bash
# Verify paths are absolute
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Check Server Process**:
```bash
# On macOS
ps aux | grep sibyl-mcp

# Check logs
tail -f ~/.sibyl/logs/mcp_server.log
```

**Common Issues**:
1. ❌ Relative paths in config → Use absolute paths
2. ❌ Virtual environment not activated → Use full path to `sibyl-mcp`
3. ❌ Missing environment variables → Ensure `.env` loaded
4. ❌ Wrong transport → Use `stdio` for Claude Desktop

### Tools Not Appearing

**Verify Tool Configuration**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml list-tools
```

**Check Logs**:
```bash
# Enable debug logging
export SIBYL_LOG_LEVEL=DEBUG
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

### Tool Execution Fails

**Check Pipeline**:
```bash
# Test pipeline directly
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline search_documents \
  --param query="test"
```

**Check Parameters**:
```yaml
# Ensure parameter types match
parameters:
  query:
    type: string      # Not integer!
    required: true
```

## Security Best Practices

### 1. Limit Tool Exposure

Only expose necessary tools:

```yaml
mcp:
  tools:
    - name: search_documents  # Safe: read-only
      pipeline: search
    # Don't expose:
    # - delete_all_data  # Dangerous!
    # - update_credentials  # Dangerous!
```

### 2. Validate Inputs

Add input validation:

```yaml
mcp:
  tools:
    - name: search_documents
      parameters:
        query:
          type: string
          minLength: 1
          maxLength: 500       # Prevent very long inputs
          pattern: "^[a-zA-Z0-9 ]+$"  # Alphanumeric only
```

### 3. Enable Authentication

For HTTP transport:

```yaml
mcp:
  transport: http
  authentication:
    type: api_key
    header: X-API-Key
```

### 4. Use HTTPS

In production:

```yaml
mcp:
  transport: http
  tls:
    enabled: true
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
```

### 5. Rate Limiting

Prevent abuse:

```yaml
mcp:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
```

## Examples

### Complete MCP Workspace

See [complete example workspace](../workspaces/configuration.md#mcp-configuration).

### Integration with Claude Desktop

See [Client Integration Guide](client-integration.md).

### Custom Tool Development

See [Tool Exposure Guide](tool-exposure.md).

### REST API Usage

See [REST API Guide](rest-api.md).

## Further Reading

- **[Server Setup](server-setup.md)** - Detailed server configuration
- **[Client Integration](client-integration.md)** - Integrate with MCP clients
- **[Tool Exposure](tool-exposure.md)** - Expose custom tools
- **[REST API](rest-api.md)** - HTTP/REST API usage
- **[MCP Specification](https://modelcontextprotocol.io/)** - Official MCP docs

---

**Previous**: [Techniques](../techniques/catalog.md) | **Next**: [Server Setup](server-setup.md)
