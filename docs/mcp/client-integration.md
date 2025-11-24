# MCP Client Integration

Complete guide to integrating Sibyl MCP server with various MCP clients.

## Overview

Sibyl MCP server can be integrated with multiple types of clients:

1. **Claude Desktop** - Anthropic's desktop application
2. **Custom MCP Clients** - Build your own MCP clients
3. **Web Applications** - Browser-based integrations
4. **CLI Tools** - Command-line MCP clients
5. **Third-Party Tools** - Other MCP-compatible applications

## Claude Desktop Integration

### Installation and Setup

**1. Install Claude Desktop**:
- Download from [claude.ai](https://claude.ai/download)
- Install for your platform (macOS, Windows)

**2. Locate Configuration File**:

**macOS**:
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows**:
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**3. Configure Sibyl MCP Server**:

```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/docs.yaml"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**4. Restart Claude Desktop**

**5. Verify Integration**:
- Open Claude Desktop
- Look for MCP tools in the interface
- Try: "Use sibyl to search for information about X"

### Multiple Sibyl Instances

Configure multiple Sibyl servers for different purposes:

```json
{
  "mcpServers": {
    "sibyl-docs": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/docs.yaml"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    },
    "sibyl-code": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/code.yaml"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    },
    "sibyl-customer-data": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/customer.yaml"
      ],
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

**Usage in Claude Desktop**:
```
User: Use sibyl-docs to explain quantum computing
Claude: [Uses sibyl-docs tool to search documentation]

User: Use sibyl-code to find the authentication implementation
Claude: [Uses sibyl-code tool to search codebase]

User: Use sibyl-customer-data to get customer info for ID 12345
Claude: [Uses sibyl-customer-data tool to query database]
```

### Environment Variables

**Best practices**:
```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": ["--workspace", "/Users/username/sibyl/config/workspaces/prod.yaml"],
      "env": {
        // API Keys
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-...",

        // Database
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "REDIS_URL": "redis://localhost:6379/0",

        // Logging
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "/Users/username/.sibyl/logs/mcp.log",

        // Application
        "WORKSPACE_ENV": "production",
        "CACHE_ENABLED": "true"
      }
    }
  }
}
```

**Security**: Use environment variables instead of hardcoding secrets:
```json
// ❌ Bad - hardcoded secrets
{
  "env": {
    "OPENAI_API_KEY": "sk-abc123..."
  }
}

// ✅ Good - reference system environment
{
  "env": {
    "OPENAI_API_KEY": "${OPENAI_API_KEY}"
  }
}
```

### Troubleshooting Claude Desktop

**Tools not appearing**:
```bash
# 1. Verify workspace
sibyl workspace validate /path/to/workspace.yaml

# 2. Test MCP server independently
/path/to/.venv/bin/sibyl-mcp --workspace /path/to/workspace.yaml

# 3. Check logs
tail -f ~/.sibyl/logs/mcp_server.log

# 4. Verify Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Common issues**:
1. **Relative paths**: Use absolute paths for `command` and workspace
2. **Wrong Python**: Ensure `sibyl-mcp` is from the correct virtual environment
3. **Missing env vars**: Set all required environment variables
4. **Permission issues**: Ensure files are readable

**Debug mode**:
```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/path/to/sibyl-mcp",
      "args": ["--workspace", "/path/to/workspace.yaml"],
      "env": {
        "LOG_LEVEL": "DEBUG",
        "SIBYL_DEBUG": "true"
      }
    }
  }
}
```

## Custom MCP Client (Python)

Build your own MCP client to interact with Sibyl.

### Basic Python Client

```python
import asyncio
import json
from typing import Dict, Any

class SibylMCPClient:
    """Simple MCP client for Sibyl."""

    def __init__(self, server_url: str, api_key: str = None):
        """
        Initialize MCP client.

        Args:
            server_url: URL of Sibyl MCP server (e.g., http://localhost:8000)
            api_key: Optional API key for authentication
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        import aiohttp
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def list_tools(self) -> list:
        """List available tools."""
        headers = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        async with self.session.get(
            f"{self.server_url}/mcp/tools",
            headers=headers
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool.

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        async with self.session.post(
            f"{self.server_url}/mcp/tools/{tool_name}",
            headers=headers,
            json=parameters
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def call_tool_streaming(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ):
        """
        Call a tool with streaming response.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Yields:
            Streaming response chunks
        """
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        async with self.session.post(
            f"{self.server_url}/mcp/tools/{tool_name}/stream",
            headers=headers,
            json=parameters
        ) as response:
            response.raise_for_status()
            async for line in response.content:
                if line:
                    yield json.loads(line)


async def main():
    """Example usage."""
    async with SibylMCPClient(
        server_url="http://localhost:8000",
        api_key="your-api-key"
    ) as client:

        # List available tools
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Call a tool
        result = await client.call_tool(
            tool_name="search_documents",
            parameters={"query": "What is Sibyl?"}
        )
        print(f"\nResult: {result['answer']}")

        # Streaming call
        print("\nStreaming result:")
        async for chunk in client.call_tool_streaming(
            tool_name="search_documents",
            parameters={"query": "Explain RAG"}
        ):
            print(chunk['text'], end='', flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Python Client

```python
import asyncio
import aiohttp
from typing import Dict, Any, Optional, AsyncIterator
import logging

logger = logging.getLogger(__name__)

class AdvancedSibylClient:
    """Advanced MCP client with retry logic, caching, and error handling."""

    def __init__(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3
    ):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=self._get_headers(),
                    **kwargs
                ) as response:
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    return response

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def list_tools(self, use_cache: bool = True) -> list:
        """List available tools with caching."""
        cache_key = "tools_list"

        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        async with await self._request_with_retry(
            'GET',
            f"{self.server_url}/mcp/tools"
        ) as response:
            tools = await response.json()
            self._cache[cache_key] = tools
            return tools

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """Call tool with optional caching."""
        cache_key = f"tool_{tool_name}_{hash(frozenset(parameters.items()))}"

        if use_cache and cache_key in self._cache:
            logger.info(f"Cache hit for {tool_name}")
            return self._cache[cache_key]

        async with await self._request_with_retry(
            'POST',
            f"{self.server_url}/mcp/tools/{tool_name}",
            json=parameters
        ) as response:
            result = await response.json()

            if use_cache:
                self._cache[cache_key] = result

            return result

    async def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        async with self.session.get(
            f"{self.server_url}/health"
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_metrics(self) -> str:
        """Get Prometheus metrics."""
        async with self.session.get(
            f"{self.server_url}:9090/metrics"
        ) as response:
            response.raise_for_status()
            return await response.text()
```

## Web Application Integration

### JavaScript/TypeScript Client

```typescript
// sibyl-mcp-client.ts

interface Tool {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

interface ToolResult {
  output: any;
  metadata: Record<string, any>;
}

class SibylMCPClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(baseUrl: string, apiKey?: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    return headers;
  }

  async listTools(): Promise<Tool[]> {
    const response = await fetch(
      `${this.baseUrl}/mcp/tools`,
      { headers: this.getHeaders() }
    );

    if (!response.ok) {
      throw new Error(`Failed to list tools: ${response.statusText}`);
    }

    return response.json();
  }

  async callTool(
    toolName: string,
    parameters: Record<string, any>
  ): Promise<ToolResult> {
    const response = await fetch(
      `${this.baseUrl}/mcp/tools/${toolName}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(parameters),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || response.statusText);
    }

    return response.json();
  }

  async *callToolStreaming(
    toolName: string,
    parameters: Record<string, any>
  ): AsyncGenerator<any> {
    const response = await fetch(
      `${this.baseUrl}/mcp/tools/${toolName}/stream`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(parameters),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to call tool: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Stream not available');
    }

    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.trim()) {
          yield JSON.parse(line);
        }
      }
    }
  }
}

// Usage example
async function example() {
  const client = new SibylMCPClient(
    'http://localhost:8000',
    'your-api-key'
  );

  // List tools
  const tools = await client.listTools();
  console.log('Available tools:', tools);

  // Call tool
  const result = await client.callTool('search_documents', {
    query: 'What is Sibyl?'
  });
  console.log('Result:', result);

  // Streaming call
  for await (const chunk of client.callToolStreaming('search_documents', {
    query: 'Explain RAG'
  })) {
    console.log('Chunk:', chunk);
  }
}
```

### React Integration

```tsx
// useSibylMCP.ts - React Hook

import { useState, useEffect } from 'react';

interface UseSibylMCPOptions {
  baseUrl: string;
  apiKey?: string;
}

export function useSibylMCP({ baseUrl, apiKey }: UseSibylMCPOptions) {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const client = useMemo(
    () => new SibylMCPClient(baseUrl, apiKey),
    [baseUrl, apiKey]
  );

  useEffect(() => {
    async function loadTools() {
      try {
        setLoading(true);
        const toolsList = await client.listTools();
        setTools(toolsList);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    loadTools();
  }, [client]);

  const callTool = async (toolName: string, parameters: any) => {
    try {
      setLoading(true);
      setError(null);
      const result = await client.callTool(toolName, parameters);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { tools, loading, error, callTool };
}

// Component usage
function SearchComponent() {
  const { tools, loading, error, callTool } = useSibylMCP({
    baseUrl: 'http://localhost:8000',
    apiKey: process.env.REACT_APP_SIBYL_API_KEY,
  });

  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);

  const handleSearch = async () => {
    const searchResult = await callTool('search_documents', { query });
    setResult(searchResult);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter your question"
      />
      <button onClick={handleSearch}>Search</button>

      {result && (
        <div>
          <h3>Result:</h3>
          <p>{result.output}</p>
        </div>
      )}
    </div>
  );
}
```

## CLI Tool Integration

### Bash Script

```bash
#!/bin/bash
# sibyl-cli.sh - Simple CLI wrapper for Sibyl MCP

SIBYL_URL="${SIBYL_URL:-http://localhost:8000}"
SIBYL_API_KEY="${SIBYL_API_KEY}"

# List tools
list_tools() {
    curl -s \
        -H "X-API-Key: $SIBYL_API_KEY" \
        "$SIBYL_URL/mcp/tools" | jq '.'
}

# Call tool
call_tool() {
    local tool_name="$1"
    local query="$2"

    curl -s \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $SIBYL_API_KEY" \
        -d "{\"query\": \"$query\"}" \
        "$SIBYL_URL/mcp/tools/$tool_name" | jq '.output'
}

# Main
case "$1" in
    list)
        list_tools
        ;;
    search)
        call_tool "search_documents" "$2"
        ;;
    *)
        echo "Usage: $0 {list|search <query>}"
        exit 1
        ;;
esac
```

**Usage**:
```bash
# List tools
./sibyl-cli.sh list

# Search
./sibyl-cli.sh search "What is Sibyl?"
```

## Error Handling

### Client-Side Error Handling

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SibylMCPError(Exception):
    """Base exception for Sibyl MCP errors."""
    pass

class AuthenticationError(SibylMCPError):
    """Authentication failed."""
    pass

class RateLimitError(SibylMCPError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")

class ToolNotFoundError(SibylMCPError):
    """Tool not found."""
    pass

class ToolExecutionError(SibylMCPError):
    """Tool execution failed."""
    pass

async def safe_call_tool(
    client: SibylMCPClient,
    tool_name: str,
    parameters: dict,
    max_retries: int = 3
) -> Optional[dict]:
    """Safely call tool with error handling."""
    for attempt in range(max_retries):
        try:
            return await client.call_tool(tool_name, parameters)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                logger.error(f"Rate limited after {max_retries} attempts")
                raise
            logger.warning(f"Rate limited, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)

        except AuthenticationError:
            logger.error("Authentication failed")
            raise

        except ToolNotFoundError:
            logger.error(f"Tool not found: {tool_name}")
            raise

        except ToolExecutionError as e:
            if attempt == max_retries - 1:
                logger.error(f"Tool execution failed after {max_retries} attempts")
                raise
            logger.warning(f"Tool execution failed, retrying: {e}")
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise SibylMCPError(f"Unexpected error: {e}") from e

    return None
```

## Further Reading

- **[MCP Overview](overview.md)** - MCP integration overview
- **[Server Setup](server-setup.md)** - MCP server configuration
- **[Tool Exposure](tool-exposure.md)** - Configure MCP tools
- **[REST API](rest-api.md)** - HTTP API reference

---

**Previous**: [Server Setup](server-setup.md) | **Next**: [Tool Exposure](tool-exposure.md)
