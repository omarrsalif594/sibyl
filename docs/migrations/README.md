# Migration Guides

Guides for migrating between Sibyl versions and from other frameworks.

---

## Version Migrations

### Upgrading to v0.2.x from v0.1.x

**Breaking Changes:**
- Configuration format updated
- Some technique names changed
- Result pattern now required

**Migration Steps:**

1. **Update configuration:**
```yaml
# Old (v0.1.x)
techniques:
  chunking: "fixed_size"

# New (v0.2.x)
shops:
  rag_pipeline:
    chunking:
      technique: fixed_size
```

2. **Update imports:**
```python
# Old
from sibyl.chunking import chunk_documents

# New
from sibyl.techniques.rag_pipeline import chunking
```

3. **Handle Results:**
```python
# Old
chunks = await chunk_documents(docs)

# New
result = await chunking.execute(ctx, technique="fixed_size", params={"documents": docs})
if result.is_success:
    chunks = result.value
```

---

## Framework Migrations

### From LangChain

**Key Differences:**
- Sibyl uses workspace configuration vs LangChain's chains
- Technique-based architecture vs component-based
- Built-in MCP support

**Migration Example:**

```python
# LangChain
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA

vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
qa = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())
answer = qa.run(query)

# Sibyl
ctx = ApplicationContext.from_workspace("workspace")
result = await retrieval.execute(ctx, technique="semantic_search", params={"query": query})
```

### From LlamaIndex

**Key Differences:**
- Workspace configuration vs programmatic setup
- Technique catalog vs custom nodes
- Focus on production deployment

**Migration Example:**

```python
# LlamaIndex
from llama_index import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader('data').load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query(query)

# Sibyl
# Configure in workspace_config.yaml, then:
result = await retrieval.execute(ctx, technique="semantic_search", params={"query": query})
```

---

## Database Migrations

State management schema migrations are automatic. To manually migrate:

```bash
sibyl migrate --workspace path/to/workspace
```

---

## Learn More

- [Configuration Reference](../workspaces/configuration.md)
- [Techniques Catalog](../techniques/catalog.md)
- [Changelog](../../CHANGELOG.md)
