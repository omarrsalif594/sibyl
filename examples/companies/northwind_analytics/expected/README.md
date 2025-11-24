# Golden Snapshots for Northwind Analytics

This directory contains "golden" snapshot files used for regression testing of Northwind Analytics pipelines.

## What are Golden Snapshots?

Golden snapshots are pre-recorded expected outputs from deterministic pipeline runs. Tests compare actual pipeline outputs against these golden files to detect regressions in:

- Output structure changes
- Data format modifications
- Unexpected content variations
- Quality degradation

## Files

- `explain_dashboard.json` - Expected output for dashboard explanation pipeline
- `generate_release_notes.json` - Expected output for release notes generation pipeline

## Regenerating Golden Files

When pipeline implementations change intentionally (e.g., improved prompts, enhanced formatting), you should regenerate the golden files:

```bash
# Regenerate all golden snapshots
pytest tests/examples/test_northwind_analytics.py::TestGoldenSnapshots --regen-golden

# Regenerate specific snapshot
pytest tests/examples/test_northwind_analytics.py::TestGoldenSnapshots::test_explain_dashboard_golden_snapshot --regen-golden
```

## Important Notes

1. **Normalization**: Golden snapshots have non-deterministic fields removed (timestamps, run_ids, etc.) via `normalize_result()`

2. **Deterministic Pipelines Only**: Only pipelines with fixed inputs and predictable outputs are suitable for golden snapshots

3. **Review Changes**: Always review git diffs when regenerating golden files to ensure changes are intentional

4. **Version Control**: Golden files are checked into git and should be updated through pull requests

## Adding New Golden Snapshots

To add a new golden snapshot:

1. Add a test method in `tests/examples/test_northwind_analytics.py::TestGoldenSnapshots`
2. Use `compare_with_golden()` helper
3. Run test with `--regen-golden` to create the initial golden file
4. Verify the golden file looks correct
5. Commit the golden file with your test

Example:

```python
def test_new_pipeline_golden_snapshot(self, request):
    result = run_example_pipeline(
        workspace_path=str(WORKSPACE_PATH),
        pipeline_name="new_pipeline",
        params={"fixed_param": "value"}
    )
    assert_pipeline_ok(result)

    golden_path = EXPECTED_DIR / "new_pipeline.json"
    compare_with_golden(
        result,
        str(golden_path),
        regen=request.config.getoption("--regen-golden", default=False),
        normalize=True
    )
```

## See Also

- `/tests/examples/conftest.py` - Test harness utilities
- `/tests/examples/test_northwind_analytics.py` - Test implementations
- `/docs/examples/TESTING_CONVENTIONS.md` - Testing conventions and guidelines
