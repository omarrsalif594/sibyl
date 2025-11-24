# CI Integration for Example Benchmarks

This document provides recommendations for integrating example benchmarks into CI/CD pipelines.

## Overview

The benchmark system supports two execution modes optimized for different CI scenarios:

- **CI Mode** (`--mode=ci`): Fast, essential tests without MCP dependencies
- **Full Mode** (`--mode=full`): Comprehensive benchmarks including MCP integrations

## Recommended CI Strategy

### 1. Fast Checks (Every PR)

Run CI mode benchmarks on every pull request to catch major regressions quickly.

**Characteristics**:
- Runtime: <5 minutes
- No external dependencies
- Suitable for branch protection rules

### 2. Nightly Full Benchmarks

Run comprehensive benchmarks daily to track MCP-dependent pipelines.

**Characteristics**:
- Runtime: ~15-30 minutes
- Requires MCP servers
- Generates performance trends

### 3. Release Validation

Generate fresh baselines before releases to establish new performance standards.

## GitHub Actions Example

### File: `.github/workflows/examples_benchmarks.yml`

```yaml
name: Example Benchmarks

on:
  # Run CI benchmarks on every PR
  pull_request:
    branches: [main]
    paths:
      - 'examples/**'
      - 'tests/examples/**'
      - 'sibyl/**'

  # Run full benchmarks nightly
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

  # Manual trigger
  workflow_dispatch:
    inputs:
      mode:
        description: 'Benchmark mode'
        required: true
        default: 'ci'
        type: choice
        options:
          - ci
          - full

jobs:
  # Fast CI benchmarks (runs on every PR)
  benchmark-ci:
    name: Benchmarks - CI Mode
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request' || github.event.inputs.mode == 'ci'

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run CI benchmarks
        run: |
          python examples/shared/bench_examples.py \
            --mode=ci \
            --output=ci_results.json

      - name: Compare with baseline
        run: |
          python examples/shared/bench_examples.py \
            --mode=ci \
            --compare=examples/shared/benchmarks/ci_baseline.json

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: ci-benchmark-results
          path: ci_results.json

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('ci_results.json', 'utf8'));

            const completed = results.pipelines.filter(p => p.status === 'completed').length;
            const total = results.pipelines.length;

            const body = \`### Benchmark Results (CI Mode)

            - **Completed**: \${completed}/\${total}
            - **Total Runtime**: \${(results.total_runtime_ms / 1000).toFixed(2)}s

            See artifacts for full details.
            \`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

  # Full benchmarks with MCP (nightly)
  benchmark-full:
    name: Benchmarks - Full Mode
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event.inputs.mode == 'full'

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Setup MCP servers
        run: |
          # Install Node.js MCPs
          npm install -g @executeautomation/serena-mcp

          # Install Python MCPs
          pip install chronulus-mcp graphiti-mcp

          # Start containerized MCPs (Qdrant, Neo4j)
          cd examples/shared/mcp
          docker-compose up -d

          # Wait for services to be ready
          sleep 10

      - name: Verify MCP infrastructure
        run: |
          pytest tests/examples/test_mcp_integration.py::test_mcp_infrastructure_status -v

      - name: Run full benchmarks
        run: |
          python examples/shared/bench_examples.py \
            --mode=full \
            --output=full_results.json

      - name: Compare with baseline
        continue-on-error: true
        run: |
          python examples/shared/bench_examples.py \
            --mode=full \
            --compare=examples/shared/benchmarks/baseline.json

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: full-benchmark-results
          path: |
            full_results.json
            examples/shared/benchmarks/

      - name: Generate performance report
        run: |
          python devops/scripts/generate_benchmark_report.py \
            --input=full_results.json \
            --baseline=examples/shared/benchmarks/baseline.json \
            --output=performance_report.md

      - name: Upload performance report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: performance_report.md

      - name: Cleanup MCP servers
        if: always()
        run: |
          cd examples/shared/mcp
          docker-compose down
```

## GitLab CI Example

### File: `.gitlab-ci.yml`

```yaml
# Example Benchmarks CI

stages:
  - benchmark-ci
  - benchmark-full

variables:
  PYTHONPATH: "$CI_PROJECT_DIR"

# CI mode benchmarks (fast, every merge request)
benchmark:ci:
  stage: benchmark-ci
  image: python:3.11
  only:
    - merge_requests
    - main
  script:
    - pip install -e ".[test]"
    - python examples/shared/bench_examples.py --mode=ci --output=ci_results.json
    - python examples/shared/bench_examples.py --mode=ci --compare=examples/shared/benchmarks/ci_baseline.json
  artifacts:
    paths:
      - ci_results.json
    reports:
      junit: ci_results.json
    expire_in: 1 week

# Full benchmarks (nightly)
benchmark:full:
  stage: benchmark-full
  image: python:3.11
  services:
    - name: qdrant/qdrant:latest
      alias: qdrant
    - name: neo4j:latest
      alias: neo4j
  only:
    - schedules
  script:
    - pip install -e ".[test]"
    - npm install -g @executeautomation/serena-mcp
    - pip install chronulus-mcp graphiti-mcp
    - python examples/shared/bench_examples.py --mode=full --output=full_results.json
    - python examples/shared/bench_examples.py --mode=full --compare=examples/shared/benchmarks/baseline.json
  artifacts:
    paths:
      - full_results.json
      - examples/shared/benchmarks/
    expire_in: 30 days
```

## CircleCI Example

### File: `.circleci/config.yml`

```yaml
version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  benchmark-ci:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - python/install-packages:
          pkg-manager: pip
          pip-dependency-file: setup.py
      - run:
          name: Run CI Benchmarks
          command: |
            python examples/shared/bench_examples.py --mode=ci --output=ci_results.json
      - run:
          name: Compare with Baseline
          command: |
            python examples/shared/bench_examples.py --mode=ci --compare=examples/shared/benchmarks/ci_baseline.json
      - store_artifacts:
          path: ci_results.json

  benchmark-full:
    docker:
      - image: cimg/python:3.11
      - image: qdrant/qdrant:latest
      - image: neo4j:latest
    steps:
      - checkout
      - python/install-packages:
          pkg-manager: pip
          pip-dependency-file: setup.py
      - run:
          name: Setup MCP Dependencies
          command: |
            npm install -g @executeautomation/serena-mcp
            pip install chronulus-mcp graphiti-mcp
      - run:
          name: Run Full Benchmarks
          command: |
            python examples/shared/bench_examples.py --mode=full --output=full_results.json
      - run:
          name: Compare with Baseline
          command: |
            python examples/shared/bench_examples.py --mode=full --compare=examples/shared/benchmarks/baseline.json
      - store_artifacts:
          path: full_results.json

workflows:
  version: 2
  benchmark-ci:
    jobs:
      - benchmark-ci:
          filters:
            branches:
              only:
                - main
                - develop

  nightly-full:
    triggers:
      - schedule:
          cron: "0 2 * * *"
          filters:
            branches:
              only:
                - main
    jobs:
      - benchmark-full
```

## Integration Best Practices

### 1. Baseline Management

- **Version Control**: Commit baselines to git
- **Update Policy**: Update baseline after intentional performance work
- **Review Process**: Require review for baseline changes

```bash
# Update baseline after optimization
git add examples/shared/benchmarks/baseline.json
git commit -m "Update benchmark baseline: optimize revenue_analysis (-15%)"
```

### 2. Regression Handling

Set up clear policies for handling regressions:

**Automatic Block** (>50% slower):
- Block merge automatically
- Require investigation before merge

**Warning** (20-50% slower):
- Allow merge with approval
- Create tracking issue

**Minor** (<20% slower):
- Log for tracking
- No blocking

### 3. Performance Trending

Store benchmark results over time to identify trends:

```bash
# Save timestamped results
timestamp=$(date +%Y%m%d-%H%M%S)
python examples/shared/bench_examples.py --output=benchmarks/history/$timestamp.json
```

### 4. Notifications

Configure alerts for significant changes:

- Slack/Discord notifications for regressions
- Email summaries of nightly runs
- GitHub issue creation for persistent regressions

## Environment Variables

Recommended CI environment variables:

```bash
# Disable interactive prompts
export CI=true

# Configure timeouts
export SIBYL_TIMEOUT=300

# Logging
export LOG_LEVEL=INFO

# MCP configuration
export QDRANT_URL=http://localhost:6333
export NEO4J_URI=bolt://localhost:7687
```

## Troubleshooting

### Common CI Issues

1. **Timeouts in CI Mode**
   - Verify no MCP-dependent tests are running
   - Check `skip_ci=True` flag in benchmark config

2. **MCP Connection Failures**
   - Ensure services are started and healthy
   - Add health checks before running benchmarks

3. **Flaky Benchmarks**
   - Increase timeout values
   - Add retry logic for transient failures

4. **Resource Constraints**
   - Use larger CI runners for full mode
   - Consider running full benchmarks less frequently

## Monitoring and Alerting

Example Prometheus metrics:

```python
# Export benchmark metrics
benchmark_runtime_ms{company="northwind_analytics",pipeline="revenue_analysis"} 2345
benchmark_status{company="northwind_analytics",pipeline="revenue_analysis",status="completed"} 1
```

Example alert rule:

```yaml
- alert: BenchmarkRegression
  expr: benchmark_runtime_ms > benchmark_baseline_ms * 1.2
  for: 10m
  annotations:
    summary: "Performance regression detected"
    description: "{{ $labels.pipeline }} is >20% slower than baseline"
```

## Further Resources

- [BENCHMARKING.md](../../docs/examples/BENCHMARKING.md) - Full benchmarking guide
- [TESTING_CONVENTIONS.md](../../docs/examples/TESTING_CONVENTIONS.md) - Test organization
- [MCP_GUIDE.md](../../docs/examples/MCP_GUIDE.md) - MCP setup and configuration
