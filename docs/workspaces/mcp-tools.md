# MCP Tools Configuration

Complete guide to configuring MCP tool exposure in Sibyl workspaces.

## Overview

MCP (Model Context Protocol) tools allow you to expose Sibyl pipelines as callable tools that Claude Desktop and other MCP clients can use. This enables seamless integration of your RAG pipelines, data sources, and custom workflows into AI assistant interfaces.

## Basic MCP Configuration

### Minimal MCP Setup

```yaml
# config/workspaces/my_workspace.yaml
name: my_workspace

providers:
  # ... provider configuration

pipelines:
  search_documents:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

# MCP Configuration
mcp:
  enabled: true
  transport: stdio              # For Claude Desktop
  tools:
    - name: search_documents
      description: "Search indexed documents and answer questions"
      pipeline: search_documents
      parameters:
        query:
          type: string
          description: "Question to answer"
          required: true
```

### Complete MCP Configuration

```yaml
mcp:
  enabled: true
  transport: stdio

  # Server metadata
  server:
    name: "My Sibyl Server"
    version: "1.0.0"
    description: "Custom document search and analysis"

  # Tool exposure
  tools:
    - name: search_documents
      description: "Search and answer questions from documents"
      pipeline: search_documents
      parameters:
        query:
          type: string
          description: "Your question"
          required: true
        top_k:
          type: integer
          description: "Number of results to retrieve"
          default: 5
          minimum: 1
          maximum: 20

  # Logging
  logging:
    level: INFO
    log_requests: true
    log_responses: false

  # Metrics (for HTTP transport)
  metrics:
    enabled: true
    port: 9090
```

## Tool Parameter Types

### String Parameters

```yaml
tools:
  - name: search_tool
    parameters:
      query:
        type: string
        description: "Search query"
        required: true
        minLength: 1
        maxLength: 500
        pattern: "^[a-zA-Z0-9 .,?!-]+$"  # Alphanumeric + punctuation
```

### Integer Parameters

```yaml
tools:
  - name: search_tool
    parameters:
      top_k:
        type: integer
        description: "Number of results"
        default: 5
        minimum: 1
        maximum: 100
```

### Number (Float) Parameters

```yaml
tools:
  - name: search_tool
    parameters:
      threshold:
        type: number
        description: "Similarity threshold"
        default: 0.7
        minimum: 0.0
        maximum: 1.0
```

### Boolean Parameters

```yaml
tools:
  - name: search_tool
    parameters:
      include_metadata:
        type: boolean
        description: "Include document metadata"
        default: true
```

### Enum Parameters

```yaml
tools:
  - name: search_tool
    parameters:
      search_mode:
        type: string
        description: "Search mode to use"
        enum: ["vector", "hybrid", "keyword"]
        default: "hybrid"

      language:
        type: string
        description: "Document language"
        enum: ["en", "fr", "es", "de"]
```

### Array Parameters

```yaml
tools:
  - name: multi_search
    parameters:
      queries:
        type: array
        description: "List of search queries"
        items:
          type: string
        minItems: 1
        maxItems: 5

      document_types:
        type: array
        description: "Document types to search"
        items:
          type: string
          enum: ["pdf", "markdown", "text", "html"]
        default: ["pdf", "markdown"]
```

### Object Parameters

```yaml
tools:
  - name: advanced_search
    parameters:
      filters:
        type: object
        description: "Search filters"
        properties:
          date_from:
            type: string
            description: "Start date (YYYY-MM-DD)"
          date_to:
            type: string
            description: "End date (YYYY-MM-DD)"
          categories:
            type: array
            items:
              type: string
          author:
            type: string
```

## Complete Tool Examples

### Example 1: Simple Document Search

```yaml
mcp:
  tools:
    - name: search_docs
      description: "Search documents and get answers"
      pipeline: qa_pipeline
      parameters:
        question:
          type: string
          description: "Your question"
          required: true
          minLength: 5
          maxLength: 500
```

**Usage in Claude Desktop**:
```
User: Use search_docs to find information about machine learning
Claude: [Calls search_docs with question="machine learning"]
```

### Example 2: Advanced Search with Filters

```yaml
mcp:
  tools:
    - name: advanced_search
      description: "Search with advanced filters and options"
      pipeline: advanced_search_pipeline
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

        search_mode:
          type: string
          description: "Search algorithm to use"
          enum: ["vector", "hybrid", "keyword"]
          default: "hybrid"

        date_from:
          type: string
          description: "Filter by start date (YYYY-MM-DD)"
          required: false
          pattern: "^\\d{4}-\\d{2}-\\d{2}$"

        date_to:
          type: string
          description: "Filter by end date (YYYY-MM-DD)"
          required: false
          pattern: "^\\d{4}-\\d{2}-\\d{2}$"

        categories:
          type: array
          description: "Document categories to search"
          items:
            type: string
            enum: ["technical", "business", "general"]
          default: []

        include_metadata:
          type: boolean
          description: "Include document metadata in results"
          default: false
```

### Example 3: Multi-Query Research

```yaml
mcp:
  tools:
    - name: research_topic
      description: "Perform comprehensive research on a topic"
      pipeline: research_workflow
      parameters:
        topic:
          type: string
          description: "Research topic"
          required: true
          minLength: 3
          maxLength: 200

        depth:
          type: string
          description: "Research depth level"
          enum: ["quick", "standard", "deep"]
          default: "standard"

        subtopics:
          type: array
          description: "Specific subtopics to focus on"
          items:
            type: string
          minItems: 0
          maxItems: 10

        output_format:
          type: string
          description: "Output format"
          enum: ["summary", "detailed", "structured"]
          default: "summary"
```

### Example 4: Code Analysis

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
          enum: ["python", "javascript", "java", "go", "rust"]
          required: false

        file_patterns:
          type: array
          description: "File patterns to include (glob format)"
          items:
            type: string
          default: ["**/*.py"]

        include_tests:
          type: boolean
          description: "Include test files"
          default: false
```

### Example 5: Data Retrieval

```yaml
mcp:
  tools:
    - name: get_customer_info
      description: "Retrieve customer information"
      pipeline: customer_data_pipeline
      parameters:
        customer_id:
          type: string
          description: "Customer ID"
          required: true
          pattern: "^CUST-\\d{6}$"

        fields:
          type: array
          description: "Fields to retrieve"
          items:
            type: string
            enum: ["name", "email", "phone", "address", "orders", "preferences"]
          default: ["name", "email"]

        include_history:
          type: boolean
          description: "Include order history"
          default: false
```

## Pipeline-to-Tool Mapping

### Direct Mapping

```yaml
pipelines:
  search:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

mcp:
  tools:
    - name: search
      pipeline: search           # Direct mapping
      parameters:
        query:
          type: string
          required: true
```

### Parameter Mapping

```yaml
# Pipeline expects 'query' and 'k'
pipelines:
  search:
    parameters:
      query: string
      k: integer
    steps:
      - use: rag.retrieval
        config:
          top_k: ${k}

# MCP tool uses different names
mcp:
  tools:
    - name: search_docs
      pipeline: search
      parameters:
        question:              # Maps to 'query'
          type: string
          required: true
        num_results:           # Maps to 'k'
          type: integer
          default: 5

      parameter_mapping:       # Explicit mapping
        question: query
        num_results: k
```

### Default Parameter Values

```yaml
mcp:
  tools:
    - name: search
      pipeline: search
      parameters:
        query:
          type: string
          required: true

      # Set defaults for pipeline parameters not exposed
      defaults:
        rerank: true
        similarity_threshold: 0.7
        provider: primary
```

## Multiple Tools from Same Pipeline

```yaml
pipelines:
  flexible_search:
    parameters:
      query: string
      mode: string
      top_k: integer
    steps:
      - use: rag.search
        config:
          subtechnique: ${mode}
          top_k: ${top_k}

mcp:
  tools:
    # Quick search tool
    - name: quick_search
      description: "Fast search with fewer results"
      pipeline: flexible_search
      defaults:
        mode: vector
        top_k: 3

    # Deep search tool
    - name: deep_search
      description: "Comprehensive search with more results"
      pipeline: flexible_search
      defaults:
        mode: hybrid
        top_k: 20

    # Custom search tool
    - name: custom_search
      description: "Customizable search"
      pipeline: flexible_search
      parameters:
        query:
          type: string
          required: true
        mode:
          type: string
          enum: ["vector", "hybrid", "keyword"]
        num_results:
          type: integer
          default: 5
      parameter_mapping:
        num_results: top_k
```

## Transport Configuration

### stdio (Claude Desktop)

```yaml
mcp:
  transport: stdio

  # No additional configuration needed
```

**Claude Desktop Config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/path/to/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/path/to/workspace.yaml"
      ]
    }
  }
}
```

### HTTP (REST API)

```yaml
mcp:
  transport: http
  port: 8000
  host: "0.0.0.0"

  # CORS for web clients
  cors:
    enabled: true
    origins:
      - "http://localhost:3000"
      - "https://myapp.com"
    methods: ["GET", "POST"]
    headers: ["Content-Type", "Authorization"]

  # Authentication
  authentication:
    type: api_key
    header: X-API-Key
    keys:
      - "${API_KEY_1}"
      - "${API_KEY_2}"

  # Rate limiting
  rate_limiting:
    enabled: true
    requests_per_minute: 60
    burst: 10

  # TLS (production)
  tls:
    enabled: true
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
```

**Usage**:
```bash
# List tools
curl http://localhost:8000/mcp/tools

# Call tool
curl -X POST http://localhost:8000/mcp/tools/search_docs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"query": "machine learning"}'
```

## Security Best Practices

### 1. Input Validation

```yaml
mcp:
  tools:
    - name: search
      parameters:
        query:
          type: string
          minLength: 1           # Prevent empty
          maxLength: 500         # Prevent abuse
          pattern: "^[a-zA-Z0-9 .,?!-]+$"  # Allowed chars only
```

### 2. Read-Only Tools

```yaml
# Good - expose read-only operations
mcp:
  tools:
    - name: search_docs        # Safe: read-only
    - name: get_info           # Safe: read-only

# Avoid - don't expose destructive operations
# - name: delete_all         # Dangerous!
# - name: update_config      # Dangerous!
```

### 3. Parameter Constraints

```yaml
mcp:
  tools:
    - name: search
      parameters:
        top_k:
          type: integer
          minimum: 1            # Prevent invalid
          maximum: 20           # Prevent resource abuse
```

### 4. Authentication (HTTP)

```yaml
mcp:
  transport: http
  authentication:
    type: api_key
    header: X-API-Key
    keys:
      - "${API_KEY_1}"        # From environment
      - "${API_KEY_2}"
```

### 5. Rate Limiting

```yaml
mcp:
  rate_limiting:
    enabled: true
    requests_per_minute: 60   # Prevent abuse
    burst: 10
    by_key: true              # Per API key
```

## Observability and Monitoring

### Logging

```yaml
mcp:
  logging:
    level: INFO                    # DEBUG, INFO, WARNING, ERROR
    format: json                   # json, text
    log_requests: true             # Log all requests
    log_responses: false           # Don't log full responses (privacy)
    log_errors: true               # Always log errors

    # File logging
    file:
      enabled: true
      path: /var/log/sibyl/mcp.log
      rotation:
        max_bytes: 10485760        # 10MB
        backup_count: 5
```

### Metrics

```yaml
mcp:
  metrics:
    enabled: true
    port: 9090
    path: /metrics

    # Custom labels
    labels:
      environment: production
      service: sibyl-mcp
```

**Available Metrics**:
- `sibyl_mcp_tool_calls_total{tool="search_docs"}` - Total tool calls
- `sibyl_mcp_tool_duration_seconds{tool="search_docs"}` - Tool execution time
- `sibyl_mcp_tool_errors_total{tool="search_docs"}` - Tool errors
- `sibyl_mcp_requests_total{method="POST"}` - HTTP requests (HTTP transport)

### Health Checks

```yaml
mcp:
  health:
    enabled: true
    port: 8001
    path: /health

    # Health check configuration
    checks:
      - name: database
        type: database
        connection: "${DATABASE_URL}"

      - name: vector_store
        type: vector_store
        provider: main

      - name: llm_provider
        type: llm
        provider: primary
```

**Check Health**:
```bash
curl http://localhost:8001/health

# Response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "checks": {
#     "database": "healthy",
#     "vector_store": "healthy",
#     "llm_provider": "healthy"
#   },
#   "uptime_seconds": 3600
# }
```

## Tool Discovery and Documentation

### Auto-Generated Documentation

```yaml
mcp:
  documentation:
    enabled: true
    path: /docs                  # http://localhost:8000/docs

    # OpenAPI/Swagger
    openapi:
      enabled: true
      title: "Sibyl MCP API"
      version: "1.0.0"
      description: "MCP tools for document search and analysis"
```

### Tool Metadata

```yaml
mcp:
  tools:
    - name: search_docs
      description: "Search indexed documents and answer questions"

      # Extended metadata
      metadata:
        category: search
        tags: ["rag", "documents", "qa"]
        version: "1.0.0"
        author: "Your Name"

        # Usage examples
        examples:
          - description: "Basic search"
            parameters:
              query: "What is machine learning?"

          - description: "Advanced search"
            parameters:
              query: "Explain neural networks"
              top_k: 10
              search_mode: "hybrid"

        # Response schema
        response_schema:
          type: object
          properties:
            answer:
              type: string
              description: "Generated answer"
            sources:
              type: array
              description: "Source documents"
              items:
                type: object
                properties:
                  document_id:
                    type: string
                  title:
                    type: string
                  score:
                    type: number
```

## Troubleshooting

### Tool Not Appearing in Claude Desktop

**Check Configuration**:
```bash
# Verify workspace is valid
sibyl workspace validate config/workspaces/my_workspace.yaml

# List available tools
sibyl-mcp --workspace config/workspaces/my_workspace.yaml list-tools
```

**Check Claude Desktop Config**:
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Verify paths are absolute
# Verify sibyl-mcp is in PATH or use full path
```

### Tool Execution Fails

**Test Pipeline Directly**:
```bash
# Test the pipeline that the tool uses
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline search_documents \
  --param query="test"
```

**Check Logs**:
```bash
# Enable debug logging
export SIBYL_LOG_LEVEL=DEBUG
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

### Parameter Validation Errors

```yaml
# Ensure parameter types match
parameters:
  top_k:
    type: integer    # Not string!
    required: true

# Ensure required parameters are provided
# Ensure values meet constraints (min, max, pattern)
```

## Further Reading

- **[MCP Overview](../mcp/overview.md)** - MCP integration overview
- **[Server Setup](../mcp/server-setup.md)** - Detailed server configuration
- **[Client Integration](../mcp/client-integration.md)** - Integrate with MCP clients
- **[Pipeline Configuration](configuration.md)** - Configure pipelines

---

**Previous**: [Shops and Techniques](shops-and-techniques.md) | **Next**: [Best Practices](best-practices.md)
