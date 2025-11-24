# Infrastructure

This category contains foundational infrastructure techniques for resource management,
security, resilience, and system optimization.

## Overview

Infrastructure techniques provide the foundational capabilities needed by all other categories,
including budget management, rate limiting, caching, security, and monitoring.

## Techniques

- **budget_allocation**: Budget allocation
- **caching**: Caching mechanisms
- **checkpointing**: Checkpointing
- **evaluation**: Evaluation metrics
- **learning**: Learning systems
- **rate_limiting**: Rate limiting
- **resilience**: Resilience patterns
- **scoring**: Scoring mechanisms
- **security**: Security features
- **security_validation**: Security validation
- **storage**: Storage backends
- **workflow_optimization**: Workflow optimization

## Architecture

```
Application Layer
     ↓
Infrastructure Layer (this category)
     ↓
- Budget & Rate Limiting
- Caching & Storage
- Security & Validation
- Resilience & Recovery
- Evaluation & Scoring
- Learning & Optimization
```

## Usage

```python
from sibyl.techniques.infrastructure.budget_allocation import BudgetAllocationTechnique
from sibyl.techniques.infrastructure.caching import CachingTechnique
from sibyl.techniques.infrastructure.security import SecurityTechnique

# Configure infrastructure
budget = BudgetAllocationTechnique(...)
cache = CachingTechnique(...)
security = SecurityTechnique(...)
```

## Core Integration

Core engines for these techniques are located in:
- `sibyl/core/infrastructure/`

Infrastructure techniques are typically configured globally and used by all other components.
