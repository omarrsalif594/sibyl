# Scenario 1: Hyperparameter Sweep with Job Polling & Streaming

## Overview
This scenario demonstrates how to plan and execute a distributed hyperparameter optimization sweep with automatic job polling, streaming progress updates, and control flow features.

## ML Platform Problem
As an ML engineer at Vertex Foundry, you have a $500 budget to find the optimal hyperparameters for your ConvNet model. You need to:
1. Efficiently explore the hyperparameter space within budget
2. Monitor multiple parallel training jobs in real-time
3. Handle job failures with automatic retries
4. Stream progress updates as jobs complete
5. Identify the best configuration quickly

## Features Demonstrated
- **PollableJobHandle**: Distributed training jobs return pollable handles
- **Automatic Job Polling**: Framework polls job status with exponential backoff
- **Streaming Outputs**: Real-time progress chunks as jobs complete
- **Control Flow**: `when` conditions and `retry` logic for failed jobs
- **ExternalHandle**: Conductor MCP integration for job orchestration

## Prerequisites
1. Conductor MCP server running (workflow orchestration)
2. Solver MCP server running (hyperparameter optimization)
3. Vertex Foundry workspace configured
4. Training code and data available

## Setup

### 1. Verify MCPs are running
```bash
# Check Conductor MCP
curl http://localhost:8080/health

# Check Solver MCP
curl http://localhost:8081/health
```

### 2. Verify workspace configuration
```bash
sibyl workspace validate examples/companies/vertex_foundry/config/workspace.yaml
```

## Execution

### Command
```bash
sibyl pipeline run hyperparameter_sweep \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input budget_usd=500 \
  --input param_space='{"learning_rate": [0.0001, 0.001, 0.01], "batch_size": [32, 64, 128], "dropout": [0.3, 0.5, 0.7]}' \
  --input target_metric="val_acc" \
  --stream
```

### Alternative: Use JSON input file
```bash
# Create input file
cat > sweep_input.json <<EOF
{
  "budget_usd": 500,
  "param_space": {
    "learning_rate": [0.0001, 0.001, 0.01],
    "batch_size": [32, 64, 128],
    "dropout": [0.3, 0.5, 0.7]
  },
  "target_metric": "val_acc"
}
EOF

sibyl pipeline run hyperparameter_sweep \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input-file sweep_input.json \
  --stream
```

## Expected Behavior

### Phase 1: Search Grid Planning
```
[2025-01-22 10:15:23] INFO: Starting pipeline: hyperparameter_sweep
[2025-01-22 10:15:23] INFO: Step 1/9: plan_search_grid
[2025-01-22 10:15:23] INFO: Connecting to Solver MCP...
[2025-01-22 10:15:24] INFO: Optimizing search grid with budget constraint $500
[2025-01-22 10:15:26] INFO: Search grid planned:
  - Total trials: 18
  - Estimated cost: $478.50
  - Estimated duration: 36 hours (parallel execution)
  - Max concurrent jobs: 5
```

### Phase 2: Job Launch & PollableJobHandle
```
[2025-01-22 10:15:26] INFO: Step 3/9: launch_training_jobs
[2025-01-22 10:15:26] INFO: Connecting to Conductor MCP...
[2025-01-22 10:15:27] INFO: Submitting 18 training jobs...
[2025-01-22 10:15:30] INFO: Jobs submitted successfully
[2025-01-22 10:15:30] INFO: Created PollableJobHandle: job_handle_abc123def456
[2025-01-22 10:15:30] INFO: Job IDs: [
  "job_001", "job_002", "job_003", "job_004", "job_005",
  "job_006", "job_007", "job_008", "job_009", "job_010",
  "job_011", "job_012", "job_013", "job_014", "job_015",
  "job_016", "job_017", "job_018"
]
```

### Phase 3: Automatic Job Polling with Backoff
```
[2025-01-22 10:15:30] INFO: Step 4/9: monitor_training_progress
[2025-01-22 10:15:30] INFO: Starting automatic job polling...
[2025-01-22 10:15:30] INFO: Polling configuration:
  - Initial delay: 2000ms
  - Max delay: 10000ms
  - Backoff multiplier: 1.5x
  - Max attempts: 50

[2025-01-22 10:15:32] INFO: Poll #1 - Jobs status:
  - Running: 5
  - Queued: 13
  - Completed: 0
  - Failed: 0

[2025-01-22 10:15:35] INFO: Poll #2 - Jobs status (delay: 3000ms):
  - Running: 5
  - Queued: 13
  - Completed: 0
  - Failed: 0

[2025-01-22 10:15:39] INFO: Poll #3 - Jobs status (delay: 4500ms):
  - Running: 5
  - Queued: 11
  - Completed: 2
  - Failed: 0
```

### Phase 4: Streaming Progress Updates
```
[2025-01-22 10:15:39] STREAM: {
  "type": "job_completed",
  "job_id": "job_001",
  "hyperparameters": {"learning_rate": 0.001, "batch_size": 32, "dropout": 0.3},
  "metrics": {"val_acc": 84.2, "train_loss": 0.234},
  "duration_seconds": 7200,
  "cost_usd": 25.20
}

[2025-01-22 10:15:39] STREAM: {
  "type": "job_completed",
  "job_id": "job_002",
  "hyperparameters": {"learning_rate": 0.001, "batch_size": 32, "dropout": 0.5},
  "metrics": {"val_acc": 82.7, "train_loss": 0.245},
  "duration_seconds": 7150,
  "cost_usd": 25.00
}

[2025-01-22 10:15:45] INFO: Poll #4 - Jobs status (delay: 6750ms):
  - Running: 5
  - Queued: 9
  - Completed: 4
  - Failed: 0

[2025-01-22 10:15:45] STREAM: {
  "type": "job_completed",
  "job_id": "job_003",
  "hyperparameters": {"learning_rate": 0.001, "batch_size": 64, "dropout": 0.3},
  "metrics": {"val_acc": 85.9, "train_loss": 0.187},
  "duration_seconds": 7300,
  "cost_usd": 25.50
}
```

### Phase 5: Job Failure & Automatic Retry (Control Flow)
```
[2025-01-22 10:16:12] STREAM: {
  "type": "job_failed",
  "job_id": "job_008",
  "hyperparameters": {"learning_rate": 0.01, "batch_size": 128, "dropout": 0.5},
  "error": "RuntimeError: Loss became NaN at step 1523",
  "error_type": "transient",
  "duration_seconds": 1612,
  "cost_usd": 5.60
}

[2025-01-22 10:16:12] WARN: Job job_008 failed with transient error
[2025-01-22 10:16:12] INFO: Step 6/9: retry_failed_jobs (triggered by failure)
[2025-01-22 10:16:12] INFO: Retrying job_008 with modified configuration...
[2025-01-22 10:16:15] INFO: Retry job submitted: job_008_retry_1
[2025-01-22 10:16:15] INFO: Continuing to poll all jobs...

[2025-01-22 10:18:45] STREAM: {
  "type": "job_completed",
  "job_id": "job_008_retry_1",
  "hyperparameters": {"learning_rate": 0.005, "batch_size": 128, "dropout": 0.5},
  "metrics": {"val_acc": 83.1, "train_loss": 0.298},
  "duration_seconds": 7400,
  "cost_usd": 25.90,
  "note": "Retry succeeded with reduced learning rate"
}
```

### Phase 6: All Jobs Complete
```
[2025-01-22 10:45:30] INFO: Poll #28 - All jobs completed
[2025-01-22 10:45:30] INFO: Final status:
  - Completed: 18
  - Failed (permanent): 0
  - Total retries: 1
  - Total duration: 30 minutes (wall clock)
```

### Phase 7: Results Aggregation & Best Selection
```
[2025-01-22 10:45:30] INFO: Step 7/9: aggregate_results
[2025-01-22 10:45:31] INFO: Aggregated 18 completed jobs
[2025-01-22 10:45:31] INFO: Ranking by val_acc (descending)...

[2025-01-22 10:45:31] INFO: Step 8/9: select_best
[2025-01-22 10:45:31] INFO: Best hyperparameters found:
  - learning_rate: 0.001
  - batch_size: 64
  - dropout: 0.3
  - val_acc: 85.9%
  - train_loss: 0.187
  - run_id: job_003

[2025-01-22 10:45:31] INFO: Top 3 configurations:
  1. lr=0.001, bs=64, dropout=0.3 → val_acc=85.9%
  2. lr=0.001, bs=128, dropout=0.3 → val_acc=85.1%
  3. lr=0.001, bs=32, dropout=0.3 → val_acc=84.2%
```

### Phase 8: Cost Summary
```
[2025-01-22 10:45:31] INFO: Step 9/9: calculate_cost
[2025-01-22 10:45:31] INFO: Cost breakdown:
  - Successful jobs: $453.20
  - Failed job (partial): $5.60
  - Retry jobs: $25.90
  - Total: $484.70
  - Budget remaining: $15.30
  - Budget utilization: 96.9%

[2025-01-22 10:45:31] SUCCESS: Pipeline completed successfully
```

## Pipeline Outputs

The pipeline generates the following outputs:

```json
{
  "best_hyperparameters": {
    "learning_rate": 0.001,
    "batch_size": 64,
    "dropout": 0.3
  },
  "best_score": 85.9,
  "all_results": [
    {
      "job_id": "job_003",
      "hyperparameters": {"learning_rate": 0.001, "batch_size": 64, "dropout": 0.3},
      "metrics": {"val_acc": 85.9, "train_loss": 0.187},
      "cost_usd": 25.50
    },
    // ... 17 more results
  ],
  "total_cost": 484.70
}
```

## Key Technical Details

### PollableJobHandle Implementation
```python
# Internal representation (conceptual)
class PollableJobHandle:
    handle_id: str = "job_handle_abc123def456"
    job_ids: List[str] = ["job_001", "job_002", ...]
    status: JobStatus = JobStatus.RUNNING
    polling_config: PollingConfig

    async def poll(self) -> JobStatusUpdate:
        # Framework automatically polls with backoff
        pass

    async def stream_results(self) -> AsyncIterator[JobResult]:
        # Yields results as they become available
        pass
```

### Automatic Retry Logic
```yaml
# From pipelines.yaml
retry_failed_jobs:
  when: "{{ jobs.status.failed_count > 0 }}"
  retry:
    max_attempts: 2
    when: "{{ error.type == 'transient' }}"
```

The framework automatically:
1. Detects transient errors (NaN loss, OOM, connection issues)
2. Applies retry logic based on error type
3. Modifies hyperparameters if needed (e.g., reduce learning rate)
4. Re-submits failed jobs
5. Continues polling all jobs

## Verification

### Check streaming output was captured
```bash
ls -lh sweep_output_stream.jsonl
# Should contain ~18+ lines (one per completed job)
```

### Validate results
```bash
# Parse best hyperparameters
jq '.best_hyperparameters' sweep_output.json

# Check cost stayed within budget
jq '.total_cost' sweep_output.json
```

## Troubleshooting

### No streaming output
- Ensure `--stream` flag is used
- Check workspace.yaml has `streaming.enabled: true`

### Jobs not polling
- Verify Conductor MCP is running
- Check polling configuration in pipelines.yaml
- Look for timeout errors in logs

### Budget exceeded
- Solver MCP should prevent this by planning within budget
- Check cost estimation accuracy
- Review failed job costs (partial charges)

## What This Demonstrates

1. **PollableJobHandle**: Jobs return pollable handles that framework can monitor
2. **Automatic Polling**: Framework polls job status with exponential backoff (no manual polling loop)
3. **Streaming**: Real-time progress chunks delivered as jobs complete
4. **Control Flow**: `when` conditions trigger retry logic for failed jobs
5. **MCP Integration**: Conductor MCP for orchestration, Solver MCP for optimization
6. **Cost Management**: Budget-constrained optimization with accurate tracking
7. **Fault Tolerance**: Automatic retry of transient failures

This scenario showcases the complete job handling experience for ML workflows.
