# Scenario 3: GPU Resource Optimization (Optional)

## Overview
This optional scenario demonstrates using the Solver MCP to optimally allocate limited GPU resources across multiple team experiments, balancing throughput, cost, and priorities.

## ML Platform Problem
Your team has 10 experiments waiting to run, but only 8 GPUs available (4x T4, 3x V100, 1x A100). You need to:
1. Understand each experiment's resource requirements
2. Formulate an optimization problem with constraints
3. Solve for optimal GPU allocation
4. Generate an execution schedule
5. Estimate completion time and total cost

## Features Demonstrated
- **Solver MCP Integration**: Complex constraint solving
- **ExternalHandle**: Solver MCP connection
- **Control Flow**: Conditional logic based on resource availability
- **Data Integration**: Loading experiment requirements from files

## Prerequisites
1. Solver MCP server running (optimization)
2. Vertex Foundry workspace configured
3. Experiment queue data available

## Setup

### 1. Verify Solver MCP is running
```bash
curl http://localhost:8081/health
```

### 2. Create experiment queue data
```bash
cat > examples/companies/vertex_foundry/data/experiments/pending_queue.json <<EOF
{
  "experiments": [
    {
      "exp_id": "exp_101",
      "name": "Large ResNet Training",
      "gpu_requirement": {"type": "A100", "count": 1},
      "estimated_hours": 8,
      "priority": "high"
    },
    {
      "exp_id": "exp_102",
      "name": "Hyperparameter Sweep - Part 1",
      "gpu_requirement": {"type": "T4", "count": 4},
      "estimated_hours": 12,
      "priority": "medium"
    },
    {
      "exp_id": "exp_103",
      "name": "Model Ensembling",
      "gpu_requirement": {"type": "V100", "count": 2},
      "estimated_hours": 6,
      "priority": "high"
    },
    {
      "exp_id": "exp_104",
      "name": "Data Augmentation Test",
      "gpu_requirement": {"type": "T4", "count": 1},
      "estimated_hours": 3,
      "priority": "low"
    },
    {
      "exp_id": "exp_105",
      "name": "Architecture Search",
      "gpu_requirement": {"type": "V100", "count": 3},
      "estimated_hours": 24,
      "priority": "medium"
    },
    {
      "exp_id": "exp_106",
      "name": "Fine-tuning BERT",
      "gpu_requirement": {"type": "V100", "count": 1},
      "estimated_hours": 4,
      "priority": "high"
    },
    {
      "exp_id": "exp_107",
      "name": "Lightweight CNN Test",
      "gpu_requirement": {"type": "T4", "count": 1},
      "estimated_hours": 2,
      "priority": "low"
    },
    {
      "exp_id": "exp_108",
      "name": "Transfer Learning Baseline",
      "gpu_requirement": {"type": "T4", "count": 2},
      "estimated_hours": 5,
      "priority": "medium"
    },
    {
      "exp_id": "exp_109",
      "name": "Distillation Pipeline",
      "gpu_requirement": {"type": "V100", "count": 2},
      "estimated_hours": 10,
      "priority": "high"
    },
    {
      "exp_id": "exp_110",
      "name": "Ablation Study",
      "gpu_requirement": {"type": "T4", "count": 1},
      "estimated_hours": 4,
      "priority": "medium"
    }
  ],
  "available_gpus": {
    "T4": {"count": 4, "cost_per_hour": 0.35},
    "V100": {"count": 3, "cost_per_hour": 1.00},
    "A100": {"count": 1, "cost_per_hour": 2.50}
  }
}
EOF
```

## Execution

### Command - Maximize Throughput
```bash
sibyl pipeline run optimize_resources \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input-file examples/companies/vertex_foundry/data/experiments/pending_queue.json \
  --input optimization_objective="maximize_throughput"
```

### Command - Minimize Cost
```bash
sibyl pipeline run optimize_resources \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input-file examples/companies/vertex_foundry/data/experiments/pending_queue.json \
  --input optimization_objective="minimize_cost"
```

### Command - Balance Mode
```bash
sibyl pipeline run optimize_resources \
  --workspace examples/companies/vertex_foundry/config/workspace.yaml \
  --config examples/companies/vertex_foundry/config/pipelines.yaml \
  --input-file examples/companies/vertex_foundry/data/experiments/pending_queue.json \
  --input optimization_objective="balance"
```

## Expected Behavior

### Phase 1: Load Experiment Requirements
```
[2025-01-22 14:00:00] INFO: Starting pipeline: optimize_resources
[2025-01-22 14:00:00] INFO: Step 1/5: load_experiment_requirements
[2025-01-22 14:00:00] INFO: Loading pending experiments...
[2025-01-22 14:00:01] INFO: Loaded 10 experiments:
  - High priority: 4 experiments
  - Medium priority: 4 experiments
  - Low priority: 2 experiments
[2025-01-22 14:00:01] INFO: Total GPU requirements:
  - T4: 9 GPUs needed (4 available)
  - V100: 8 GPUs needed (3 available)
  - A100: 1 GPU needed (1 available)
[2025-01-22 14:00:01] WARN: Resource contention detected - optimization required
```

### Phase 2: Formulate Optimization Problem
```
[2025-01-22 14:00:01] INFO: Step 2/5: formulate_optimization
[2025-01-22 14:00:01] INFO: Optimization objective: maximize_throughput
[2025-01-22 14:00:02] INFO: Formulating mixed-integer programming problem...

[2025-01-22 14:00:03] INFO: Problem formulation:
  Decision Variables:
  - x_i ∈ {0, 1}: Whether experiment i is scheduled in wave 1
  - t_i ≥ 0: Start time for experiment i
  - c_i ≥ 0: Completion time for experiment i

  Objective Function:
  - Maximize: Σ(priority_i * x_i) - α * max(c_i)
  - Where α balances priority vs. completion time

  Constraints:
  - GPU capacity: Σ(gpu_req_i * active_i(t)) ≤ gpu_available for all t, all GPU types
  - Precedence: High priority experiments scheduled first
  - No preemption: Once started, experiment runs to completion
  - Resource exclusivity: One experiment per GPU at a time

[2025-01-22 14:00:03] INFO: Problem size:
  - Variables: 30 (10 binary, 20 continuous)
  - Constraints: 47
  - Complexity: Medium
```

### Phase 3: Solve Allocation Problem
```
[2025-01-22 14:00:03] INFO: Step 3/5: solve_allocation
[2025-01-22 14:00:03] INFO: Connecting to Solver MCP...
[2025-01-22 14:00:04] INFO: Solver type: mixed_integer_programming
[2025-01-22 14:00:04] INFO: Timeout: 60 seconds
[2025-01-22 14:00:04] INFO: Solving...

[2025-01-22 14:00:12] INFO: Solver progress:
  - Iteration 100: Best bound = 42.5, Incumbent = 38.2, Gap = 11.3%
[2025-01-22 14:00:18] INFO: Solver progress:
  - Iteration 200: Best bound = 41.1, Incumbent = 39.7, Gap = 3.5%
[2025-01-22 14:00:21] INFO: Solver progress:
  - Iteration 250: Best bound = 40.2, Incumbent = 40.0, Gap = 0.5%

[2025-01-22 14:00:22] INFO: Solution found!
[2025-01-22 14:00:22] INFO: Solver statistics:
  - Status: Optimal
  - Objective value: 40.0
  - Optimality gap: 0.3%
  - Solve time: 18.2 seconds
  - Iterations: 267
```

### Phase 4: Generate Allocation Plan
```
[2025-01-22 14:00:22] INFO: Step 4/5: create_allocation_plan
[2025-01-22 14:00:23] INFO: Translating solution to execution plan...

[2025-01-22 14:00:24] INFO: Optimal Allocation Plan:

WAVE 1 (Immediate Start - Time 0:00):
┌──────────┬─────────────────────────────┬──────────┬───────┬──────────┬──────┐
│ Exp ID   │ Name                        │ GPU Type │ Count │ Duration │ Cost │
├──────────┼─────────────────────────────┼──────────┼───────┼──────────┼──────┤
│ exp_101  │ Large ResNet Training       │ A100     │ 1     │ 8h       │ $20  │
│ exp_103  │ Model Ensembling            │ V100     │ 2     │ 6h       │ $12  │
│ exp_106  │ Fine-tuning BERT            │ V100     │ 1     │ 4h       │ $4   │
│ exp_102  │ Hyperparameter Sweep P1     │ T4       │ 4     │ 12h      │ $17  │
└──────────┴─────────────────────────────┴──────────┴───────┴──────────┴──────┘
GPU Utilization: 8/8 (100%)
Estimated Completion: 12 hours (exp_102 is critical path)
Total Cost: $53

WAVE 2 (Start at Time 4:00 - after exp_106 completes):
┌──────────┬─────────────────────────────┬──────────┬───────┬──────────┬──────┐
│ Exp ID   │ Name                        │ GPU Type │ Count │ Duration │ Cost │
├──────────┼─────────────────────────────┼──────────┼───────┼──────────┼──────┤
│ exp_109  │ Distillation Pipeline       │ V100     │ 2     │ 10h      │ $20  │
│ exp_110  │ Ablation Study              │ T4       │ 1     │ 4h       │ $1.4 │
└──────────┴─────────────────────────────┴──────────┴───────┴──────────┴──────┘
Note: Starts when V100 (exp_106) and T4 (from exp_102) become available

WAVE 3 (Start at Time 6:00 - after exp_103 completes):
┌──────────┬─────────────────────────────┬──────────┬───────┬──────────┬──────┐
│ Exp ID   │ Name                        │ GPU Type │ Count │ Duration │ Cost │
├──────────┼─────────────────────────────┼──────────┼───────┼──────────┼──────┤
│ exp_105  │ Architecture Search         │ V100     │ 3     │ 24h      │ $72  │
└──────────┴─────────────────────────────┴──────────┴───────┴──────────┴──────┘
Note: Requires all 3 V100s, starts when all available

WAVE 4 (Start at Time 8:00 - after exp_101 completes):
┌──────────┬─────────────────────────────┬──────────┬───────┬──────────┬──────┐
│ Exp ID   │ Name                        │ GPU Type │ Count │ Duration │ Cost │
├──────────┼─────────────────────────────┼──────────┼───────┼──────────┼──────┤
│ exp_108  │ Transfer Learning Baseline  │ T4       │ 2     │ 5h       │ $3.5 │
│ exp_107  │ Lightweight CNN Test        │ T4       │ 1     │ 2h       │ $0.7 │
│ exp_104  │ Data Augmentation Test      │ A100     │ 1     │ 3h       │ $7.5 │
└──────────┴─────────────────────────────┴──────────┴───────┴──────────┴──────┘

DEFERRED (Insufficient resources):
None - All experiments scheduled!

[2025-01-22 14:00:24] INFO: Schedule optimized for:
  - Primary goal: Maximize throughput
  - All high-priority experiments start in Wave 1
  - GPU utilization: 100% in Wave 1, 75%+ in subsequent waves
  - No idle GPU time
```

### Phase 5: Estimate Metrics
```
[2025-01-22 14:00:24] INFO: Step 5/5: estimate_metrics
[2025-01-22 14:00:25] INFO: Calculating completion time and cost...

[2025-01-22 14:00:26] INFO: Timeline Analysis:

Time 0h  ████████████ Wave 1 starts (4 experiments, 8 GPUs)
Time 4h  ██ exp_106 completes, exp_109 starts
Time 6h  ██ exp_103 completes, exp_105 starts
Time 8h  ██ exp_101, exp_110 complete, exp_104, exp_107, exp_108 start
Time 10h ██ exp_107 completes
Time 11h ██ exp_104 completes
Time 12h ██ exp_102 completes
Time 13h ██ exp_108 completes
Time 14h ██ exp_109 completes
Time 30h ████ exp_105 completes (last experiment)

COMPLETION METRICS:
  Total Completion Time: 30 hours
  Average Completion Time: 11.2 hours per experiment
  Weighted Completion Time (by priority): 8.5 hours

COST BREAKDOWN:
  A100: $27.50 (11 GPU-hours)
  V100: $93.00 (93 GPU-hours)
  T4: $29.75 (85 GPU-hours)
  Total: $150.25

EFFICIENCY METRICS:
  GPU Utilization: 87.3% (averaged over 30 hours)
  Priority Score: 40.0 (out of 45 max)
  Experiments Scheduled: 10/10 (100%)

[2025-01-22 14:00:26] SUCCESS: Pipeline completed successfully
```

## Pipeline Outputs

```json
{
  "allocation_plan": {
    "waves": [
      {
        "wave_id": 1,
        "start_time": "0h",
        "experiments": [
          {
            "exp_id": "exp_101",
            "name": "Large ResNet Training",
            "gpu_allocation": {"type": "A100", "count": 1},
            "duration_hours": 8,
            "cost_usd": 20.0
          },
          // ... more experiments
        ],
        "gpu_utilization": 1.0
      },
      // ... more waves
    ],
    "deferred_experiments": []
  },
  "expected_completion_time": "30 hours",
  "cost_estimate": 150.25,
  "efficiency_metrics": {
    "gpu_utilization": 0.873,
    "priority_score": 40.0,
    "completion_rate": 1.0
  }
}
```

## Comparison of Optimization Objectives

### Maximize Throughput (Default)
- Prioritizes completing experiments quickly
- Favors parallelization
- May use more expensive GPUs
- Best for time-critical projects

### Minimize Cost
- Prioritizes cheaper GPUs (T4 over V100/A100)
- May serialize some experiments
- Longer total completion time
- Best for budget-constrained scenarios

### Balance Mode
- Balances time vs. cost
- Considers priority weights more heavily
- Reasonable for most use cases

## Key Technical Details

### Optimization Problem Formulation
```
Objective: maximize Σ(priority_i * scheduled_i) - α * makespan

Subject to:
  1. GPU Capacity: Σ(gpu_demand_j(t)) ≤ gpu_available_j  ∀j,t
  2. Precedence: high_priority experiments scheduled before low_priority
  3. Non-overlap: experiments on same GPU don't overlap in time
  4. Completion: c_i = t_i + duration_i
  5. Makespan: makespan ≥ c_i  ∀i
```

### Solver MCP Integration
The Solver MCP:
1. Receives problem formulation as structured data
2. Selects appropriate algorithm (MIP solver)
3. Applies optimization with constraints
4. Returns optimal/near-optimal solution
5. Reports optimality gap and solve statistics

## Verification

### Check allocation feasibility
```bash
# Verify no GPU over-allocation at any time point
jq '.allocation_plan.waves[] | .experiments[] | {exp_id, gpu_allocation}' optimize_output.json

# Check that high-priority experiments run first
jq '.allocation_plan.waves[0].experiments[] | select(.priority == "high")' optimize_output.json
```

### Validate cost estimate
```bash
# Sum costs across all experiments
jq '[.allocation_plan.waves[].experiments[].cost_usd] | add' optimize_output.json
```

## Troubleshooting

### Infeasible solution
- Problem: Some experiments cannot be scheduled
- Cause: Resource requirements exceed availability
- Solution: Increase GPU resources or defer low-priority experiments

### Solver timeout
- Problem: Solver doesn't find optimal solution in time
- Cause: Problem too complex
- Solution: Increase timeout or accept suboptimal solution

### Poor utilization
- Problem: Many GPUs idle
- Cause: Experiment requirements don't match available GPUs
- Solution: Adjust experiment GPU requirements or add more diverse GPU types

## What This Demonstrates

1. **Solver MCP Integration**: Complex constraint satisfaction problems
2. **Mixed-Integer Programming**: Discrete allocation decisions
3. **Resource Optimization**: Multi-dimensional resource constraints
4. **Practical Value**: Real ML platform resource allocation problem
5. **Multiple Objectives**: Different optimization goals (cost, time, balance)
6. **Constraint Handling**: GPU capacity, precedence, non-overlap constraints

This scenario showcases how Sibyl can integrate with optimization solvers to solve practical infrastructure problems.
