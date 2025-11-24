"""Multi-source configuration aggregation system.

This module provides infrastructure for loading and merging configuration
from multiple sources with priority-based resolution:

Priority order (highest to lowest):
1. CLI arguments (priority 100)
2. Environment variables (priority 80)
3. Config file (priority 50)
4. Defaults (priority 0)

Example:
    from sibyl.mcp_server.infrastructure.config import (
        ConfigAggregator,
        YAMLConfigSource,
        EnvVarConfigSource,
        CLIArgsConfigSource,
    )

    # Create aggregator
    aggregator = ConfigAggregator()

    # Add sources (in any order - priority determines precedence)
    aggregator.add_source(YAMLConfigSource("config.yml"))
    # Framework configuration
    aggregator.add_source(EnvVarConfigSource(prefix="SIBYL_"))
    # Application-specific configuration (e.g., ExampleDomain)
    aggregator.add_source(EnvVarConfigSource(prefix="ExampleDomain_"))
    aggregator.add_source(CLIArgsConfigSource(sys.argv))

    # Get merged config
    config = aggregator.get_config()

    # Access values
    max_workers = config.get("max_workers", default=4)
    timeout = config.get("timeout", default=300)

Core Configuration:
    # For core Sibyl configuration (hardcoded constants now in YAML)
    from sibyl.config.loader import load_core_config, get_config_value

    # Load entire config or specific section
    agent_config = load_core_config('agent')
    max_tools = agent_config.get('max_tools_per_plan', 5)

    # Or use convenience function
    max_retries = get_config_value('llm', 'retry', 'max_retries', default=3)
"""

# Lazy imports handled in __getattr__ below
# Core config loader
from sibyl.config.loader import (
    get_agent_config,
    get_budget_config,
    get_checkpointing_config,
    get_config_value,
    get_consensus_config,
    get_graph_config,
    get_learning_config,
    get_llm_config,
    get_orchestration_config,
    get_performance_config,
    get_quality_control_config,
    get_security_config,
    get_session_config,
    load_core_config,
    reload_config,
)
from sibyl.config.protocol import (
    ConfigSource,
    ConfigValue,
)
from sibyl.config.sources import (
    CLIArgsConfigSource,
    DictConfigSource,
    EnvVarConfigSource,
    YAMLConfigSource,
)

# Config validator
from sibyl.config.validator import (
    ConfigValidationError,
    ConfigValidator,
    validate_config,
)

__all__ = [
    "CLIArgsConfigSource",
    # Aggregator
    "ConfigAggregator",
    # Protocol
    "ConfigSource",
    "ConfigValidationError",
    # Validator
    "ConfigValidator",
    "ConfigValue",
    "DictConfigSource",
    "EmbeddingsProviderConfig",
    "EnvVarConfigSource",
    "LLMProviderConfig",
    "MCPConfig",
    "MCPProviderConfig",
    "MCPToolConfig",
    "PipelineConfig",
    "PipelineStepConfig",
    "ProvidersConfig",
    "ShopConfig",
    "VectorStoreConfig",
    "WorkspaceLoadError",
    "WorkspaceSettings",
    # Sources
    "YAMLConfigSource",
    "get_agent_config",
    "get_budget_config",
    "get_checkpointing_config",
    "get_config_value",
    "get_consensus_config",
    "get_graph_config",
    "get_learning_config",
    "get_llm_config",
    "get_orchestration_config",
    "get_performance_config",
    "get_quality_control_config",
    "get_security_config",
    "get_session_config",
    "get_workspace_info",
    # Core config loader
    "load_core_config",
    # Workspace configuration
    "load_workspace",
    "load_workspace_dict",
    "reload_config",
    "validate_config",
    "validate_workspace_file",
]
