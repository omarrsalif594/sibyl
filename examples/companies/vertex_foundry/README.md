# Vertex Foundry - ML Platform Engineering Example

Demonstrates: Job Polling, Streaming, SessionHandle, Control Flow

## Company Story

**Vertex Foundry** is the ML platform engineering team at a fast-growing AI company. They provide infrastructure for:
- Experiment tracking and management
- Hyperparameter tuning and optimization
- Distributed training job orchestration
- Model deployment and monitoring
- Resource allocation and cost optimization

The team uses **Sibyl** to build intelligent workflows that combine:
- **Conductor MCP**: For orchestrating distributed training jobs
- **Solver MCP**: For hyperparameter optimization and resource allocation
- **Deep Code Reasoning MCP**: For debugging failed training runs

This example showcases:
- **PollableJobHandle**: For long-running distributed training jobs
- **SessionHandle**: For multi-turn code analysis conversations
- **Automatic Job Polling**: With exponential backoff and retry logic
- **Streaming Outputs**: Real-time progress updates as jobs complete
- **Control Flow**: `when` conditions and `retry` logic in pipelines

## Scenarios

### 1. Hyperparameter Sweep with Job Polling ([details](scenarios/01_hyperparameter_sweep.md))
**Problem**: "I have a $500 budget to find the best hyperparameters for my model"

**Pipeline Flow**:
1. Solver MCP plans optimal search grid within budget
2. Conductor MCP launches 18 parallel training jobs → Returns **PollableJobHandle**
3. Framework automatically polls job status with exponential backoff
4. Streams progress chunks as jobs complete (real-time updates)
5. Detects failed job with transient error → Automatic retry with modified config
6. Aggregates results and selects best hyperparameters
7. Reports total cost and resource utilization

**Demonstrates**:
- PollableJobHandle for distributed jobs
- Automatic job polling (no manual loop required)
- Streaming outputs (progress chunks)
- Control flow: automatic retry on transient failures
- Budget-constrained optimization

**Expected Runtime**: ~30 minutes (simulated), ~5 minutes (mocked tests)

---

### 2. Diagnose Failing Training Job ([details](scenarios/02_diagnose_failing_job.md))
**Problem**: "My training job crashed at step 1523 with NaN loss - figure out why"

**Pipeline Flow**:
1. Load failed run metadata and error logs
2. Extract error patterns (gradient explosion, NaN progression)
3. Create **SessionHandle** for persistent code analysis conversation
4. **Turn 1**: Analyze training code for bugs → Finds `reduction='sum'` bug
5. **Turn 2**: Correlate error patterns with code issues (uses context from Turn 1)
6. **Turn 3**: Identify root cause through reasoning chain (uses context from Turns 1-2)
7. **Turn 4**: Generate fix recommendations (uses full context)
8. Create comprehensive diagnostic report
9. Close session

**Demonstrates**:
- SessionHandle for multi-turn conversations
- Context retention across analysis steps
- Chain-of-thought reasoning building on previous turns
- Deep code analysis with MCP integration
- Practical bug diagnosis with actionable fixes

**Expected Runtime**: ~2 minutes

---

### 3. GPU Resource Optimization ([details](scenarios/03_resource_optimization.md))
**Problem**: "10 experiments waiting, only 8 GPUs available - optimize allocation"

**Pipeline Flow**:
1. Load experiment requirements and GPU availability
2. Formulate mixed-integer programming problem
3. Solver MCP finds optimal allocation schedule
4. Generate execution plan with job waves
5. Estimate completion time and total cost

**Demonstrates**:
- Solver MCP for constraint satisfaction
- Resource optimization with multiple objectives
- Practical ML infrastructure problem

**Expected Runtime**: ~1 minute

## Project Structure

```
vertex_foundry/
├── README.md                          # This file
├── config/
│   ├── workspace.yaml                 # MCP connections, data sources
│   └── pipelines.yaml                 # Pipeline definitions
├── data/
│   ├── experiments/
│   │   ├── experiment_configs/        # 5 experiment YAML configs
│   │   └── logs/                      # Error log from failed run
│   ├── code/
│   │   ├── train_model.py            # Training script (contains bug)
│   │   ├── model.py                   # Model definition
│   │   └── data_loader.py             # Data loading utilities
│   └── runs/                          # 5 historical run metadata JSONs
├── scenarios/
│   ├── 01_hyperparameter_sweep.md     # Detailed scenario 1 walkthrough
│   ├── 02_diagnose_failing_job.md     # Detailed scenario 2 walkthrough
│   └── 03_resource_optimization.md    # Detailed scenario 3 walkthrough
└── tests/
    └── test_smoke.py                  # Comprehensive smoke tests
```

## Prerequisites

### 1. Required MCPs
This example requires the following MCP servers to be running:

```bash
# Conductor MCP (workflow orchestration)
mcp-conductor start --port 8080

# Solver MCP (optimization)
mcp-solver start --port 8081

# Deep Code Reasoning MCP (code analysis)
mcp-deep-code-reasoning start --port 8082 --model claude-sonnet-4-5
```

### 2. Sibyl Installation
```bash
pip install sibyl-framework
```

### 3. Verify Setup
```bash
# Check MCPs are running
curl http://localhost:8080/health  # Conductor
curl http://localhost:8081/health  # Solver
curl http://localhost:8082/health  # Deep Code Reasoning

# Validate workspace
sibyl workspace validate examples/companies/vertex_foundry/config/workspace.yaml
```

## Quick Start

### Run Scenario 1: Hyperparameter Sweep
```bash
cd examples/companies/vertex_foundry

# Run with streaming output
sibyl pipeline run hyperparameter_sweep \
  --workspace config/workspace.yaml \
  --config config/pipelines.yaml \
  --input budget_usd=500 \
  --input param_space='{"learning_rate": [0.0001, 0.001, 0.01], "batch_size": [32, 64, 128], "dropout": [0.3, 0.5, 0.7]}' \
  --input target_metric="val_acc" \
  --stream \
  --output sweep_results.json

# View best hyperparameters
jq '.best_hyperparameters' sweep_results.json
```

**Expected output**:
```json
{
  "learning_rate": 0.001,
  "batch_size": 64,
  "dropout": 0.3,
  "val_acc": 85.9
}
```

### Run Scenario 2: Diagnose Failure
```bash
# Diagnose the failed run
sibyl pipeline run diagnose_failure \
  --workspace config/workspace.yaml \
  --config config/pipelines.yaml \
  --input run_id="run_20250116_091523" \
  --input include_code_analysis=true \
  --verbose \
  --output diagnosis.json

# View root cause
jq '.diagnosis.root_cause' diagnosis.json

# View recommendations
jq '.recommendations' diagnosis.json
```

**Expected output**:
```
Root Cause: Loss function misconfiguration: CrossEntropyLoss(reduction='sum') should be reduction='mean'

Recommendations:
1. [CRITICAL] Fix loss function reduction in train_model.py line 85
2. [HIGH] Reduce learning rate to 0.001 or lower
3. [MEDIUM] Add gradient clipping (max_norm=1.0)
```

### Run Scenario 3: Resource Optimization
```bash
# Optimize GPU allocation
sibyl pipeline run optimize_resources \
  --workspace config/workspace.yaml \
  --config config/pipelines.yaml \
  --input-file data/experiments/pending_queue.json \
  --input optimization_objective="maximize_throughput" \
  --output allocation_plan.json

# View allocation plan
jq '.allocation_plan' allocation_plan.json
```

## Running Tests

### Smoke Tests
```bash
# Run all smoke tests
pytest examples/companies/vertex_foundry/tests/test_smoke.py -v

# Run specific test suite
pytest examples/companies/vertex_foundry/tests/test_smoke.py::TestHyperparameterSweep -v
pytest examples/companies/vertex_foundry/tests/test_smoke.py::TestDiagnoseFailure -v

# Run with coverage
pytest examples/companies/vertex_foundry/tests/test_smoke.py --cov=examples/companies/vertex_foundry
```

**Expected**: All tests pass (16 tests total)

### Test Coverage
The smoke tests verify:
- ✓ Search grid planning with budget constraints
- ✓ PollableJobHandle creation and usage
- ✓ Automatic job polling with progression
- ✓ Streaming job results
- ✓ Retry logic for failed jobs
- ✓ Best hyperparameter selection
- ✓ Cost calculation
- ✓ Failed run data loading
- ✓ SessionHandle creation
- ✓ Multi-turn code analysis
- ✓ Context retention across turns
- ✓ Diagnostic report generation
- ✓ Configuration file validation
- ✓ Synthetic data existence
- ✓ Intentional bug presence

## Synthetic Data

All data in this example is synthetic and created for demonstration purposes:

### Training Code
- `train_model.py`: PyTorch training script with intentional bug
  - **Bug**: Line 85 - `CrossEntropyLoss(reduction='sum')` should be `reduction='mean'`
  - **Impact**: Causes gradient explosion when combined with high learning rate
- `model.py`: Simple ConvNet architecture
- `data_loader.py`: Mock CIFAR-10 data loader

### Experiment Configs
- 5 YAML configs with different hyperparameter settings
- Realistic GPU requirements and cost estimates

### Run Metadata
- 5 JSON files representing historical training runs
- 4 successful runs, 1 failed run
- Failed run: `run_20250116_091523` - Crashed at step 1523 with NaN loss

### Error Logs
- `run_20250116_091523_error.log`: Detailed error log showing:
  - Gradient explosion progression
  - NaN loss detection
  - Loss function configuration
  - Diagnostic information

## Key Implementation Details

### PollableJobHandle
```python
# Conceptual implementation (from pipelines.yaml)
launch_training_jobs:
  technique: conductor_orchestration
  mcp: conductor
  config:
    return_handle: true  # Returns PollableJobHandle
  outputs:
    job_handle: "training_jobs.handle"  # PollableJobHandle

monitor_training_progress:
  technique: job_polling
  config:
    polling:
      initial_delay_ms: 2000
      max_delay_ms: 10000
      backoff_multiplier: 1.5
      max_attempts: 50
  inputs:
    job_handle: "{{ training_jobs.handle }}"  # Framework polls automatically
```

### SessionHandle
```python
# Conceptual implementation (from pipelines.yaml)
initialize_analysis_session:
  technique: session_creation
  mcp: code_analyzer
  config:
    session_type: "persistent"
    context_retention: true
    max_turns: 10
  outputs:
    session_handle: "analysis.session"  # SessionHandle

analyze_training_code:
  technique: code_analysis
  mcp: code_analyzer
  inputs:
    session_handle: "{{ analysis.session }}"  # Reuses same session

correlate_errors_with_code:
  technique: pattern_matching
  mcp: code_analyzer
  inputs:
    session_handle: "{{ analysis.session }}"  # Context preserved from previous turn
```

### Control Flow
```yaml
# Automatic retry on failure
retry_failed_jobs:
  when: "{{ jobs.status.failed_count > 0 }}"  # Conditional execution
  retry:
    max_attempts: 2
    when: "{{ error.type == 'transient' }}"  # Only retry transient errors

# Budget validation
validate_budget:
  when: "{{ search_plan.cost > inputs.budget_usd }}"
  action:
    type: error
    message: "Estimated cost exceeds budget"
```

## Features Showcase

### 1. PollableJobHandle
- **What**: Handle for long-running jobs that can be polled for status
- **Where**: Scenario 1 - Hyperparameter sweep
- **How**: Conductor MCP returns handle, framework polls automatically
- **Why**: No manual polling loop, automatic backoff, cleaner code

### 2. SessionHandle
- **What**: Persistent conversation context across multiple MCP calls
- **Where**: Scenario 2 - Failure diagnosis
- **How**: Code analyzer MCP maintains context across 4 turns
- **Why**: Multi-turn reasoning, context retention, sophisticated analysis

### 3. Automatic Job Polling
- **What**: Framework polls jobs without manual intervention
- **Where**: Scenario 1 - Job monitoring step
- **How**: Configured with backoff parameters, runs automatically
- **Why**: Simpler code, efficient polling, no busy-waiting

### 4. Streaming Outputs
- **What**: Real-time progress chunks as jobs complete
- **Where**: Scenario 1 - Result streaming
- **How**: Job handle yields results as async iterator
- **Why**: Live updates, better UX, early visibility

### 5. Control Flow
- **What**: Conditional execution and retry logic in pipelines
- **Where**: Both scenarios - retry, validation, conditional steps
- **How**: `when` conditions and `retry` configurations
- **Why**: Robust pipelines, automatic error handling, flexibility

## Troubleshooting

### MCPs not responding
```bash
# Check MCP status
ps aux | grep mcp

# Restart MCPs
mcp-conductor restart
mcp-solver restart
mcp-deep-code-reasoning restart
```

### Pipeline execution fails
```bash
# Enable debug logging
export SIBYL_LOG_LEVEL=DEBUG

# Run with verbose output
sibyl pipeline run <name> --verbose --debug
```

### Tests fail
```bash
# Check data files exist
ls -R examples/companies/vertex_foundry/data/

# Verify configurations are valid
yamllint config/workspace.yaml
yamllint config/pipelines.yaml
```

## Learning Resources

- **MCP Integration Guide**: Working with external MCPs
- **Pipeline Configuration**: YAML syntax and best practices

## Contributing

This example demonstrates Sibyl's capabilities. To extend:
1. Add new scenarios to `scenarios/`
2. Create corresponding pipeline definitions in `config/pipelines.yaml`
3. Add smoke tests to `tests/test_smoke.py`
4. Update this README with usage instructions

## License

This example is part of the Sibyl framework and follows the same license.

---

**Questions?** See detailed scenario walkthroughs in `scenarios/` directory or run smoke tests for implementation examples.
