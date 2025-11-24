# Plugins & Extensions

Extend Sibyl with custom plugins and third-party integrations.

---

## Overview

Sibyl's plugin system allows you to:
- Add custom techniques
- Integrate external services
- Extend core functionality
- Share reusable components

---

## Plugin Types

### 1. Technique Plugins

Add new chunking, embedding, or retrieval strategies.

**Example:**
```python
# my_plugin/custom_chunker.py
from sibyl.core.infrastructure.registry import TechniqueRegistry

class SemanticChunker:
    async def chunk(self, ctx, documents):
        # Implementation
        pass

# Register
TechniqueRegistry.register(
    shop="rag_pipeline",
    technique="chunking",
    subtechnique="semantic",
    implementation="custom",
    factory=lambda cfg: SemanticChunker(cfg)
)
```

### 2. Provider Plugins

Add support for new LLM providers or vector databases.

**Example:**
```python
# my_plugin/custom_provider.py
from sibyl.core.infrastructure.providers import BaseProvider

class CustomLLMProvider(BaseProvider):
    async def generate(self, prompt: str) -> str:
        # Implementation
        pass
```

### 3. MCP Tool Plugins

Expose custom functionality as MCP tools.

See [MCP Integration](../examples/mcp-integration.md)

---

## Installing Plugins

```bash
# From PyPI
pip install sibyl-plugin-name

# From source
pip install -e path/to/plugin

# From git
pip install git+https://github.com/user/sibyl-plugin.git
```

---

## Creating Plugins

See [Plugin Development Guide](./development.md)

---

## Available Plugins

### Official Plugins

- `sibyl-postgres` - PostgreSQL vector storage
- `sibyl-redis` - Redis caching
- `sibyl-openai` - OpenAI provider
- `sibyl-cohere` - Cohere embeddings

### Community Plugins

Browse at: https://github.com/sibyl-ai/awesome-sibyl-plugins

---

## Learn More

- [Plugin Development](./development.md)
- [Plugin Distribution](./distribution.md)
- [Custom Techniques](../techniques/custom-techniques.md)
