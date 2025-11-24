# Testing Guide

Comprehensive guide to testing Sibyl applications and custom techniques.

---

## Overview

This guide covers:
- Unit testing techniques
- Integration testing
- Testing custom implementations
- Mocking and fixtures
- Test organization
- CI/CD integration

---

## Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── techniques/
│   │   ├── test_chunking.py
│   │   ├── test_embedding.py
│   │   └── test_retrieval.py
│   ├── core/
│   │   ├── test_context.py
│   │   └── test_config.py
│   └── infrastructure/
│       ├── test_cache.py
│       └── test_state.py
├── integration/            # Integration tests
│   ├── test_rag_pipeline.py
│   ├── test_sql_agent.py
│   └── test_mcp_server.py
├── e2e/                    # End-to-end tests
│   └── test_workflows.py
├── fixtures/               # Shared fixtures
│   ├── sample_docs.py
│   └── test_data.py
└── conftest.py            # Pytest configuration
```

---

## Unit Testing

### Testing Techniques

**tests/unit/techniques/test_chunking.py:**
```python
"""Unit tests for chunking techniques."""

import pytest

from sibyl.techniques.rag_pipeline.chunking.subtechniques.fixed_size.default import (
    FixedSizeChunker
)
from sibyl.core.domain.contracts import Document


@pytest.fixture
def sample_document():
    """Create sample document for testing."""
    return Document(
        id="doc1",
        content="This is a test document. " * 100,  # Long content
        metadata={"source": "test.md"}
    )


@pytest.fixture
def chunker():
    """Create chunker instance."""
    return FixedSizeChunker(config={
        "chunk_size": 100,
        "chunk_overlap": 20
    })


@pytest.mark.asyncio
async def test_fixed_size_chunking(chunker, sample_document):
    """Test basic fixed-size chunking."""

    result = await chunker.chunk(None, [sample_document])

    assert result.is_success
    chunks = result.value

    # Verify chunks created
    assert len(chunks) > 1

    # Verify chunk sizes
    for chunk in chunks[:-1]:  # All but last
        assert len(chunk.content) <= 100

    # Verify overlap
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i].content[-20:]
        chunk2_start = chunks[i + 1].content[:20]
        # Should have some overlap
        assert len(set(chunk1_end.split()) & set(chunk2_start.split())) > 0


@pytest.mark.asyncio
async def test_empty_document(chunker):
    """Test handling of empty document."""

    empty_doc = Document(id="empty", content="", metadata={})

    result = await chunker.chunk(None, [empty_doc])

    assert result.is_success
    assert len(result.value) == 0  # No chunks from empty doc


@pytest.mark.asyncio
async def test_invalid_config():
    """Test invalid configuration handling."""

    with pytest.raises(ValueError):
        FixedSizeChunker(config={"chunk_size": -1})


@pytest.mark.parametrize("chunk_size,overlap,expected_chunks", [
    (50, 10, 10),
    (100, 20, 5),
    (200, 50, 3),
])
@pytest.mark.asyncio
async def test_different_configurations(
    sample_document,
    chunk_size,
    overlap,
    expected_chunks
):
    """Test chunking with different configurations."""

    chunker = FixedSizeChunker(config={
        "chunk_size": chunk_size,
        "chunk_overlap": overlap
    })

    result = await chunker.chunk(None, [sample_document])

    assert result.is_success
    assert len(result.value) == pytest.approx(expected_chunks, rel=0.2)
```

### Testing Core Components

**tests/unit/core/test_context.py:**
```python
"""Tests for ApplicationContext."""

import pytest
from pathlib import Path

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.config import WorkspaceConfig


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace."""

    workspace_dir = tmp_path / "test_workspace"
    workspace_dir.mkdir()

    config = {
        "workspace_name": "test",
        "shops": {
            "rag_pipeline": {
                "retrieval": {
                    "technique": "semantic_search",
                    "config": {"top_k": 5}
                }
            }
        }
    }

    config_file = workspace_dir / "workspace_config.yaml"
    import yaml
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return workspace_dir


def test_context_from_workspace(temp_workspace):
    """Test context creation from workspace."""

    ctx = ApplicationContext.from_workspace(str(temp_workspace))

    assert ctx.workspace_name == "test"
    assert "rag_pipeline" in ctx.config.shops


def test_get_technique_config(temp_workspace):
    """Test retrieving technique configuration."""

    ctx = ApplicationContext.from_workspace(str(temp_workspace))

    config = ctx.get_technique_config(
        shop="rag_pipeline",
        technique="retrieval",
        subtechnique="semantic_search"
    )

    assert config is not None
    assert config.get("top_k") == 5


def test_missing_workspace():
    """Test handling of missing workspace."""

    with pytest.raises(FileNotFoundError):
        ApplicationContext.from_workspace("/nonexistent/workspace")
```

---

## Integration Testing

### Testing RAG Pipeline

**tests/integration/test_rag_pipeline.py:**
```python
"""Integration tests for RAG pipeline."""

import pytest
from pathlib import Path

from sibyl.core.application.context import ApplicationContext
from sibyl.techniques.data_integration import load_documents
from sibyl.techniques.rag_pipeline import chunking, embedding, retrieval


@pytest.fixture(scope="module")
async def indexed_workspace(tmp_path_factory):
    """Create and index a test workspace."""

    workspace = tmp_path_factory.mktemp("workspace")

    # Create test documents
    docs_dir = workspace / "data" / "docs"
    docs_dir.mkdir(parents=True)

    (docs_dir / "doc1.md").write_text("This is test document 1 about pricing.")
    (docs_dir / "doc2.md").write_text("This is test document 2 about features.")

    # Create config
    config = {
        "workspace_name": "test",
        "data_paths": {
            "documents": [{"path": "data/docs"}]
        },
        "shops": {
            "rag_pipeline": {
                "chunking": {
                    "technique": "fixed_size",
                    "config": {"chunk_size": 100}
                },
                "embedding": {
                    "technique": "sentence_transformer",
                    "config": {"model_name": "all-MiniLM-L6-v2"}
                },
                "retrieval": {
                    "technique": "semantic_search",
                    "config": {"top_k": 3}
                }
            }
        }
    }

    import yaml
    (workspace / "workspace_config.yaml").write_text(yaml.dump(config))

    # Load and index
    ctx = ApplicationContext.from_workspace(str(workspace))

    docs_result = await load_documents.execute(
        ctx=ctx,
        technique="loader",
        params={"source": "workspace"}
    )

    chunks_result = await chunking.execute(
        ctx=ctx,
        technique="fixed_size",
        params={"documents": docs_result.value}
    )

    embeddings_result = await embedding.execute(
        ctx=ctx,
        technique="sentence_transformer",
        params={"chunks": chunks_result.value}
    )

    # Store (would normally go to vector DB)
    ctx.vector_store = {
        "chunks": chunks_result.value,
        "embeddings": embeddings_result.value
    }

    return ctx


@pytest.mark.asyncio
async def test_end_to_end_retrieval(indexed_workspace):
    """Test end-to-end retrieval."""

    result = await retrieval.execute(
        ctx=indexed_workspace,
        technique="semantic_search",
        params={"query": "What is the pricing?"}
    )

    assert result.is_success
    chunks = result.value

    assert len(chunks) > 0
    # Should retrieve document about pricing
    assert any("pricing" in chunk.content.lower() for chunk in chunks)


@pytest.mark.asyncio
async def test_retrieval_threshold(indexed_workspace):
    """Test similarity threshold filtering."""

    result = await retrieval.execute(
        ctx=indexed_workspace,
        technique="semantic_search",
        params={
            "query": "completely unrelated query xyz",
            "similarity_threshold": 0.8  # High threshold
        }
    )

    assert result.is_success
    # Should return fewer results due to high threshold
    assert len(result.value) <= 1
```

---

## Mocking and Fixtures

### Mocking External Services

**tests/fixtures/mock_providers.py:**
```python
"""Mock providers for testing."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client."""

    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text="Mocked response")],
        usage=MagicMock(input_tokens=10, output_tokens=20)
    ))

    return client


@pytest.fixture
def mock_vector_db():
    """Mock vector database."""

    db = MagicMock()
    db.search = AsyncMock(return_value=[
        {"id": "1", "score": 0.9, "content": "Result 1"},
        {"id": "2", "score": 0.8, "content": "Result 2"},
    ])
    db.insert = AsyncMock(return_value=True)

    return db


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model."""

    import numpy as np

    model = MagicMock()
    model.encode = MagicMock(return_value=np.random.rand(5, 384))

    return model
```

**Usage:**
```python
@pytest.mark.asyncio
async def test_with_mock_client(mock_anthropic_client):
    """Test using mocked Anthropic client."""

    # Inject mock
    from sibyl.core.infrastructure.providers import anthropic
    anthropic._client = mock_anthropic_client

    # Run test
    response = await anthropic.generate("test prompt")

    # Verify
    assert response == "Mocked response"
    mock_anthropic_client.messages.create.assert_called_once()
```

---

## Testing Custom Techniques

**tests/unit/custom/test_custom_reranker.py:**
```python
"""Tests for custom reranker."""

import pytest
from datetime import datetime, timedelta

from my_custom.reranker import BusinessRulesReranker


@pytest.fixture
def reranker():
    return BusinessRulesReranker(config={
        "keyword_boost": 2.0,
        "recency_weight": 0.3
    })


@pytest.mark.asyncio
async def test_keyword_boost(reranker):
    """Test keyword boosting logic."""

    chunks = [
        {"content": "Document about pricing", "score": 0.5},
        {"content": "Unrelated document", "score": 0.6},
    ]

    result = await reranker.rerank(
        ctx=None,
        request={
            "chunks": chunks,
            "boost_keywords": ["pricing"]
        }
    )

    assert result.is_success
    # Boosted document should rank first
    assert "pricing" in result.value[0]["content"]


@pytest.mark.asyncio
async def test_recency_scoring(reranker):
    """Test recency-based scoring."""

    today = datetime.now().isoformat()
    old = (datetime.now() - timedelta(days=365)).isoformat()

    chunks = [
        {
            "content": "Old doc",
            "score": 0.9,
            "metadata": {"date": old}
        },
        {
            "content": "New doc",
            "score": 0.5,
            "metadata": {"date": today}
        },
    ]

    result = await reranker.rerank(
        ctx=None,
        request={"chunks": chunks, "boost_keywords": []}
    )

    assert result.is_success
    # Recent document should rank higher
    assert "New" in result.value[0]["content"]
```

---

## Test Data Management

**tests/fixtures/sample_docs.py:**
```python
"""Sample documents for testing."""

SAMPLE_DOCS = [
    {
        "id": "doc1",
        "content": "Python is a programming language.",
        "metadata": {"source": "python.md", "category": "programming"}
    },
    {
        "id": "doc2",
        "content": "Machine learning is a subset of AI.",
        "metadata": {"source": "ml.md", "category": "ai"}
    },
    {
        "id": "doc3",
        "content": "RAG combines retrieval and generation.",
        "metadata": {"source": "rag.md", "category": "ai"}
    },
]


def get_sample_documents():
    """Get sample documents for testing."""
    from sibyl.core.domain.contracts import Document
    return [Document(**doc) for doc in SAMPLE_DOCS]
```

---

## CI/CD Integration

### GitHub Actions

**.github/workflows/test.yml:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run linting
      run: |
        ruff check .
        mypy sibyl

    - name: Run tests
      run: |
        pytest tests/ -v --cov=sibyl --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### pytest Configuration

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"

# Coverage
addopts = """
    --strict-markers
    --cov=sibyl
    --cov-report=term-missing
    --cov-report=html
    -v
"""

markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
]
```

---

## Performance Testing

**tests/performance/test_retrieval_performance.py:**
```python
"""Performance tests for retrieval."""

import pytest
import time


@pytest.mark.slow
@pytest.mark.asyncio
async def test_retrieval_latency(indexed_workspace):
    """Test retrieval latency."""

    queries = ["test query"] * 100

    start = time.time()

    for query in queries:
        await retrieval.execute(
            ctx=indexed_workspace,
            technique="semantic_search",
            params={"query": query}
        )

    elapsed = time.time() - start

    # Should average under 100ms per query
    avg_latency = elapsed / len(queries)
    assert avg_latency < 0.1, f"Average latency too high: {avg_latency:.3f}s"


@pytest.mark.slow
def test_embedding_throughput(sample_documents):
    """Test embedding throughput."""

    chunks = ["test chunk"] * 1000

    start = time.time()

    # Embed in batches
    model.encode(chunks, batch_size=32)

    elapsed = time.time() - start

    # Should process at least 100 chunks/second
    throughput = len(chunks) / elapsed
    assert throughput > 100, f"Throughput too low: {throughput:.1f} chunks/s"
```

---

## Best Practices

1. **Test Isolation:** Each test should be independent
2. **Use Fixtures:** Share setup code with pytest fixtures
3. **Mock External Calls:** Don't hit real APIs in tests
4. **Test Edge Cases:** Empty inputs, invalid configs, errors
5. **Use Parametrize:** Test multiple scenarios efficiently
6. **Async Tests:** Use `@pytest.mark.asyncio` for async code
7. **Coverage:** Aim for >80% code coverage
8. **Fast Tests:** Keep unit tests fast (<1s each)

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_chunking.py

# Run specific test
pytest tests/unit/test_chunking.py::test_fixed_size_chunking

# Run with coverage
pytest --cov=sibyl --cov-report=html

# Run only fast tests
pytest -m "not slow"

# Run in parallel
pytest -n auto

# Run with verbose output
pytest -v -s
```

---

## Next Steps

- [Code Style Guide](./code-style.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [CI/CD Setup](../operations/deployment.md#cicd)
