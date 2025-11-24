# MCP Integration Example

Integrate Sibyl with MCP (Model Context Protocol) servers to expose your AI capabilities as tools.

## Overview

Learn how to:
- Set up MCP server for Sibyl
- Expose techniques as MCP tools
- Connect MCP clients (Claude Desktop, IDEs)
- Build custom MCP tools

**Time:** 15 minutes | **Difficulty:** Beginner

---

## Quick Setup

### Step 1: Configure MCP Server

**workspace_config.yaml:**
```yaml
workspace_name: mcp_workspace

mcp:
  enabled: true
  server:
    host: "localhost"
    port: 8765
    transport: "stdio"  # or "sse"

  exposed_tools:
    # Expose RAG as an MCP tool
    - name: "search_knowledge_base"
      shop: "rag_pipeline"
      technique: "retrieval"
      subtechnique: "semantic_search"
      description: "Search the knowledge base for information"
      parameters:
        query:
          type: "string"
          description: "The search query"
          required: true
        top_k:
          type: "integer"
          description: "Number of results to return"
          default: 5

    # Expose SQL query as an MCP tool
    - name: "query_database"
      shop: "data_integration"
      technique: "query_sql"
      description: "Query the SQL database"
      parameters:
        question:
          type: "string"
          description: "Natural language question"
          required: true

shops:
  rag_pipeline:
    retrieval:
      technique: semantic_search

  data_integration:
    query_sql:
      technique: query

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
```

### Step 2: Start MCP Server

```bash
# Start the MCP server
sibyl mcp start --workspace workspaces/mcp_workspace
```

**Output:**
```
🚀 Starting Sibyl MCP Server...
✅ Loaded workspace: mcp_workspace
✅ Registered 2 MCP tools:
   - search_knowledge_base
   - query_database
🌐 Server listening on localhost:8765
✨ MCP Server ready!
```

---

## Connect Claude Desktop

### Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sibyl": {
      "command": "sibyl",
      "args": ["mcp", "start", "--workspace", "workspaces/mcp_workspace"],
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Restart Claude Desktop

The Sibyl tools will now appear in Claude Desktop's tool menu.

### Example Usage in Claude Desktop

**User:** "Search the knowledge base for pricing information"

**Claude:** *Uses `search_knowledge_base` tool*

```json
{
  "tool": "search_knowledge_base",
  "parameters": {
    "query": "pricing information",
    "top_k": 5
  }
}
```

**Result:** Returns relevant pricing documents from your knowledge base.

---

## Custom MCP Tool

Create a custom tool that combines multiple techniques:

**custom_mcp_tool.py:**
```python
#!/usr/bin/env python3
"""Custom MCP tool combining RAG and SQL."""

from typing import Any, Dict

from sibyl.core.application.context import ApplicationContext
from sibyl.core.infrastructure.mcp import MCPTool, MCPToolParameter
from sibyl.techniques.rag_pipeline import retrieval
from sibyl.techniques.data_integration import query_sql
from sibyl.techniques.ai_generation import generation


class HybridSearchTool(MCPTool):
    """MCP tool that searches both documents and database."""

    name = "hybrid_search"
    description = "Search both knowledge base and database simultaneously"

    parameters = [
        MCPToolParameter(
            name="query",
            type="string",
            description="The search query",
            required=True
        ),
        MCPToolParameter(
            name="search_docs",
            type="boolean",
            description="Search documents",
            default=True
        ),
        MCPToolParameter(
            name="search_db",
            type="boolean",
            description="Search database",
            default=True
        )
    ]

    def __init__(self, ctx: ApplicationContext):
        self.ctx = ctx

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hybrid search."""

        query = params["query"]
        results = {}

        # Search documents
        if params.get("search_docs", True):
            doc_result = await retrieval.execute(
                ctx=self.ctx,
                technique="semantic_search",
                params={"query": query, "top_k": 3}
            )

            if doc_result.is_success:
                results["documents"] = [
                    {
                        "content": chunk.content,
                        "source": chunk.metadata.get("source"),
                        "score": chunk.metadata.get("score")
                    }
                    for chunk in doc_result.value
                ]

        # Search database
        if params.get("search_db", True):
            sql_result = await query_sql.execute(
                ctx=self.ctx,
                technique="query",
                params={"question": query}
            )

            if sql_result.is_success:
                results["database"] = sql_result.value

        # Synthesize answer
        synthesis_result = await self._synthesize(query, results)
        results["answer"] = synthesis_result

        return results

    async def _synthesize(self, query: str, results: dict) -> str:
        """Synthesize final answer from all sources."""

        prompt = f"""Answer this question using the provided information:

Question: {query}

Document Results:
{results.get('documents', 'None')}

Database Results:
{results.get('database', 'None')}

Provide a comprehensive answer citing both sources."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={"prompt": prompt}
        )

        return result.value if result.is_success else "Unable to synthesize answer"


# Register the tool
def register_tool(ctx: ApplicationContext):
    """Register custom tool with MCP server."""
    from sibyl.core.infrastructure.mcp import MCPServer

    tool = HybridSearchTool(ctx)
    MCPServer.register_tool(tool)
```

**Use in workspace_config.yaml:**
```yaml
mcp:
  custom_tools:
    - module: "custom_mcp_tool"
      function: "register_tool"
```

---

## MCP REST API

Enable HTTP access to MCP tools:

**workspace_config.yaml:**
```yaml
mcp:
  rest_api:
    enabled: true
    host: "0.0.0.0"
    port: 8080
    cors_origins: ["*"]
```

**Example API Call:**
```bash
curl -X POST http://localhost:8080/tools/search_knowledge_base \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pricing information",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "results": [
    {
      "content": "Our pricing starts at $99/month...",
      "source": "docs/pricing.md",
      "score": 0.92
    },
    ...
  ]
}
```

---

## Advanced: Tool Composition

Create tools that call other tools:

```python
class ComposedTool(MCPTool):
    """Tool that composes multiple tools."""

    name = "research_and_analyze"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        topic = params["topic"]

        # Step 1: Search knowledge base
        search_result = await self.call_tool(
            "search_knowledge_base",
            {"query": topic, "top_k": 10}
        )

        # Step 2: Query related data
        sql_result = await self.call_tool(
            "query_database",
            {"question": f"Find data related to {topic}"}
        )

        # Step 3: Synthesize
        return {
            "research": search_result,
            "data": sql_result,
            "summary": self._create_summary(search_result, sql_result)
        }
```

---

## Monitoring MCP Tools

View tool usage:

```bash
# View logs
sibyl mcp logs --workspace workspaces/mcp_workspace

# View metrics
sibyl mcp metrics
```

**Output:**
```
MCP Tool Usage (Last 24h):
  search_knowledge_base: 142 calls (avg 0.3s)
  query_database: 56 calls (avg 1.2s)
  hybrid_search: 23 calls (avg 1.8s)

Errors: 3 (2.1%)
Success Rate: 97.9%
```

---

## Next Steps

1. **Security:** Add authentication to MCP server
2. **Rate Limiting:** Implement rate limits for tools
3. **Caching:** Cache frequent tool calls
4. **Monitoring:** Add detailed logging and metrics

---

## Learn More

- [MCP Integration Guide](../mcp/overview.md)
- [MCP Server Setup](../mcp/server-setup.md)
- [MCP Tool Development](../mcp/tool-exposure.md)
- [REST API Reference](../mcp/rest-api.md)
