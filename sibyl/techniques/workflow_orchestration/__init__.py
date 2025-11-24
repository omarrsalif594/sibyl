"""
Workflow orchestration techniques.

This module provides convenient access to the main technique classes
for workflow orchestration:
- SessionManagementTechnique: Session lifecycle and rotation management
- GraphTechnique: Graph-based analysis and operations
- ContextManagementTechnique: Context window optimization
- OrchestrationTechnique: Workflow execution and orchestration
- OrchestrationStrategiesTechnique: Orchestration strategies (consensus, error reporting)

By importing from this module, users can avoid deep imports from submodules.

Example:
    from sibyl.techniques.workflow_orchestration import SessionManagementTechnique
    from sibyl.techniques.workflow_orchestration import GraphTechnique
    from sibyl.techniques.workflow_orchestration import ContextManagementTechnique
"""

from sibyl.techniques.workflow_orchestration.context_management.technique import (
    ContextManagementTechnique,
)
from sibyl.techniques.workflow_orchestration.graph.technique import (
    GraphTechnique,
)
from sibyl.techniques.workflow_orchestration.orchestration.technique import (
    OrchestrationTechnique,
)
from sibyl.techniques.workflow_orchestration.orchestration_strategies.technique import (
    OrchestrationStrategiesTechnique,
)
from sibyl.techniques.workflow_orchestration.session_management.technique import (
    SessionManagementTechnique,
)

__all__ = [
    "ContextManagementTechnique",
    "GraphTechnique",
    "OrchestrationStrategiesTechnique",
    "OrchestrationTechnique",
    "SessionManagementTechnique",
]
