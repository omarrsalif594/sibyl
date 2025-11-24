# Configuration Module

This directory contains configuration infrastructure and core configuration files.

## Current Status

### Workspace Configuration → MOVED ✅
- **Old location**: `sibyl.config.workspace_loader`, `sibyl.config.workspace_schema`
- **New location**: `sibyl.workspace` (see `sibyl/workspace/`)

### Active Configuration Infrastructure

The following files remain for non-workspace configuration:

#### Core Configuration
- **`loader.py`**: Core configuration loader (loads `core_defaults.yaml`)
- **`core_defaults.yaml`**: Hardcoded defaults for agent, LLM, orchestration, etc.
- **`schema.yaml`**: Configuration schema definitions

#### Multi-Source Configuration System
- **`protocol.py`**: Configuration source protocol and types
- **`sources.py`**: Configuration sources (YAML, env vars, CLI args, etc.)
- **`aggregator.py`**: Multi-source configuration aggregator with priority resolution
- **`validator.py`**: Configuration validation against schema

### Purpose

These files support the multi-source configuration system used by:
- Core defaults and hardcoded constants
- Configuration aggregation from multiple sources (files, env vars, CLI)

### Future

- Workspace-related configuration should use `sibyl.workspace`
- Core configuration infrastructure remains for system-level settings
- Consider migrating to a more modern configuration approach in future versions

## Usage

### For Workspace Configuration (NEW)
```python
from sibyl.workspace import load_workspace, WorkspaceSettings

workspace = load_workspace("config/workspaces/example.yaml")
```

### For Core Configuration (EXISTING)
```python
from sibyl.config import load_core_config, get_config_value

# Load entire config section
agent_config = load_core_config('agent')
max_tools = agent_config.get('max_tools_per_plan', 5)

# Or use convenience function
max_retries = get_config_value('llm', 'retry', 'max_retries', default=3)
```
