# Creating Custom Techniques

Learn how to extend Sibyl by creating your own custom techniques.

## Overview

This guide shows you how to:
- Create custom technique implementations
- Register techniques with the framework
- Use custom techniques in workspaces
- Package and share custom techniques

**Time:** 20 minutes | **Difficulty:** Intermediate

---

## Custom Technique Structure

```
sibyl/techniques/my_shop/my_technique/
├── __init__.py
├── contracts.py          # Input/output contracts
├── protocols.py          # Interface definitions
├── subtechniques/
│   └── my_implementation/
│       ├── custom/       # User customizations
│       │   └── README.md
│       └── default/      # Default implementation
│           ├── __init__.py
│           └── implementation.py
```

---

## Example: Custom Reranker

Let's create a custom reranking technique that uses business rules.

### Step 1: Define Contracts

**contracts.py:**
```python
"""Contracts for custom reranker."""

from dataclasses import dataclass
from typing import List

from sibyl.core.domain.base import BaseModel


@dataclass
class RerankRequest(BaseModel):
    """Request for reranking."""
    query: str
    chunks: List[dict]
    boost_keywords: List[str]  # Boost chunks containing these
    recency_weight: float = 0.2  # Weight for recent documents


@dataclass
class RerankResponse(BaseModel):
    """Response from reranking."""
    reranked_chunks: List[dict]
    scores: List[float]
    boosted_count: int
```

### Step 2: Define Protocol

**protocols.py:**
```python
"""Protocol for custom reranker."""

from typing import Protocol

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import Result

from .contracts import RerankRequest, RerankResponse


class BusinessReranker(Protocol):
    """Protocol for business rules reranker."""

    async def rerank(
        self,
        ctx: ApplicationContext,
        request: RerankRequest
    ) -> Result[RerankResponse]:
        """Rerank chunks using business rules."""
        ...
```

### Step 3: Implement Technique

**subtechniques/business_rerank/default/implementation.py:**
```python
"""Business rules reranker implementation."""

from datetime import datetime
from typing import List

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import Result
from sibyl.techniques.rag_pipeline.reranking.contracts import (
    RerankRequest,
    RerankResponse
)


class BusinessRulesReranker:
    """Reranker using custom business logic."""

    def __init__(self, config: dict):
        self.keyword_boost = config.get("keyword_boost", 2.0)
        self.recency_weight = config.get("recency_weight", 0.2)
        self.min_score = config.get("min_score", 0.0)

    async def rerank(
        self,
        ctx: ApplicationContext,
        request: RerankRequest
    ) -> Result[RerankResponse]:
        """Rerank using business rules."""

        try:
            # Score each chunk
            scored_chunks = []
            for chunk in request.chunks:
                score = self._calculate_score(chunk, request)
                if score >= self.min_score:
                    scored_chunks.append((chunk, score))

            # Sort by score
            scored_chunks.sort(key=lambda x: x[1], reverse=True)

            # Extract results
            reranked = [chunk for chunk, _ in scored_chunks]
            scores = [score for _, score in scored_chunks]

            # Count boosted
            boosted_count = sum(
                1 for chunk in reranked
                if self._contains_keywords(chunk, request.boost_keywords)
            )

            response = RerankResponse(
                reranked_chunks=reranked,
                scores=scores,
                boosted_count=boosted_count
            )

            return Result.success(response)

        except Exception as e:
            return Result.failure(
                error_type="rerank_error",
                message=f"Reranking failed: {str(e)}"
            )

    def _calculate_score(self, chunk: dict, request: RerankRequest) -> float:
        """Calculate score for a chunk."""

        # Base score (from initial retrieval)
        base_score = chunk.get("score", 0.5)

        # Keyword boost
        keyword_score = 0.0
        if self._contains_keywords(chunk, request.boost_keywords):
            keyword_score = self.keyword_boost

        # Recency boost
        recency_score = self._calculate_recency_score(chunk)

        # Combine scores
        final_score = (
            base_score * (1 - request.recency_weight) +
            keyword_score * 0.3 +
            recency_score * request.recency_weight
        )

        return final_score

    def _contains_keywords(self, chunk: dict, keywords: List[str]) -> bool:
        """Check if chunk contains any keywords."""
        content = chunk.get("content", "").lower()
        return any(kw.lower() in content for kw in keywords)

    def _calculate_recency_score(self, chunk: dict) -> float:
        """Calculate recency score based on document date."""

        date_str = chunk.get("metadata", {}).get("date")
        if not date_str:
            return 0.0

        try:
            doc_date = datetime.fromisoformat(date_str)
            now = datetime.now()
            days_old = (now - doc_date).days

            # Exponential decay: newer = higher score
            return max(0.0, 1.0 - (days_old / 365.0))

        except (ValueError, TypeError):
            return 0.0


# Factory function
def create_reranker(config: dict) -> BusinessRulesReranker:
    """Create reranker instance."""
    return BusinessRulesReranker(config)
```

### Step 4: Register Technique

**subtechniques/business_rerank/default/__init__.py:**
```python
"""Register business reranker."""

from sibyl.core.infrastructure.registry import TechniqueRegistry
from .implementation import create_reranker


def register():
    """Register the technique."""
    TechniqueRegistry.register(
        shop="rag_pipeline",
        technique="reranking",
        subtechnique="business_rerank",
        implementation="default",
        factory=create_reranker,
        description="Business rules reranker with keyword and recency boosting"
    )


# Auto-register on import
register()
```

---

## Use Custom Technique

**workspace_config.yaml:**
```yaml
workspace_name: custom_rerank_workspace

shops:
  rag_pipeline:
    reranking:
      technique: business_rerank  # Your custom technique!
      config:
        keyword_boost: 3.0
        recency_weight: 0.3
        min_score: 0.1
```

**usage.py:**
```python
#!/usr/bin/env python3

from sibyl.core.application.context import ApplicationContext
from sibyl.techniques.rag_pipeline import reranking
from sibyl.techniques.rag_pipeline.reranking.contracts import RerankRequest


async def main():
    ctx = ApplicationContext.from_workspace("workspaces/custom_rerank_workspace")

    # Sample chunks
    chunks = [
        {"content": "Product pricing information from 2024", "score": 0.8,
         "metadata": {"date": "2024-05-01"}},
        {"content": "Old pricing data from 2020", "score": 0.7,
         "metadata": {"date": "2020-01-01"}},
        {"content": "Recent pricing update", "score": 0.6,
         "metadata": {"date": "2024-11-01"}},
    ]

    request = RerankRequest(
        query="latest pricing",
        chunks=chunks,
        boost_keywords=["pricing", "recent", "latest"],
        recency_weight=0.3
    )

    result = await reranking.execute(
        ctx=ctx,
        technique="business_rerank",
        params={"request": request}
    )

    if result.is_success:
        response = result.value
        print(f"Reranked {len(response.reranked_chunks)} chunks")
        print(f"Boosted {response.boosted_count} chunks with keywords")

        for i, (chunk, score) in enumerate(
            zip(response.reranked_chunks, response.scores), 1
        ):
            print(f"{i}. [{score:.2f}] {chunk['content'][:50]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Testing Custom Techniques

**test_business_reranker.py:**
```python
"""Tests for business reranker."""

import pytest
from datetime import datetime, timedelta

from sibyl.techniques.rag_pipeline.reranking.subtechniques.business_rerank.default import (
    create_reranker
)


@pytest.mark.asyncio
async def test_keyword_boosting():
    """Test keyword boosting."""

    reranker = create_reranker({"keyword_boost": 2.0})

    chunks = [
        {"content": "Contains keyword pricing", "score": 0.5},
        {"content": "No keywords here", "score": 0.5},
    ]

    request = RerankRequest(
        query="pricing",
        chunks=chunks,
        boost_keywords=["pricing"]
    )

    result = await reranker.rerank(None, request)

    assert result.is_success
    # Chunk with keyword should rank higher
    assert result.value.reranked_chunks[0]["content"] == "Contains keyword pricing"


@pytest.mark.asyncio
async def test_recency_scoring():
    """Test recency scoring."""

    reranker = create_reranker({"recency_weight": 0.5})

    today = datetime.now().isoformat()
    old_date = (datetime.now() - timedelta(days=365)).isoformat()

    chunks = [
        {"content": "Old doc", "score": 0.8, "metadata": {"date": old_date}},
        {"content": "New doc", "score": 0.6, "metadata": {"date": today}},
    ]

    request = RerankRequest(
        query="test",
        chunks=chunks,
        boost_keywords=[],
        recency_weight=0.5
    )

    result = await reranker.rerank(None, request)

    assert result.is_success
    # Newer document should rank higher despite lower base score
    assert result.value.reranked_chunks[0]["content"] == "New doc"
```

---

## Packaging Custom Techniques

Create a distributable package:

**setup.py:**
```python
from setuptools import setup, find_packages

setup(
    name="sibyl-custom-rerankers",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sibyl-core>=0.1.0",
    ],
    entry_points={
        "sibyl.techniques": [
            "business_rerank = my_package.business_rerank:register",
        ],
    },
)
```

Install and use:
```bash
pip install sibyl-custom-rerankers
```

---

## Best Practices

1. **Follow Contracts:** Always use proper input/output contracts
2. **Error Handling:** Return `Result.failure()` for errors
3. **Configuration:** Make techniques configurable via `config` dict
4. **Testing:** Write comprehensive tests
5. **Documentation:** Include clear README in `custom/` folder
6. **Type Hints:** Use type hints for better IDE support

---

## Learn More

- [Technique Catalog](../techniques/catalog.md)
- [Custom Techniques Guide](../techniques/custom-techniques.md)
- [Development Guide](../development/testing-guide.md)
