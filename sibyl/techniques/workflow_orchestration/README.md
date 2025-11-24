# Workflow Orchestration

This category contains techniques for orchestrating complex multi-step workflows and managing
execution sessions.

## Overview

Workflow orchestration techniques handle the coordination of multi-phase LLM operations,
session management, context lifecycle, and graph-based dependencies.

## Techniques

- **context_management**: Context management
- **graph**: Graph operations
- **orchestration**: Workflow orchestration
- **orchestration_strategies**: Orchestration strategies
- **session_management**: Session management

## Architecture

```
Workflow Definition → Orchestrator → Session Manager → Context Manager
                           ↓                ↓
                      Graph Engine    Session State
                           ↓                ↓
                    Execution Steps   Budget Tracking
```

## Usage

```python
from sibyl.techniques.workflow_orchestration.orchestration import OrchestrationTechnique
from sibyl.techniques.workflow_orchestration.session_management import SessionManagementTechnique

# Create orchestrator
orchestrator = OrchestrationTechnique(...)

# Manage sessions
session_manager = SessionManagementTechnique(...)
```

## Core Integration

Core engines for these techniques are located in:
- `sibyl/core/workflow_orchestration/`

The orchestration engine coordinates between techniques and manages workflow execution.
