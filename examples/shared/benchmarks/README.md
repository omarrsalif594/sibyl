# Example Benchmarks

This directory contains benchmark baselines and results for Sibyl example pipelines.

## Files

- `baseline.json` - Reference baseline for performance comparison
- `ci_baseline.json` - CI-specific baseline (fast tests only)

## Usage

Generate a new baseline:
```bash
python examples/shared/bench_examples.py --output=examples/shared/benchmarks/baseline.json
```

Compare against baseline:
```bash
python examples/shared/bench_examples.py --compare=examples/shared/benchmarks/baseline.json
```

## Baseline Format

```json
{
  "timestamp": "2025-01-22T10:30:00Z",
  "mode": "full",
  "pipelines": [
    {
      "company": "northwind_analytics",
      "pipeline": "revenue_analysis",
      "status": "completed",
      "runtime_ms": 2345,
      "steps_executed": 6,
      "mcp_calls": 0,
      "error_message": null,
      "metadata": {}
    }
  ]
}
```

## Status Values

- `completed` - Pipeline ran successfully
- `failed` - Pipeline encountered an error
- `skipped` - Pipeline was skipped (e.g., requires MCP in CI mode)
- `timeout` - Pipeline exceeded timeout limit

## Regression Detection

The benchmark tool flags:
- **Performance Regressions**: >20% slower than baseline
- **Performance Improvements**: >20% faster than baseline
- **New Failures**: Previously passing tests that now fail
- **New Successes**: Previously failing tests that now pass
