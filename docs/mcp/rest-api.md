# REST API Reference

Complete HTTP REST API reference for Sibyl MCP server.

## Overview

When running Sibyl MCP server in HTTP mode, it exposes a REST API for programmatic access to tools and pipelines.

**Base URL**: `http://localhost:8000` (default)

## Authentication

### API Key Authentication

Include API key in request header:

```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### JWT Authentication

Include JWT token in Authorization header:

```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

## Endpoints

### List Tools

Get all available MCP tools.

**Endpoint**: `GET /mcp/tools`

**Response**:
```json
[
  {
    "name": "search_documents",
    "description": "Search indexed documents and answer questions",
    "version": "1.0.0",
    "parameters": {
      "query": {
        "type": "string",
        "description": "Your question",
        "required": true
      },
      "top_k": {
        "type": "integer",
        "description": "Number of results",
        "default": 5,
        "minimum": 1,
        "maximum": 20
      }
    },
    "metadata": {
      "category": "search",
      "tags": ["rag", "documents"]
    }
  }
]
```

**Example**:
```bash
curl http://localhost:8000/mcp/tools | jq '.'
```

### Get Tool Details

Get detailed information about a specific tool.

**Endpoint**: `GET /mcp/tools/{tool_name}`

**Response**:
```json
{
  "name": "search_documents",
  "description": "Search indexed documents and answer questions",
  "version": "1.0.0",
  "parameters": {
    "query": {
      "type": "string",
      "description": "Your question",
      "required": true,
      "minLength": 1,
      "maxLength": 500
    }
  },
  "examples": [
    {
      "description": "Basic search",
      "parameters": {
        "query": "What is Sibyl?"
      }
    }
  ],
  "response_schema": {
    "type": "object",
    "properties": {
      "answer": {
        "type": "string"
      },
      "sources": {
        "type": "array"
      }
    }
  }
}
```

**Example**:
```bash
curl http://localhost:8000/mcp/tools/search_documents | jq '.'
```

### Call Tool

Execute a tool with parameters.

**Endpoint**: `POST /mcp/tools/{tool_name}`

**Request Body**:
```json
{
  "query": "What is Sibyl?",
  "top_k": 5
}
```

**Response**:
```json
{
  "output": {
    "answer": "Sibyl is a Universal AI Assistant Platform...",
    "sources": [
      {
        "title": "Introduction to Sibyl",
        "content": "Sibyl provides...",
        "score": 0.95
      }
    ]
  },
  "metadata": {
    "tool": "search_documents",
    "execution_time_ms": 1234,
    "tokens_used": 856,
    "cost_usd": 0.012
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "What is Sibyl?",
    "top_k": 5
  }' | jq '.'
```

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Tool not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Call Tool (Streaming)

Execute a tool with streaming response.

**Endpoint**: `POST /mcp/tools/{tool_name}/stream`

**Request Body**:
```json
{
  "query": "Explain RAG in detail"
}
```

**Response** (Server-Sent Events):
```
data: {"type": "start", "tool": "search_documents"}

data: {"type": "chunk", "content": "RAG stands for"}

data: {"type": "chunk", "content": " Retrieval-Augmented"}

data: {"type": "chunk", "content": " Generation..."}

data: {"type": "metadata", "tokens_used": 45}

data: {"type": "end", "execution_time_ms": 2345}
```

**Example**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"query": "Explain RAG"}' \
  --no-buffer
```

**JavaScript Example**:
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/mcp/tools/search_documents/stream?query=test'
);

eventSource.addEventListener('chunk', (event) => {
  const data = JSON.parse(event.data);
  console.log(data.content);
});

eventSource.addEventListener('end', (event) => {
  console.log('Stream ended');
  eventSource.close();
});
```

### Health Check

Check server health status.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "vector_store": {
      "status": "healthy",
      "latency_ms": 12
    },
    "llm_provider": {
      "status": "healthy",
      "latency_ms": 45
    }
  }
}
```

**Example**:
```bash
curl http://localhost:8000/health | jq '.'
```

### Liveness Probe

Check if server is running (Kubernetes liveness probe).

**Endpoint**: `GET /health/live`

**Response**:
```json
{
  "status": "alive"
}
```

### Readiness Probe

Check if server is ready to accept traffic (Kubernetes readiness probe).

**Endpoint**: `GET /health/ready`

**Response**:
```json
{
  "status": "ready"
}
```

### Metrics

Get Prometheus metrics.

**Endpoint**: `GET /metrics` (default port: 9090)

**Response** (Prometheus format):
```
# HELP sibyl_mcp_tool_calls_total Total tool calls
# TYPE sibyl_mcp_tool_calls_total counter
sibyl_mcp_tool_calls_total{tool="search_documents",status="success"} 1234

# HELP sibyl_mcp_tool_duration_seconds Tool execution duration
# TYPE sibyl_mcp_tool_duration_seconds histogram
sibyl_mcp_tool_duration_seconds_bucket{tool="search_documents",le="0.5"} 456
sibyl_mcp_tool_duration_seconds_bucket{tool="search_documents",le="1.0"} 789
sibyl_mcp_tool_duration_seconds_sum{tool="search_documents"} 1523.4
sibyl_mcp_tool_duration_seconds_count{tool="search_documents"} 1234

# HELP sibyl_mcp_requests_total Total HTTP requests
# TYPE sibyl_mcp_requests_total counter
sibyl_mcp_requests_total{method="POST",status="200"} 5678
```

**Example**:
```bash
curl http://localhost:9090/metrics
```

## Error Responses

### Standard Error Format

All errors follow this format:

```json
{
  "error": {
    "code": "invalid_parameters",
    "message": "Parameter 'query' is required",
    "details": {
      "parameter": "query",
      "constraint": "required"
    }
  },
  "request_id": "req_abc123"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_parameters` | 400 | Invalid or missing parameters |
| `validation_error` | 400 | Parameter validation failed |
| `unauthorized` | 401 | Missing or invalid authentication |
| `forbidden` | 403 | Insufficient permissions |
| `not_found` | 404 | Tool or resource not found |
| `rate_limit_exceeded` | 429 | Too many requests |
| `tool_execution_error` | 500 | Tool execution failed |
| `internal_error` | 500 | Internal server error |

### Rate Limit Response

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded: 60 requests per minute",
    "details": {
      "limit": "60 requests per minute",
      "remaining": 0,
      "reset_at": "2024-01-01T12:01:00Z"
    }
  }
}
```

**Headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704110460
Retry-After: 45
```

## Request/Response Headers

### Common Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes (POST) | `application/json` |
| `X-API-Key` | If auth enabled | API key for authentication |
| `Authorization` | If JWT auth | `Bearer {token}` |
| `X-Request-ID` | No | Client-provided request ID for tracing |
| `Accept` | No | Response format (default: `application/json`) |

### Common Response Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | Response content type |
| `X-Request-ID` | Request ID for tracing |
| `X-Execution-Time-Ms` | Tool execution time in milliseconds |
| `X-RateLimit-Limit` | Rate limit maximum |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

## Pagination

For endpoints that return lists (future):

**Request**:
```
GET /mcp/tools?page=2&per_page=10
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 10,
    "total_pages": 5,
    "total_items": 47
  },
  "links": {
    "first": "/mcp/tools?page=1&per_page=10",
    "prev": "/mcp/tools?page=1&per_page=10",
    "next": "/mcp/tools?page=3&per_page=10",
    "last": "/mcp/tools?page=5&per_page=10"
  }
}
```

## Filtering and Sorting

Filter and sort tool lists:

**Request**:
```
GET /mcp/tools?category=search&tags=rag&sort=name&order=asc
```

**Parameters**:
- `category`: Filter by category
- `tags`: Filter by tags (comma-separated)
- `sort`: Sort field (`name`, `category`, `version`)
- `order`: Sort order (`asc`, `desc`)

## Versioning

### URL Versioning

```
GET /v1/mcp/tools
GET /v2/mcp/tools
```

### Header Versioning

```bash
curl http://localhost:8000/mcp/tools \
  -H "X-API-Version: 2.0"
```

## CORS

CORS headers for web applications:

**Preflight Request**:
```
OPTIONS /mcp/tools/search_documents
```

**Response**:
```
Access-Control-Allow-Origin: https://myapp.com
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-API-Key
Access-Control-Max-Age: 86400
```

## Client Libraries

### Python

```python
import httpx

class SibylAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": api_key},
            timeout=60.0
        )

    async def list_tools(self):
        response = await self.client.get(f"{self.base_url}/mcp/tools")
        response.raise_for_status()
        return response.json()

    async def call_tool(self, tool_name: str, parameters: dict):
        response = await self.client.post(
            f"{self.base_url}/mcp/tools/{tool_name}",
            json=parameters
        )
        response.raise_for_status()
        return response.json()

# Usage
api = SibylAPI("http://localhost:8000", "your-api-key")
tools = await api.list_tools()
result = await api.call_tool("search_documents", {"query": "test"})
```

### JavaScript/TypeScript

```typescript
class SibylAPI {
  constructor(
    private baseUrl: string,
    private apiKey: string
  ) {}

  async listTools() {
    const response = await fetch(`${this.baseUrl}/mcp/tools`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    return response.json();
  }

  async callTool(toolName: string, parameters: any) {
    const response = await fetch(
      `${this.baseUrl}/mcp/tools/${toolName}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey
        },
        body: JSON.stringify(parameters)
      }
    );
    return response.json();
  }
}

// Usage
const api = new SibylAPI('http://localhost:8000', 'your-api-key');
const tools = await api.listTools();
const result = await api.callTool('search_documents', { query: 'test' });
```

### curl Examples

**Basic search**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SIBYL_API_KEY}" \
  -d '{"query": "What is Sibyl?"}'
```

**With custom parameters**:
```bash
curl -X POST http://localhost:8000/mcp/tools/advanced_search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SIBYL_API_KEY}" \
  -d '{
    "query": "machine learning",
    "top_k": 10,
    "search_mode": "hybrid",
    "categories": ["technical", "research"]
  }'
```

**Streaming response**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SIBYL_API_KEY}" \
  -d '{"query": "Explain RAG"}' \
  --no-buffer
```

**With request tracing**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SIBYL_API_KEY}" \
  -H "X-Request-ID: req_$(uuidgen)" \
  -d '{"query": "test"}' \
  -v  # Verbose to see headers
```

## OpenAPI Specification

Access the OpenAPI specification:

**Endpoint**: `GET /openapi.json`

**Response**:
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Sibyl MCP API",
    "version": "1.0.0",
    "description": "MCP tools for document search and AI generation"
  },
  "servers": [
    {
      "url": "http://localhost:8000",
      "description": "Local development"
    }
  ],
  "paths": {
    "/mcp/tools": {
      "get": {
        "summary": "List all tools",
        "responses": {
          "200": {
            "description": "List of tools",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Tool"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Swagger UI**: `http://localhost:8000/docs`
**ReDoc**: `http://localhost:8000/redoc`

## Rate Limiting

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704110460
```

### Handling Rate Limits

**Python example**:
```python
async def call_with_retry(api, tool_name, parameters):
    while True:
        try:
            return await api.call_tool(tool_name, parameters)
        except RateLimitError as e:
            retry_after = e.retry_after
            print(f"Rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
```

**JavaScript example**:
```javascript
async function callWithRetry(api, toolName, parameters) {
  while (true) {
    try {
      return await api.callTool(toolName, parameters);
    } catch (error) {
      if (error.status === 429) {
        const retryAfter = parseInt(error.headers.get('Retry-After'));
        console.log(`Rate limited, waiting ${retryAfter}s`);
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      } else {
        throw error;
      }
    }
  }
}
```

## WebSocket API

Real-time bidirectional communication (if enabled):

**Connect**:
```javascript
const ws = new WebSocket('ws://localhost:8000/mcp/ws');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'your-api-key'
  }));

  // Call tool
  ws.send(JSON.stringify({
    type: 'call_tool',
    tool: 'search_documents',
    parameters: { query: 'test' },
    request_id: 'req_123'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Response:', data);
};
```

## Webhooks

Configure webhooks for event notifications (if enabled):

**Configuration**:
```yaml
mcp:
  webhooks:
    enabled: true
    endpoints:
      - url: https://myapp.com/webhooks/sibyl
        events:
          - tool_called
          - tool_completed
          - tool_failed
        secret: "${WEBHOOK_SECRET}"
```

**Webhook Payload**:
```json
{
  "event": "tool_completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "tool": "search_documents",
    "request_id": "req_123",
    "execution_time_ms": 1234,
    "status": "success"
  }
}
```

## Best Practices

1. **Always handle rate limits**: Implement exponential backoff
2. **Use request IDs**: For tracing and debugging
3. **Validate responses**: Check status codes and error messages
4. **Cache when possible**: Reduce API calls
5. **Use streaming for long responses**: Better UX
6. **Set appropriate timeouts**: Prevent hanging requests
7. **Monitor usage**: Track API calls and costs
8. **Handle errors gracefully**: User-friendly error messages

## Further Reading

- **[MCP Overview](overview.md)** - MCP integration overview
- **[Server Setup](server-setup.md)** - MCP server configuration
- **[Client Integration](client-integration.md)** - Build MCP clients
- **[Tool Exposure](tool-exposure.md)** - Configure MCP tools

---

**Previous**: [Tool Exposure](tool-exposure.md) | **Next**: [Observability Guide](../operations/observability.md)
