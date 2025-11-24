# Sibyl Examples

Comprehensive, realistic examples demonstrating Sibyl's capabilities through fictional companies with authentic business problems.

## Overview

Sibyl examples serve two purposes:
1. **Tutorials**: Learn Sibyl's capabilities through realistic scenarios
2. **Testbed**: Validate Sibyl's techniques and infrastructure with real-world workloads

Each example is built around a fictional company with authentic data and business problems. Examples demonstrate end-to-end workflows using Sibyl's public APIs, techniques, and MCP integrations.

## Important Notice

**All data in this directory is synthetic and generated for demonstration purposes only.**

No real company data, user information, or proprietary content is included. All examples use clearly marked fictional entities, datasets, and scenarios designed to illustrate Sibyl's capabilities while maintaining complete separation from any production systems.

## Structure

```
examples/
├── README.md                    # This file
├── companies/                   # Example companies
│   ├── riverbank_finance/       # Banking compliance & transactions
│   ├── vertex_foundry/          # ML experiment tracking
│   ├── northwind_analytics/     # RAG & document QA (planned)
│   ├── acme_shop/              # Retail forecasting (planned)
│   └── techventures/           # Code analysis (planned)
├── shared/                      # Shared infrastructure
│   ├── mcp/                    # MCP setup and configs
│   │   ├── docker-compose.yaml # Containerized MCPs
│   │   ├── mcp_requirements.md # MCP catalog
│   │   └── mcp_configs/       # Configuration templates
│   └── tooling/                # Benchmarking and testing
│       ├── bench.py           # Benchmarking CLI
│       ├── test_runner.py     # Test aggregator
│       └── README.md
├── basic_web_research/          # Simple examples
├── golden_path/                 # Getting started examples
├── extensions/                  # Extension examples
└── pipelines/                   # Pipeline examples
```

## Example Companies

### Currently Available

#### RiverBank Finance
**Industry**: Banking & Finance
**Focus**: Compliance, transaction monitoring, regulatory reporting

**Learn**: Transaction analysis, regulatory workflows, knowledge graphs, code review

**Scenarios**: Compliance Audit, Transaction Network Analysis

**MCPs**: filesystem, sqlite, graphiti, brave-search

**[→ Full Details](companies/riverbank_finance/README.md)**

---

#### Vertex Foundry
**Industry**: ML Research & Development
**Focus**: Experiment tracking, model analysis, ML operations

**Learn**: ML experiment tracking, model performance analysis, hyperparameter comparison

**Scenarios**: Experiment Tracking, Model Performance Analysis

**MCPs**: filesystem, sqlite, github

**[→ Full Details](companies/vertex_foundry/README.md)**

---

### Coming Soon

- **Northwind Analytics**: RAG pipelines, document QA, semantic search
- **Acme Shop**: Sales forecasting, inventory optimization
- **TechVentures**: Code analysis, technical due diligence

## Quick Start

### 1. Choose an Example

| I want to learn... | Go to... | Time |
|-------------------|----------|------|
| Transaction graphs & compliance | [RiverBank Finance](#riverbank-finance) | 10 min |
| ML experiment tracking | [Vertex Foundry](#vertex-foundry) | 10 min |
| RAG pipelines | Northwind Analytics (coming soon) | 15 min |

### 2. Set Up MCPs

Most examples need external services (MCPs). Quick setup:

```bash
# Start all containerized MCPs (Qdrant, Neo4j, PostgreSQL)
cd examples/shared/mcp
docker-compose up -d
```

For minimal setup, RiverBank and Vertex work with just built-in MCPs (filesystem, sqlite).

See [MCP Setup Guide](../docs/examples/MCP_GUIDE.md) for detailed instructions.

### 3. Run an Example

```bash
# Navigate to company
cd examples/companies/<company-name>

# Follow README for specific setup
cat README.md

# Run a scenario
python scenarios/<scenario-name>/run.py
```

### Quick Command Reference

```bash
# View company overview
cat examples/companies/riverbank_finance/README.md

# Explore data
ls examples/companies/riverbank_finance/data/

# Run workspace
sibyl run --workspace scenarios/<scenario>/workspace.yaml

# Run smoke tests
pytest examples/companies/riverbank_finance/tests/
```

## How Examples Differ from Core Code

| Aspect | Core Sibyl Code | Examples |
|--------|-----------------|----------|
| **Location** | `sibyl/` directory | `examples/` directory |
| **Purpose** | Production framework | Learning & demonstration |
| **Data** | No data included | Synthetic, clearly marked |
| **Imports** | Internal framework code | Public Sibyl APIs only |
| **Testing** | Unit & integration tests | Smoke tests & scenarios |
| **Documentation** | API references | Tutorials & guides |
| **Stability** | Versioned, stable APIs | May evolve with new features |

### Key Principles

1. **No Core Modifications**: Examples never modify `sibyl/core/`, `sibyl/framework/`, `sibyl/runtime/`, or `sibyl/techniques/`
2. **Public API Only**: Examples use only documented, public Sibyl APIs
3. **Self-Contained**: Each company example is independent and complete
4. **Synthetic Data**: All data is clearly marked as fake and for demonstration
5. **Educational Focus**: Code includes extensive comments explaining patterns

## Adding a New Example

To add a new company or modify existing examples, see:

- [Examples Conventions](../../docs/examples/EXAMPLES_CONVENTIONS.md) - Detailed guidelines
- [Template Structure](../../docs/examples/EXAMPLES_CONVENTIONS.md#company-template) - Boilerplate

Quick checklist:

1. Create company directory under `examples/companies/`
2. Follow standard folder structure (data/, config/, scenarios/, tests/)
3. Write comprehensive README.md for the company
4. Add synthetic datasets with clear "FAKE DATA" markers
5. Create workspace.yaml and pipelines.yaml configs
6. Write 2-3 scenario walkthroughs
7. Add smoke tests for validation
8. Update this README with company description

## Testing Examples

### Run All Smoke Tests

```bash
# From project root
python examples/shared/tooling/test_runner.py

# Specific company
python examples/shared/tooling/test_runner.py --company riverbank_finance

# Verbose output
python examples/shared/tooling/test_runner.py --verbose
```

### Run with Pytest

```bash
# All example tests
pytest -m examples

# Specific company
pytest examples/companies/riverbank_finance/tests/

# Specific test
pytest examples/companies/riverbank_finance/tests/test_smoke.py -v
```

## Benchmarking

Track performance across examples:

```bash
# Benchmark all companies
python examples/shared/tooling/bench.py --company all

# Specific companies
python examples/shared/tooling/bench.py --company riverbank_finance vertex_foundry

# Save results
python examples/shared/tooling/bench.py --company all --output results.json

# Compare with baseline
python examples/shared/tooling/bench.py --company all --baseline baseline.json
```

See [Benchmarking Tools](shared/tooling/README.md) for details.

## MCP Setup

### Quick Setup

Start all containerized MCPs:

```bash
cd examples/shared/mcp
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:6333/health  # Qdrant
```

### Individual MCP Setup

Only need specific MCPs? See:
- [MCP Requirements Table](shared/mcp/mcp_requirements.md) - Which examples need which MCPs
- [MCP Guide](../docs/examples/MCP_GUIDE.md) - Comprehensive setup instructions
- [Shared MCP Infrastructure](shared/mcp/README.md) - Docker and configuration

### Common MCPs

| MCP | Purpose | Setup |
|-----|---------|-------|
| filesystem | File I/O | Built-in, no setup |
| sqlite | SQL database | Built-in, no setup |
| qdrant | Vector store | Docker or Qdrant Cloud |
| graphiti | Knowledge graph | Neo4j + Graphiti setup |
| brave-search | Web search | API key required |
| github | Repository access | GitHub token required |

## Troubleshooting

### MCP Connection Issues

```bash
# Check MCP services are running
docker-compose ps

# View logs
docker-compose logs qdrant

# Restart services
docker-compose restart
```

See [MCP Troubleshooting](../docs/examples/MCP_GUIDE.md#troubleshooting) for detailed help.

### Test Failures

```bash
# Run with verbose output
python examples/shared/tooling/test_runner.py --verbose

# Run specific test
pytest examples/companies/riverbank_finance/tests/test_smoke.py -v

# Check for missing dependencies
pip list | grep sibyl
```

### Performance Issues

- Reduce batch sizes in configurations
- Enable MCP connection pooling
- Check Docker resource limits
- See [Performance Guide](../docs/operations/)

## Contributing

### Adding a New Example

1. Follow the standard structure (see [Examples Index](../docs/examples/INDEX.md))
2. Create company directory with:
   - README.md with overview and setup
   - config/workspace.yaml
   - data/ with sample data
   - scenarios/ with runnable scenarios
   - tests/ with smoke tests
3. Add to [Examples Index](../docs/examples/INDEX.md)
4. Document MCP requirements in [MCP Requirements](shared/mcp/mcp_requirements.md)
5. Add smoke tests
6. Submit PR with `examples` label

### Guidelines

- **Use Public APIs Only**: No access to Sibyl internals
- **Realistic Data**: Authentic-looking sample data
- **Clear Documentation**: README for company and each scenario
- **Testable**: Include smoke tests
- **MCP Documentation**: List required and optional MCPs
- **Time Estimates**: Include expected runtime

## Documentation

### Full Documentation
- **[Examples Index](../docs/examples/INDEX.md)** - Complete guide to all examples
- **[MCP Guide](../docs/examples/MCP_GUIDE.md)** - Comprehensive MCP setup and troubleshooting
- **[Main Documentation](../docs/INDEX.md)** - All Sibyl documentation

### Infrastructure Docs
- [Shared MCP Infrastructure](shared/mcp/README.md)
- [MCP Requirements](shared/mcp/mcp_requirements.md)
- [Benchmarking Tools](shared/tooling/README.md)

### Sibyl Core Docs
- [Getting Started](../docs/getting_started.md)
- [Running Pipelines](../docs/running_pipelines.md)
- [Techniques](../docs/techniques/)
- [MCP Integration](../docs/mcp/INDEX.md)

## Prerequisites

- **Python**: 3.11 or higher
- **Sibyl**: Installed (`pip install -e .` from project root)
- **Docker**: For containerized MCPs (optional but recommended)
- **API Keys**: For Brave Search, GitHub (optional, depends on examples)

## Support

- **Documentation**: [Examples Index](../docs/examples/INDEX.md)
- **MCP Help**: [MCP Guide](../docs/examples/MCP_GUIDE.md)
- **Issues**: File bugs in GitHub Issues with `examples` label
- **Discussions**: Ask questions in GitHub Discussions

## What's Next?

After exploring examples:

1. **Adapt for Your Use Case**: Use examples as templates
2. **Extend Examples**: Add your own scenarios
3. **Create Custom Techniques**: Build domain-specific techniques
4. **Integrate New MCPs**: Add capabilities beyond included examples

See [Extending Sibyl](../docs/extending/) for guidance.

---

**Status**: Infrastructure complete, scenarios in development
**Last Updated**: 2025-11-22
**Total Companies**: 5 (2 partial, 3 planned)
**Total Scenarios**: 11+ planned
