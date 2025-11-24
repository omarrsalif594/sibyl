# Budget Allocation Technique

Provides configurable budget allocation across workflow phases (planning, execution, validation).

## Overview

Eliminates hardcoded values from `sibyl/core/orchestration/budget.py` by loading configuration from the core configuration system.

## Configuration

### Core Configuration (core_defaults.yaml)

```yaml
budget:
  model_selection:
    strategy: "downgrade_cascade"
    allow_downgrade: true
  model_tier_initial: 1
  phase_allocation:
    planning: 0.15    # 15% for planning
    execution: 0.70   # 70% for execution
    validation: 0.15  # 15% for validation
```

### Environment Variables

```bash
export SIBYL_BUDGET_MODEL_TIER_INITIAL=2
export SIBYL_BUDGET_PHASE_ALLOCATION_PLANNING=0.20
export SIBYL_BUDGET_PHASE_ALLOCATION_EXECUTION=0.65
export SIBYL_BUDGET_PHASE_ALLOCATION_VALIDATION=0.15
```

## Usage

```python
from sibyl.techniques.budget_allocation import BudgetAllocationTechnique

# Initialize technique
technique = BudgetAllocationTechnique()

# Allocate a $10 budget across phases
result = technique.execute(
    subtechnique="phase_based",
    total_budget=10.0
)

print(f"Planning: ${result['phase_budgets']['planning']:.2f}")
print(f"Execution: ${result['phase_budgets']['execution']:.2f}")
print(f"Validation: ${result['phase_budgets']['validation']:.2f}")
```

## Eliminated Hardcoded Values

This technique eliminates hardcoded values from `sibyl/core/orchestration/budget.py`:

- Model tier initial: line 189-209
- Phase allocation percentages: planning (15%), execution (70%), validation (15%)
- Model selection strategy
- Downgrade allowance flag

Total: **6 hardcoded values eliminated**
