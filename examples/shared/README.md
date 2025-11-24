# Shared Resources for Sibyl Examples

This directory contains shared resources used across multiple company examples.

## Structure

```
shared/
├── mcp/         # Mock MCP servers for testing
├── datasets/    # Reusable synthetic datasets
├── tooling/     # Helper scripts and utilities
└── README.md    # This file
```

## Purpose

The shared resources help:
1. Avoid duplication across company examples
2. Provide consistent testing infrastructure
3. Enable rapid development of new examples
4. Share common patterns and utilities

## Contents

### mcp/

Mock Model Context Protocol (MCP) servers for testing examples without external dependencies.

**Status**: To be populated as needed by company tracks

**Expected Contents**:
- Mock SQL database MCP server
- Mock document storage MCP server
- Mock embedding service MCP
- Mock LLM service MCP

See [mcp/README.md](./mcp/README.md) when available.

### datasets/

Reusable synthetic datasets that can be used across multiple companies.

**Status**: To be populated as patterns emerge

**Expected Contents**:
- Common name/email generators
- Geographic data (cities, ZIP codes, addresses)
- Product taxonomies and categories
- Time-series data templates
- Generic transaction patterns

See [datasets/README.md](./datasets/README.md) when available.

### tooling/

Helper scripts and utilities for working with examples.

**Status**: Partially populated

**Available**:
- `run_example.py` - Run company examples with proper configuration

**Planned**:
- `validate_example.py` - Validate example structure and conformance
- `generate_company.py` - Bootstrap new company example
- `test_all_examples.py` - Run all example tests

See [tooling/README.md](./tooling/README.md) for usage.

## Using Shared Resources

### From Company Examples

Company examples can reference shared resources:

```python
# In company example code
from pathlib import Path

# Reference shared datasets
shared_dir = Path(__file__).parent.parent.parent / "shared"
datasets_dir = shared_dir / "datasets"

# Use shared data generator
from examples.shared.datasets import generate_fake_customers
```

### In Workspace Configs

Reference shared MCPs in workspace.yaml:

```yaml
mcps:
  mock_db:
    type: "mock"
    config:
      mock_server_path: "../../../shared/mcp/mock_sql_server.py"
```

## Contributing

### Adding Mock MCPs

When adding a mock MCP:

1. Create server implementation in `mcp/`
2. Document configuration in `mcp/README.md`
3. Add example usage to this README
4. Test with at least one company example

### Adding Shared Datasets

When adding reusable data:

1. Ensure data is clearly synthetic
2. Add generation functions to `datasets/`
3. Document in `datasets/README.md`
4. Show usage example

### Adding Tooling

When adding helper scripts:

1. Make scripts executable (`chmod +x`)
2. Add comprehensive `--help` text
3. Document in `tooling/README.md`
4. Test across multiple examples

## Design Principles

1. **Minimal Dependencies**: Shared resources should have minimal external dependencies
2. **Clear Abstractions**: Each shared component should have a clear, single purpose
3. **Easy Integration**: Should be trivial to use from company examples
4. **Well Documented**: Each component must be thoroughly documented
5. **Tested**: Shared components should have their own tests

## Versioning

Shared resources evolve with the examples framework:
- Breaking changes should be coordinated across all company examples
- Deprecations should be announced in this README
- Version compatibility noted in docs

## Questions

For questions about shared resources:
1. Check relevant subdirectory README
2. Review company examples for usage patterns
3. Consult [EXAMPLES_CONVENTIONS.md](../../docs/examples/EXAMPLES_CONVENTIONS.md)

---

**Last Updated**: 2025-11-22
