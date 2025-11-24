# Shared Tooling for Sibyl Examples

This directory contains tools for benchmarking, testing, and managing Sibyl examples.

## Tools

### 1. bench.py - Benchmarking Tool

Runs performance benchmarks across example scenarios.

**Usage:**
```bash
# Benchmark all companies
python examples/shared/tooling/bench.py --company all

# Benchmark specific companies
python examples/shared/tooling/bench.py --company riverbank_finance vertex_foundry

# Save results to JSON
python examples/shared/tooling/bench.py --company all --output results.json

# Save results to CSV
python examples/shared/tooling/bench.py --company all --output results.csv --format csv

# Compare with baseline
python examples/shared/tooling/bench.py --company all --baseline baseline.json

# Dry run (discover scenarios only)
python examples/shared/tooling/bench.py --dry-run
```

**Features:**
- Discovers all example companies and scenarios automatically
- Records timing, success/failure, artifact counts
- Multiple output formats: JSON, CSV, text
- Baseline comparison for performance regression detection
- Dry-run mode for discovery without execution

**Output:**
- Console: Human-readable summary with timing and status
- JSON: Structured data for further processing
- CSV: Tabular data for spreadsheets and analysis

### 2. test_runner.py - Test Runner

Discovers and runs all smoke tests across examples.

**Usage:**
```bash
# Run all tests
python examples/shared/tooling/test_runner.py

# Run tests for specific company
python examples/shared/tooling/test_runner.py --company riverbank_finance

# Verbose output
python examples/shared/tooling/test_runner.py --verbose

# Run only tests with specific markers
python examples/shared/tooling/test_runner.py --markers smoke
```

**Features:**
- Auto-discovers test files in company directories
- Runs pytest on each test file
- Aggregates results across all companies
- Shows pass/fail summary by company
- Returns appropriate exit code for CI/CD integration

**Output:**
- Per-company test results
- Overall pass/fail summary
- Exit code 0 if all pass, 1 if any fail

## Integration with Pytest

These tools work alongside pytest. For direct pytest usage:

```bash
# Run tests with examples marker
pytest -m examples

# Run all tests in a specific company
pytest examples/companies/riverbank_finance/tests/

# Run specific test file
pytest examples/companies/riverbank_finance/tests/test_smoke.py
```

## CI/CD Integration

Use these tools in your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run example tests
  run: |
    python examples/shared/tooling/test_runner.py

- name: Run benchmarks
  run: |
    python examples/shared/tooling/bench.py --company all --output benchmarks.json

- name: Compare with baseline
  run: |
    python examples/shared/tooling/bench.py --company all --baseline main-baseline.json
```

## Benchmarking Best Practices

1. **Establish Baseline**: Run benchmarks on a stable commit and save results
   ```bash
   python examples/shared/tooling/bench.py --company all --output baseline.json
   ```

2. **Regular Comparison**: Compare new runs against baseline
   ```bash
   python examples/shared/tooling/bench.py --company all --baseline baseline.json
   ```

3. **Track Over Time**: Save timestamped results for trend analysis
   ```bash
   python examples/shared/tooling/bench.py --company all --output results-$(date +%Y%m%d).json
   ```

4. **Isolate Environment**: Run benchmarks on consistent hardware with minimal background processes

## Testing Best Practices

1. **Smoke Tests**: Fast tests that verify basic functionality
   - Place in `companies/<company>/tests/test_smoke.py`
   - Mark with `@pytest.mark.smoke`

2. **Integration Tests**: Full scenario execution tests
   - Place in `companies/<company>/tests/test_integration.py`
   - Mark with `@pytest.mark.integration`

3. **MCP Mocking**: For tests without MCP dependencies
   - Use mock mode in workspace configuration
   - Mark with `@pytest.mark.unit`

## Troubleshooting

### bench.py Issues

**Problem**: "No companies found"
- Ensure you're running from project root or use `--examples-root` flag
- Check that `examples/companies/` directory exists

**Problem**: Scenarios not discovered
- Verify scenarios exist in `companies/<company>/scenarios/`
- Check directory structure matches expected format

### test_runner.py Issues

**Problem**: "pytest not found"
- Install pytest: `pip install pytest`
- Ensure you're using the correct Python environment

**Problem**: Tests timeout
- Default timeout is 300 seconds (5 minutes)
- Consider splitting long-running tests
- Use pytest markers to separate quick and slow tests

**Problem**: Import errors in tests
- Ensure PYTHONPATH includes project root
- Run from project root directory
- Check that `sibyl` package is installed

## Adding New Tools

To add new tools to this directory:

1. Create Python script with clear CLI interface using `argparse`
2. Make it executable: `chmod +x tool.py`
3. Add shebang: `#!/usr/bin/env python3`
4. Document usage in this README
5. Add to CI/CD pipeline if appropriate

## Related Documentation

- [Examples Index](../../../docs/examples/INDEX.md)
- [MCP Setup Guide](../mcp/README.md)
- [pytest Documentation](https://docs.pytest.org/)
