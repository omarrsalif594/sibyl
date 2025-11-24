# RiverBank Finance - Compliance Analysis Example

Demonstrates code compliance checking (AST) and AML risk detection (Graph analysis) for fintech/banking.

## Quick Start

### Prerequisites

```bash
# Install MCP servers
pip install mcp-code-analyzer graphiti-mcp

# Set API key
export OPENAI_API_KEY="your-key-here"
```

### Run Tests

```bash
# All RiverBank tests (no MCP required for basic tests)
pytest tests/examples/test_riverbank_finance.py -v -m "riverbank and not requires_mcp"

# Full suite with MCP servers
pytest tests/examples/test_riverbank_finance.py -v -m riverbank
```

## Structure

```
riverbank_finance/
├── config/
│   └── workspace.yaml          # Workspace configuration with 3 pipelines
├── data/
│   ├── code/                   # Banking code with intentional bugs
│   │   ├── interest_calculator.py    # 2 bugs (compound formula, day count)
│   │   ├── transaction_processor.js  # 1 velocity bug
│   │   └── risk_scorer.py           # 1 variance threshold bug
│   ├── docs/                   # Policy documents for RAG
│   │   ├── interest_rate_policy.md   # INT-001, INT-002, INT-003
│   │   ├── aml_policy.md            # AML-001, AML-002
│   │   ├── kyc_policy.md            # KYC-001, KYC-002
│   │   └── transaction_limits.md    # TXN-001, TXN-003
│   └── transactions/           # Synthetic transaction data
│       └── transactions.json   # 1000 txns, 10 customers, 4 suspicious patterns
├── expected/                   # Golden snapshots
│   └── code_policy_check.json # Expected compliance report
├── tests/
│   └── test_smoke.py          # Data validation smoke tests
└── README.md                   # This file
```

## Scenarios

### 1. Code Compliance Check

**Pipeline**: `code_compliance_check`

Analyzes banking code for policy violations using AST.

```bash
pytest tests/examples/test_riverbank_finance.py::TestCodeComplianceAST -v
```

**Example Test**:
```python
def test_interest_calculator_compound_bug():
    """Detects compound interest formula bug using AST analysis."""
    result = run_example_pipeline(
        workspace_path=WORKSPACE_PATH,
        pipeline_name="code_compliance_check",
        params={
            "file_path": "data/code/interest_calculator.py",
            "policy_reference": "INT-002"
        }
    )

    violations = result["outputs"]["compliance_report"]["violations"]
    assert len(violations) >= 2  # compound + day count bugs
```

**Artifacts Tested**:
- `ASTArtifact`: Python/JavaScript AST parsing
- Pattern matching for function definitions
- Policy violation detection

### 2. Risk Graph Analysis

**Pipeline**: `risk_graph_analysis`

Builds transaction graph and identifies high-risk customers using centrality metrics.

```bash
pytest tests/examples/test_riverbank_finance.py::TestTransactionGraphAnalysis -v
```

**Example Test**:
```python
def test_pagerank_centrality():
    """Calculates PageRank to identify influential nodes (potential money mules)."""
    result = run_example_pipeline(
        workspace_path=WORKSPACE_PATH,
        pipeline_name="risk_graph_analysis",
        params={
            "transaction_file": "data/transactions/transactions.json",
            "metric_type": "pagerank",
            "top_n": 10
        }
    )

    metrics = result["step_results"]["calculate_centrality"]["output"]
    assert metrics["algorithm"] == "pagerank"
    assert len(metrics["scores"]) >= 10
```

**Artifacts Tested**:
- `GraphArtifact`: Transaction graph construction
- `GraphMetricsArtifact`: Centrality calculations (PageRank, betweenness, degree)
- Risk ranking and pattern detection

### 3. Policy Explainer

**Pipeline**: `policy_explainer`

RAG-based Q&A over compliance policy documents.

```bash
pytest tests/examples/test_riverbank_finance.py::TestPolicyExplanation -v
```

**Example Test**:
```python
def test_policy_explainer_aml_structuring():
    """Explains structuring detection using RAG over AML policies."""
    result = run_example_pipeline(
        workspace_path=WORKSPACE_PATH,
        pipeline_name="policy_explainer",
        params={
            "question": "What is structuring and how do we detect it?",
            "policy_area": "AML"
        }
    )

    explanation = result["outputs"]["explanation"]
    assert "structuring" in explanation.lower()
    assert "10,000" in explanation  # CTR threshold
```

## Test Data

### Intentional Bugs (Code Files)

| File | Line | Bug | Policy |
|------|------|-----|--------|
| `interest_calculator.py` | 61-69 | Linear formula instead of exponential compound | INT-002 |
| `interest_calculator.py` | 97 | 365-day year instead of 360 | INT-003 |
| `transaction_processor.js` | - | Velocity threshold check | TXN-001 |
| `risk_scorer.py` | - | 0.30 threshold instead of 0.50 | AML-002 |

### Suspicious Patterns (Transaction Data)

| Customer | Pattern | Description |
|----------|---------|-------------|
| CUST-1004 | Structuring | Multiple ~$9,500 transactions to avoid $10k CTR |
| CUST-1006 ↔ CUST-1007 | Circular | Bidirectional transaction flows |
| CUST-1010 | Velocity + Structuring | 6+ txns in 60 min + structuring (CRITICAL) |
| CUST-1002 | Velocity | New account with high transaction frequency |

## Test Statistics

- **Total Tests**: 23
- **AST Tests**: 6 (code analysis)
- **Graph Tests**: 7 (transaction risk)
- **RAG Tests**: 4 (policy explanation)
- **Integration Tests**: 2 (cross-pipeline)
- **Config Tests**: 4 (workspace validation)

### Markers

```python
@pytest.mark.riverbank        # All RiverBank tests
@pytest.mark.examples_e2e     # E2E runtime tests
@pytest.mark.requires_mcp     # Needs MCP servers
@pytest.mark.mcp_ast_server   # Needs AST Server specifically
@pytest.mark.mcp_graphiti     # Needs Graphiti specifically
```

## Golden Snapshots

Deterministic test results stored in `expected/`:

- `code_policy_check.json` - Expected compliance report structure

### Regenerate Snapshots

```bash
pytest tests/examples/test_riverbank_finance.py::TestCodeComplianceAST::test_code_compliance_golden_snapshot \
  -v --regen-golden
```

## Documentation

Full documentation: [`docs/examples/riverbank_finance.md`](../../../docs/examples/riverbank_finance.md)

Topics covered:
- Architecture and artifact flow
- Pipeline step-by-step breakdowns
- Graph algorithm explanations
- Compliance policy references
- Integration with other examples

## Troubleshooting

### MCP Servers Not Running

Most tests require live MCP servers. To skip these:

```bash
pytest tests/examples/test_riverbank_finance.py -v -m "riverbank and not requires_mcp"
```

### Missing API Keys

Set required environment variables:

```bash
export OPENAI_API_KEY="sk-..."
```

### Vector Store Not Initialized

First run only:

```bash
python -m sibyl.tools.rag_indexer \
  --workspace examples/companies/riverbank_finance/config/workspace.yaml \
  --source policy_documents
```

## Related Examples

- **Northwind Analytics**: SQL analysis + RAG patterns
- **Vertex Foundry**: Agent orchestration
- **RetailFlow**: Optimization pipelines

## Support

Questions? Check:
1. [Full Documentation](../../../docs/examples/riverbank_finance.md)
2. [GitHub Issues](https://github.com/your-org/sibyl/labels/examples)
3. [Testing Guide](../../../docs/testing/examples.md)

---

**Status**: Complete ✓
**Last Updated**: 2024-11-22
