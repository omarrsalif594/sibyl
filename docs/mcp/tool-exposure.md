# MCP Tool Exposure

Complete guide to exposing Sibyl pipelines as MCP tools with advanced configuration patterns.

## Overview

MCP tools are the interface between Claude Desktop (or other MCP clients) and your Sibyl pipelines. This guide covers:

- Tool definition and configuration
- Parameter schemas and validation
- Dynamic tool generation
- Tool versioning and deprecation
- Advanced exposure patterns

## Basic Tool Exposure

### Simple Tool

Expose a pipeline as a tool with minimal configuration:

```yaml
# config/workspaces/my_workspace.yaml
pipelines:
  search_docs:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

mcp:
  enabled: true
  tools:
    - name: search_documents
      description: "Search indexed documents and answer questions"
      pipeline: search_docs
      parameters:
        query:
          type: string
          description: "Your question"
          required: true
```

**Result**: Claude Desktop sees a tool called `search_documents` that accepts a `query` parameter.

### Tool with Multiple Parameters

```yaml
mcp:
  tools:
    - name: advanced_search
      description: "Advanced document search with filters"
      pipeline: advanced_search_pipeline
      parameters:
        query:
          type: string
          description: "Search query"
          required: true
          minLength: 3
          maxLength: 500

        top_k:
          type: integer
          description: "Number of results to return"
          default: 5
          minimum: 1
          maximum: 20

        search_mode:
          type: string
          description: "Search algorithm"
          enum: ["vector", "hybrid", "keyword"]
          default: "hybrid"

        date_from:
          type: string
          description: "Filter by start date (YYYY-MM-DD)"
          pattern: "^\\d{4}-\\d{2}-\\d{2}$"

        categories:
          type: array
          description: "Document categories to search"
          items:
            type: string
            enum: ["technical", "business", "general"]
```

## Parameter Types and Validation

### String Parameters

```yaml
parameters:
  # Basic string
  query:
    type: string
    required: true

  # With length constraints
  title:
    type: string
    minLength: 1
    maxLength: 100

  # With pattern validation
  email:
    type: string
    pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"

  # With enum values
  status:
    type: string
    enum: ["active", "inactive", "pending"]
    default: "active"

  # With format
  date:
    type: string
    format: date              # date, date-time, email, uri, uuid
```

### Numeric Parameters

```yaml
parameters:
  # Integer
  count:
    type: integer
    minimum: 0
    maximum: 100
    default: 10

  # Float/Number
  threshold:
    type: number
    minimum: 0.0
    maximum: 1.0
    exclusiveMinimum: true    # > 0.0 (not >= 0.0)
    default: 0.7

  # Multiple of
  batch_size:
    type: integer
    multipleOf: 10            # Must be 10, 20, 30, etc.
```

### Boolean Parameters

```yaml
parameters:
  include_metadata:
    type: boolean
    description: "Include document metadata in results"
    default: false

  strict_mode:
    type: boolean
    description: "Enable strict validation"
    default: true
```

### Array Parameters

```yaml
parameters:
  # Simple array
  tags:
    type: array
    description: "Document tags"
    items:
      type: string
    minItems: 1
    maxItems: 10

  # Array with enum items
  categories:
    type: array
    items:
      type: string
      enum: ["tech", "business", "general"]
    uniqueItems: true         # No duplicates

  # Array of objects
  filters:
    type: array
    items:
      type: object
      properties:
        field:
          type: string
        operator:
          type: string
          enum: ["eq", "ne", "gt", "lt"]
        value:
          type: string
      required: ["field", "operator", "value"]
```

### Object Parameters

```yaml
parameters:
  # Simple object
  metadata:
    type: object
    description: "Additional metadata"
    properties:
      author:
        type: string
      created_at:
        type: string
        format: date-time
      tags:
        type: array
        items:
          type: string
    required: ["author"]

  # Nested objects
  search_config:
    type: object
    properties:
      retrieval:
        type: object
        properties:
          top_k:
            type: integer
          threshold:
            type: number
      reranking:
        type: object
        properties:
          enabled:
            type: boolean
          model:
            type: string
```

### Conditional Parameters

```yaml
parameters:
  search_type:
    type: string
    enum: ["simple", "advanced"]
    default: "simple"

  # Only required if search_type is "advanced"
  advanced_options:
    type: object
    properties:
      algorithm:
        type: string
      filters:
        type: object
    dependencies:
      - search_type: "advanced"
```

## Parameter Mapping

### Direct Mapping

Pipeline parameters match tool parameters exactly:

```yaml
# Pipeline
pipelines:
  search:
    parameters:
      query: string
      top_k: integer
    steps:
      - use: rag.retrieval
        config:
          top_k: ${top_k}

# Tool (1:1 mapping)
mcp:
  tools:
    - name: search
      pipeline: search
      parameters:
        query:
          type: string
        top_k:
          type: integer
```

### Custom Mapping

Tool parameters map to different pipeline parameters:

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

# Tool uses 'question' and 'num_results'
mcp:
  tools:
    - name: search_docs
      pipeline: search
      parameters:
        question:
          type: string
        num_results:
          type: integer
          default: 5

      # Map tool params to pipeline params
      parameter_mapping:
        question: query
        num_results: k
```

### Default Parameter Values

Set defaults for pipeline parameters not exposed in tool:

```yaml
mcp:
  tools:
    - name: quick_search
      pipeline: flexible_search
      parameters:
        query:
          type: string
          required: true

      # Set hidden defaults
      defaults:
        mode: "vector"          # Fast mode
        top_k: 3                # Fewer results
        rerank: false           # No reranking
        provider: "primary"
```

### Parameter Transformation

Transform parameters before passing to pipeline:

```yaml
mcp:
  tools:
    - name: search
      pipeline: search_pipeline
      parameters:
        query:
          type: string

      # Transform parameters
      parameter_transformations:
        - name: normalize_query
          type: python
          code: |
            def transform(params):
                # Normalize query
                params['query'] = params['query'].lower().strip()

                # Add timestamp
                from datetime import datetime
                params['timestamp'] = datetime.utcnow().isoformat()

                return params
```

## Multiple Tools from One Pipeline

Create multiple tools with different configurations from a single pipeline:

```yaml
pipelines:
  flexible_search:
    parameters:
      query: string
      mode: string
      top_k: integer
      rerank: boolean
    steps:
      - use: rag.search
        config:
          subtechnique: ${mode}
          top_k: ${top_k}
      - use: rag.reranking
        condition: ${rerank}

mcp:
  tools:
    # Quick search - fast, fewer results
    - name: quick_search
      description: "Fast search with top 3 results"
      pipeline: flexible_search
      parameters:
        query:
          type: string
          required: true
      defaults:
        mode: "vector"
        top_k: 3
        rerank: false

    # Standard search - balanced
    - name: search_documents
      description: "Standard search with reranking"
      pipeline: flexible_search
      parameters:
        query:
          type: string
          required: true
        num_results:
          type: integer
          default: 5
      parameter_mapping:
        num_results: top_k
      defaults:
        mode: "hybrid"
        rerank: true

    # Deep search - comprehensive, slow
    - name: deep_search
      description: "Comprehensive search with maximum results"
      pipeline: flexible_search
      parameters:
        query:
          type: string
          required: true
      defaults:
        mode: "hybrid"
        top_k: 20
        rerank: true
```

## Dynamic Tool Generation

### Auto-Generate Tools from Pipelines

```yaml
mcp:
  auto_generate_tools: true
  auto_generate_config:
    # Which pipelines to expose
    include_pipelines:
      - search_*              # All search pipelines
      - qa_*                  # All QA pipelines

    exclude_pipelines:
      - internal_*            # Exclude internal pipelines

    # Naming convention
    name_template: "${pipeline_name}"
    description_template: "Execute ${pipeline_name} pipeline"

    # Default parameters
    default_parameters:
      - name: input
        type: object
        description: "Pipeline input"
        required: true
```

### Tool Discovery from Directory

```yaml
mcp:
  tools_directory: ./custom_tools
  auto_discover: true

  # Tool definition format
  tool_definition_format: yaml    # yaml, json, python
```

**Example tool definition** (`./custom_tools/analyze_code.yaml`):
```yaml
name: analyze_code
description: "Analyze code and answer questions"
pipeline: code_analysis_pipeline
parameters:
  query:
    type: string
    required: true
  language:
    type: string
    enum: ["python", "javascript", "java"]
  include_tests:
    type: boolean
    default: false
```

### Programmatic Tool Registration

```python
# custom_tools/register.py
from sibyl.mcp import MCPServer

def register_tools(server: MCPServer):
    """Register custom tools programmatically."""

    # Register tool
    server.register_tool(
        name="custom_search",
        description="Custom search implementation",
        pipeline="search_pipeline",
        parameters={
            "query": {
                "type": "string",
                "required": True
            }
        }
    )

    # Register tool with handler
    @server.tool("analyze_sentiment")
    async def analyze_sentiment(text: str) -> dict:
        """Analyze sentiment of text."""
        # Custom implementation
        result = await some_analysis(text)
        return {"sentiment": result}
```

## Tool Versioning

### Multiple Versions

Support multiple versions of the same tool:

```yaml
mcp:
  versioning:
    enabled: true
    default_version: v2
    version_in_path: true         # /v1/tools/search, /v2/tools/search

  tools:
    # Version 1 - deprecated
    - name: search_documents
      version: v1
      pipeline: search_v1
      deprecated: true
      deprecation_message: "Use v2 for better results"
      sunset_date: "2024-12-31"

    # Version 2 - current
    - name: search_documents
      version: v2
      pipeline: search_v2
      default: true

    # Version 3 - beta
    - name: search_documents
      version: v3
      pipeline: search_v3
      beta: true
```

**Usage**:
```bash
# Default version (v2)
curl -X POST http://localhost:8000/mcp/tools/search_documents

# Specific version
curl -X POST http://localhost:8000/mcp/v1/tools/search_documents
curl -X POST http://localhost:8000/mcp/v2/tools/search_documents
curl -X POST http://localhost:8000/mcp/v3/tools/search_documents
```

### Version Migration

```yaml
mcp:
  tools:
    - name: search
      version: v2
      pipeline: search_v2

      # Auto-migrate v1 requests
      migration:
        from_version: v1
        parameter_changes:
          # Renamed parameter
          old_query: query

          # Changed type
          max_results:
            old_type: string
            new_type: integer
            transform: "int(value)"

          # Removed parameter
          deprecated_option:
            removed: true
            replacement: "Use new_option instead"
```

## Tool Organization

### Tool Categories

```yaml
mcp:
  tools:
    - name: search_documents
      category: search
      tags: ["rag", "documents", "retrieval"]

    - name: analyze_code
      category: analysis
      tags: ["code", "analysis"]

    - name: generate_summary
      category: generation
      tags: ["ai", "generation", "summary"]

  # Category descriptions
  categories:
    search:
      description: "Search and retrieval tools"
      icon: "🔍"
    analysis:
      description: "Analysis and inspection tools"
      icon: "🔬"
    generation:
      description: "Content generation tools"
      icon: "✨"
```

### Tool Groups

```yaml
mcp:
  tool_groups:
    # Documentation group
    - name: documentation
      description: "Tools for working with documentation"
      tools:
        - search_docs
        - index_docs
        - summarize_docs

    # Code group
    - name: code
      description: "Tools for code analysis"
      tools:
        - analyze_code
        - search_code
        - explain_code
```

## Tool Metadata and Documentation

### Rich Tool Metadata

```yaml
mcp:
  tools:
    - name: search_documents
      description: "Search indexed documents and answer questions"

      # Extended metadata
      metadata:
        version: "2.0.0"
        author: "Your Team"
        category: search
        tags: ["rag", "documents", "qa"]

        # Cost information
        cost:
          estimate: "~$0.01 per query"
          factors:
            - "Number of documents retrieved"
            - "LLM generation cost"

        # Performance
        performance:
          avg_latency_ms: 1500
          p95_latency_ms: 3000

        # Rate limits
        rate_limit:
          requests_per_minute: 60
          requests_per_hour: 1000

        # Usage examples
        examples:
          - description: "Basic question"
            parameters:
              query: "What is Sibyl?"
            expected_output: "Detailed explanation..."

          - description: "Complex query with filters"
            parameters:
              query: "Explain RAG pipelines"
              top_k: 10
              search_mode: "hybrid"
            expected_output: "Comprehensive answer..."

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
                  title: { type: string }
                  content: { type: string }
                  score: { type: number }
            metadata:
              type: object
              description: "Execution metadata"
```

### OpenAPI Documentation

Generate OpenAPI/Swagger documentation:

```yaml
mcp:
  documentation:
    enabled: true
    path: /docs

    openapi:
      enabled: true
      title: "Sibyl MCP API"
      version: "2.0.0"
      description: |
        MCP tools for document search, code analysis, and AI generation.

      servers:
        - url: http://localhost:8000
          description: Local development
        - url: https://api.example.com
          description: Production

      contact:
        name: API Support
        email: support@example.com
        url: https://example.com/support

      license:
        name: Apache-2.0
        url: https://www.apache.org/licenses/LICENSE-2.0
```

**Access documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI spec: `http://localhost:8000/openapi.json`

## Tool Security

### Input Validation

```yaml
mcp:
  tools:
    - name: search_documents
      parameters:
        query:
          type: string
          required: true

          # Security constraints
          minLength: 1
          maxLength: 1000           # Prevent very long inputs
          pattern: "^[a-zA-Z0-9 .,?!-]+$"  # Allowed characters only

      # Additional validation
      validation:
        - name: no_sql_injection
          type: pattern
          pattern: "(?i)(select|insert|update|delete|drop|union)"
          action: reject

        - name: no_path_traversal
          type: pattern
          pattern: "\\.\\."
          action: reject
```

### Tool Permissions

```yaml
mcp:
  authentication:
    type: api_key

  authorization:
    enabled: true

    # Define roles
    roles:
      admin:
        description: "Full access"
        permissions: ["*"]

      user:
        description: "Standard user"
        permissions:
          - "search_*"          # All search tools
          - "read_*"            # All read tools

      readonly:
        description: "Read-only access"
        permissions:
          - "search_documents"
          - "get_info"

    # Assign API keys to roles
    api_key_roles:
      "${API_KEY_ADMIN}": admin
      "${API_KEY_USER}": user
      "${API_KEY_READONLY}": readonly

  # Tool-specific permissions
  tools:
    - name: delete_documents
      description: "Delete indexed documents"
      pipeline: delete_pipeline

      # Require admin role
      permissions:
        required_roles: ["admin"]

      # Additional confirmation
      confirmation_required: true
      confirmation_message: "Are you sure you want to delete documents?"
```

### Rate Limiting per Tool

```yaml
mcp:
  tools:
    - name: expensive_analysis
      pipeline: complex_pipeline

      # Tool-specific rate limits
      rate_limit:
        requests_per_minute: 10   # Lower than global limit
        requests_per_hour: 100

        # Cost-based limit
        max_cost_per_hour: 5.0
```

## Tool Analytics

### Usage Tracking

```yaml
mcp:
  analytics:
    enabled: true

    # What to track
    track_tool_calls: true
    track_parameters: true        # Be careful with PII
    track_results: false          # Don't track full results
    track_errors: true
    track_latency: true

    # Storage
    storage: database
    database_url: "${DATABASE_URL}"
    table: tool_analytics

    # Retention
    retention_days: 90
```

**Query analytics**:
```sql
-- Most popular tools
SELECT tool_name, COUNT(*) as calls
FROM tool_analytics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY calls DESC;

-- Average latency
SELECT tool_name, AVG(latency_ms) as avg_latency
FROM tool_analytics
GROUP BY tool_name;

-- Error rate
SELECT
  tool_name,
  COUNT(*) as total_calls,
  SUM(CASE WHEN error THEN 1 ELSE 0 END) as errors,
  (SUM(CASE WHEN error THEN 1 ELSE 0 END)::float / COUNT(*)) * 100 as error_rate
FROM tool_analytics
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY tool_name;
```

## Testing Tools

### Manual Testing

```bash
# List tools
curl http://localhost:8000/mcp/tools | jq '.'

# Get tool details
curl http://localhost:8000/mcp/tools/search_documents | jq '.'

# Call tool
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Sibyl?"}' | jq '.'
```

### Automated Testing

```python
# tests/mcp/test_tools.py
import pytest
from sibyl.mcp import MCPServer

@pytest.fixture
async def mcp_server():
    """Create MCP server for testing."""
    server = MCPServer(workspace="config/workspaces/test.yaml")
    await server.start()
    yield server
    await server.stop()

@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test listing tools."""
    tools = await mcp_server.list_tools()

    assert len(tools) > 0
    assert any(tool["name"] == "search_documents" for tool in tools)

@pytest.mark.asyncio
async def test_call_search_tool(mcp_server):
    """Test calling search tool."""
    result = await mcp_server.call_tool(
        "search_documents",
        {"query": "test query"}
    )

    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0

@pytest.mark.asyncio
async def test_invalid_parameters(mcp_server):
    """Test parameter validation."""
    with pytest.raises(ValidationError):
        await mcp_server.call_tool(
            "search_documents",
            {"query": ""}  # Empty query
        )

@pytest.mark.asyncio
async def test_tool_not_found(mcp_server):
    """Test calling non-existent tool."""
    with pytest.raises(ToolNotFoundError):
        await mcp_server.call_tool(
            "nonexistent_tool",
            {}
        )
```

## Further Reading

- **[MCP Overview](overview.md)** - MCP integration overview
- **[Server Setup](server-setup.md)** - MCP server configuration
- **[Client Integration](client-integration.md)** - Integrate with MCP clients
- **[MCP Tools Configuration](../workspaces/mcp-tools.md)** - Workspace MCP config
- **[REST API](rest-api.md)** - HTTP API reference

---

**Previous**: [Client Integration](client-integration.md) | **Next**: [REST API Reference](rest-api.md)
