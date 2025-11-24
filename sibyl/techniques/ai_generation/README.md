# AI Generation

This category contains techniques for AI content generation, consensus mechanisms,
and output validation.

## Overview

AI generation techniques handle the core generation process, including multi-model consensus,
voting mechanisms, output formatting, and validation.

## Techniques

- **consensus**: Consensus mechanisms
- **formatting**: Output formatting
- **generation**: AI generation
- **validation**: Output validation
- **voting**: Voting mechanisms

## Architecture

```
Generation Request → Generator(s) → Consensus/Voting → Formatting → Validation
                          ↓              ↓                ↓            ↓
                    Multi-Model    Vote Aggregation   Structured   Quality
                    Calls          & Resolution       Output       Checks
```

## Usage

```python
from sibyl.techniques.ai_generation.generation import GenerationTechnique
from sibyl.techniques.ai_generation.consensus import ConsensusTechnique
from sibyl.techniques.ai_generation.validation import ValidationTechnique

# Generate with consensus
generator = GenerationTechnique(...)
consensus = ConsensusTechnique(...)
validator = ValidationTechnique(...)
```

## Core Integration

Core engines for these techniques are located in:
- `sibyl/core/ai_generation/`

The generation engine coordinates multi-model calls and consensus resolution.
