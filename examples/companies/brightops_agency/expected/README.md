# Golden Snapshots - BrightOps Agency

This directory contains golden snapshot files for regression testing of BrightOps Agency pipelines.

## What are Golden Snapshots?

Golden snapshots are saved, normalized outputs from pipeline executions that serve as the "expected" baseline for regression testing. When tests run, they compare current pipeline outputs against these golden snapshots to detect unintended changes.

## Files in This Directory

### meeting_to_plan_acme.json
Golden snapshot for the `meeting_to_plan` pipeline using the Acme kickoff meeting.

**Pipeline:** `meeting_to_plan`
**Input:** `{"meeting_file": "kickoff_acme_mobile_2024_03.md"}`
**Key Outputs:**
- Categories (5 work streams)
- Checkpoints (4 milestones)
- Quality score (8.5/10)
- Validation notes

**Techniques Demonstrated:**
- category_naming
- checkpoint_naming
- quality_scoring
- Sequential Thinking MCP

---

### learn_preferences_sarah.json
Golden snapshot for the `learn_preferences` pipeline learning Sarah's communication patterns.

**Pipeline:** `learn_preferences`
**Input:** `{"client_name": "Acme CEO Sarah"}`
**Key Outputs:**
- PatternArtifact with communication preferences
- Confidence score (0.85)
- Pattern details (communication style, decision-making, expectations)
- Human-readable summary

**Techniques Demonstrated:**
- RAG pipeline
- Sequential Thinking MCP
- In-Memoria MCP
- PatternArtifact creation

---

### project_breakdown_restaurant_app.json
Golden snapshot for the `project_breakdown` pipeline expanding a restaurant app brief.

**Pipeline:** `project_breakdown`
**Input:** `{"project_brief": "Build a mobile app for restaurant reservations", "timeline_weeks": 16}`
**Key Outputs:**
- Work categories (5 streams with 30+ items)
- Milestones (4 phases)
- Estimates (80 person-weeks, $725K budget, 6 person team)
- Quality score (8.7/10)
- Expanded scope with architecture

**Techniques Demonstrated:**
- Sequential Thinking MCP (scope expansion, architecture exploration, estimation)
- category_naming
- checkpoint_naming
- quality_scoring

---

## How to Use

### Running Tests Against Golden Snapshots

```bash
# Run all BrightOps tests including golden snapshot comparisons
pytest tests/examples/test_brightops_agency.py -m golden -v

# Run specific golden snapshot test
pytest tests/examples/test_brightops_agency.py::test_meeting_to_plan_golden_snapshot -v
```

### Regenerating Golden Snapshots

If pipeline behavior intentionally changes and you need to update the golden snapshots:

```bash
# Regenerate all golden snapshots
pytest tests/examples/test_brightops_agency.py -m golden --regen-golden -v

# This will:
# 1. Run the pipelines
# 2. Normalize the outputs
# 3. Save new golden snapshot files
# 4. Skip the comparison (since we're regenerating)
```

### When to Regenerate

Regenerate golden snapshots when:
- Pipeline implementation changes intentionally
- AI generation techniques are updated
- Output format is improved
- New fields are added to outputs

**Important:** Review changes carefully before regenerating! Golden snapshots protect against unintended regressions.

## Normalization

Golden snapshots are **normalized** before saving, which means:
- Timestamp fields removed
- Run IDs removed
- Duration/execution time removed
- Request/trace IDs removed

This allows us to compare functional output without being affected by non-deterministic metadata.

See `tests/examples/conftest.py::normalize_result()` for the normalization logic.

## File Format

All golden snapshots are JSON files with the following structure:

```json
{
  "status": "completed",
  "outputs": {
    // Pipeline-specific outputs
  },
  "metadata": {
    "techniques_used": [...],
    "mcp_providers": [...]
  }
}
```

## Best Practices

1. **Review changes:** Always `git diff` golden snapshots before committing
2. **Document changes:** Explain why snapshots were regenerated in commit messages
3. **Keep snapshots small:** Use minimal but representative test cases
4. **Version control:** Golden snapshots should be committed to git
5. **CI/CD:** Run golden snapshot tests in CI to catch regressions early

## Troubleshooting

### Test fails with "differs from golden snapshot"

This means the pipeline output changed. Either:
1. **Intended change:** Regenerate with `--regen-golden` and review the diff
2. **Unintended regression:** Fix the pipeline code to match expected output

### Golden snapshot file not found

First time running the test? The test will automatically create the golden snapshot.

### Non-deterministic outputs

If AI generation produces slightly different outputs each run:
- Use temperature=0 for deterministic generation
- Validate structure/invariants instead of exact content
- Use separate tests for invariants vs golden snapshots

## See Also

- `tests/examples/conftest.py` - Test harness and utilities
- `tests/examples/test_brightops_agency.py` - Full test suite
- `examples/companies/brightops_agency/README.md` - BrightOps overview
- `docs/examples/brightops_agency.md` - Detailed documentation
