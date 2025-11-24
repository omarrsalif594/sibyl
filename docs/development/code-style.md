# Code Style Guide

Coding standards and best practices for contributing to Sibyl.

---

## Overview

This guide ensures consistency, maintainability, and quality across the Sibyl codebase.

**Key Principles:**
- Clarity over cleverness
- Explicit over implicit
- Simple over complex
- Tested and documented

---

## Python Style

### PEP 8 Compliance

We follow [PEP 8](https://pep8.org/) with these additions:

```python
# Line length: 88 characters (Black default)
# Use 4 spaces for indentation (no tabs)
# 2 blank lines between top-level functions/classes
# 1 blank line between methods


# Good
class MyClass:
    """Class docstring."""

    def __init__(self):
        """Initialize."""
        self.value = 0

    def method(self):
        """Method docstring."""
        pass


# Bad - inconsistent spacing
class MyClass:
    def __init__(self):
        self.value=0
    def method(self):
        pass
```

### Type Hints

Use type hints for all public APIs:

```python
from typing import List, Optional, Dict, Any


# Good - clear types
async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks."""
    ...


# Bad - no type hints
async def retrieve_chunks(query, top_k=5, threshold=None):
    """Retrieve relevant chunks."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_score(
    base_score: float,
    boost: float = 1.0,
    penalty: float = 0.0
) -> float:
    """Calculate final score with boost and penalty.

    The final score is calculated as:
        final = (base_score * boost) - penalty

    Args:
        base_score: The initial score value
        boost: Multiplicative boost factor. Defaults to 1.0
        penalty: Additive penalty value. Defaults to 0.0

    Returns:
        The calculated final score

    Raises:
        ValueError: If base_score is negative

    Examples:
        >>> calculate_score(0.8, boost=1.5)
        1.2

        >>> calculate_score(0.5, penalty=0.1)
        0.4
    """
    if base_score < 0:
        raise ValueError("base_score must be non-negative")

    return (base_score * boost) - penalty
```

### Naming Conventions

```python
# Classes: PascalCase
class ChunkingStrategy:
    pass


# Functions/methods: snake_case
def process_document(doc: Document) -> List[Chunk]:
    pass


# Constants: UPPER_SNAKE_CASE
MAX_CHUNK_SIZE = 1024
DEFAULT_OVERLAP = 50


# Private members: leading underscore
class MyClass:
    def __init__(self):
        self._internal_state = {}

    def _private_method(self):
        pass


# Protected members: single underscore
class BaseClass:
    def _protected_method(self):
        """Intended for subclass use."""
        pass
```

---

## Code Organization

### Module Structure

```python
"""Module docstring explaining purpose.

This module provides chunking functionality for splitting
documents into smaller pieces for processing.
"""

# Standard library imports
import asyncio
from pathlib import Path
from typing import List, Optional

# Third-party imports
import numpy as np
from pydantic import BaseModel

# Local imports
from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import Result
from sibyl.techniques.base import BaseTechnique


# Constants
DEFAULT_CHUNK_SIZE = 512


# Classes
class Chunker(BaseTechnique):
    """Main chunker class."""
    pass


# Functions
def split_text(text: str, size: int) -> List[str]:
    """Split text into chunks."""
    pass
```

### File Organization

```
sibyl/techniques/my_shop/my_technique/
├── __init__.py              # Public API
├── contracts.py             # Data contracts
├── protocols.py             # Interfaces
├── exceptions.py            # Custom exceptions
├── subtechniques/
│   └── implementation/
│       └── default/
│           ├── __init__.py
│           ├── strategy.py  # Main logic
│           ├── utils.py     # Helper functions
│           └── config.py    # Configuration
```

---

## Design Patterns

### Result Pattern

Always use `Result` for operations that can fail:

```python
from sibyl.core.domain.contracts import Result


# Good
async def load_document(path: str) -> Result[Document]:
    """Load document from path."""
    try:
        with open(path) as f:
            content = f.read()
        doc = Document(content=content)
        return Result.success(doc)
    except FileNotFoundError:
        return Result.failure(
            error_type="file_not_found",
            message=f"Document not found: {path}"
        )


# Bad - raises exceptions
async def load_document(path: str) -> Document:
    """Load document from path."""
    with open(path) as f:  # Can raise exception
        content = f.read()
    return Document(content=content)
```

### Dependency Injection

Use `ApplicationContext` for dependencies:

```python
# Good
class ChunkingStrategy:
    """Stateless chunking strategy."""

    async def chunk(
        self,
        ctx: ApplicationContext,
        documents: List[Document]
    ) -> Result[List[Chunk]]:
        """Chunk documents using context config."""
        config = ctx.get_technique_config(
            shop="rag_pipeline",
            technique="chunking"
        )
        ...


# Bad - hard-coded dependencies
class ChunkingStrategy:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def chunk(self, documents: List[Document]) -> List[Chunk]:
        ...
```

### Protocol-Based Design

Define interfaces with Protocols:

```python
from typing import Protocol

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import Result


class Chunker(Protocol):
    """Protocol for chunking strategies."""

    async def chunk(
        self,
        ctx: ApplicationContext,
        documents: List[Document]
    ) -> Result[List[Chunk]]:
        """Split documents into chunks."""
        ...


# Implementations follow the protocol
class FixedSizeChunker:
    """Fixed-size chunking implementation."""

    async def chunk(
        self,
        ctx: ApplicationContext,
        documents: List[Document]
    ) -> Result[List[Chunk]]:
        """Implementation."""
        ...
```

---

## Error Handling

### Error Types

```python
# Use specific error types
return Result.failure(
    error_type="validation_error",
    message="Chunk size must be positive",
    details={"chunk_size": chunk_size}
)


# Common error types
ERROR_TYPES = {
    "validation_error": "Input validation failed",
    "configuration_error": "Invalid configuration",
    "execution_error": "Execution failed",
    "timeout_error": "Operation timed out",
    "not_found_error": "Resource not found",
}
```

### Exception Handling

```python
# Good - specific exceptions, clear error messages
try:
    result = await expensive_operation()
except TimeoutError as e:
    return Result.failure(
        error_type="timeout_error",
        message=f"Operation timed out after {timeout}s",
        details={"timeout": timeout, "operation": "expensive_operation"}
    )
except ValueError as e:
    return Result.failure(
        error_type="validation_error",
        message=f"Invalid value: {e}",
        details={"error": str(e)}
    )


# Bad - bare except, no context
try:
    result = await expensive_operation()
except:
    return Result.failure("error", "Something went wrong")
```

---

## Async Best Practices

```python
# Good - properly awaited
async def process_documents(docs: List[Document]) -> List[Result]:
    """Process documents concurrently."""
    tasks = [process_single(doc) for doc in docs]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# Good - async context manager
async def with_connection():
    """Use async context manager."""
    async with get_connection() as conn:
        result = await conn.query("SELECT * FROM table")
    return result


# Bad - not awaited
async def process_documents(docs: List[Document]):
    results = [process_single(doc) for doc in docs]  # Not awaited!
    return results


# Bad - blocking call in async function
async def load_data():
    import time
    time.sleep(5)  # Blocks event loop!
    return data
```

---

## Configuration

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""

    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: Optional[int] = None
    max_chunks: Optional[int] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        if self.min_chunk_size and self.min_chunk_size > self.chunk_size:
            raise ValueError("min_chunk_size cannot exceed chunk_size")


# Usage
config = ChunkingConfig(chunk_size=1024, chunk_overlap=100)
```

---

## Testing

```python
import pytest


class TestChunking:
    """Tests for chunking functionality."""

    @pytest.fixture
    def chunker(self):
        """Create chunker instance."""
        return FixedSizeChunker(config={"chunk_size": 100})

    @pytest.mark.asyncio
    async def test_basic_chunking(self, chunker):
        """Test basic chunking behavior."""
        doc = Document(content="x" * 300)

        result = await chunker.chunk(None, [doc])

        assert result.is_success
        assert len(result.value) == 3

    @pytest.mark.asyncio
    async def test_empty_document(self, chunker):
        """Test empty document handling."""
        doc = Document(content="")

        result = await chunker.chunk(None, [doc])

        assert result.is_success
        assert len(result.value) == 0

    @pytest.mark.parametrize("size,expected", [
        (50, 6),
        (100, 3),
        (200, 2),
    ])
    @pytest.mark.asyncio
    async def test_different_sizes(self, size, expected):
        """Test various chunk sizes."""
        chunker = FixedSizeChunker(config={"chunk_size": size})
        doc = Document(content="x" * 300)

        result = await chunker.chunk(None, [doc])

        assert len(result.value) == expected
```

---

## Logging

```python
import logging

logger = logging.getLogger(__name__)


# Good - structured logging with context
async def process_query(query: str) -> Result[str]:
    """Process query."""
    logger.info(
        "Processing query",
        extra={
            "query_length": len(query),
            "query_hash": hash(query),
        }
    )

    try:
        result = await execute_query(query)
        logger.info(
            "Query processed successfully",
            extra={"result_count": len(result)}
        )
        return Result.success(result)

    except Exception as e:
        logger.error(
            "Query processing failed",
            extra={"error": str(e), "query": query},
            exc_info=True
        )
        return Result.failure("execution_error", str(e))


# Bad - unstructured logging
async def process_query(query: str):
    print(f"Processing {query}")  # Don't use print!
    result = await execute_query(query)
    print("Done")
    return result
```

---

## Code Review Checklist

- [ ] Type hints on all public functions
- [ ] Docstrings on all public APIs
- [ ] Tests for new functionality
- [ ] Error handling uses Result pattern
- [ ] Async functions properly awaited
- [ ] No blocking calls in async code
- [ ] Configuration is validated
- [ ] Logging at appropriate levels
- [ ] No hardcoded values
- [ ] Code is formatted (Black/Ruff)
- [ ] No unused imports
- [ ] Type checking passes (mypy)

---

## Tools

### Formatting

```bash
# Black (code formatter)
black sibyl/

# Ruff (linter)
ruff check sibyl/ --fix

# isort (import sorting)
isort sibyl/
```

### Type Checking

```bash
# mypy
mypy sibyl/
```

### Pre-commit Hooks

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.254
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

Install:
```bash
pre-commit install
```

---

## Next Steps

- [Testing Guide](./testing-guide.md)
- [Contributing](../../CONTRIBUTING.md)
- [API Reference](../api/core.md)
