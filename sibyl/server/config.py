"""Configuration management with validation and hot-reload support.

This module provides centralized configuration for sibyl MCP server with:
- YAML file support (sibyl_config.yml)
- Environment variable overrides
- Validation with pydantic
- Hot-reload via SIGHUP signal
- Type-safe configuration classes

Configuration precedence (highest to lowest):
1. Environment variables (MCP_*)
2. YAML config file
3. Default values

Example sibyl_config.yml:
    rotation:
      enabled: true
      summarize_threshold_pct: 60
      rotate_threshold_pct: 70
      strategy: "summarize"

    server:
      http_host: "127.0.0.1"
      http_port: 8770
      log_level: "INFO"

Usage:
    # Load configuration
    config = load_config()

    # Access settings
    if config.rotation.enabled:
        threshold = config.rotation.summarize_threshold_pct

    # Hot-reload
    config.reload()
"""

import logging
import os
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import provider configs only (they don't have circular dependencies)
from sibyl.techniques.infrastructure.providers.config import (
    CapabilitiesConfig,
    ConnectionConfig,
    ModelConfig,
    ProviderConfig,
    ProvidersConfig,
    RateLimitsConfig,
)

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not installed, YAML config support disabled")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RotationConfig:
    """Configuration for automatic session rotation.

    Attributes:
        version: Configuration schema version (for migration compatibility)
        enabled: Whether session rotation is enabled
        summarize_threshold_pct: Percentage threshold for background summarization (default: 60)
        rotate_threshold_pct: Percentage threshold for rotation (default: 70)
        strategy: Rotation strategy: "summarize" | "fork" | "restart"
        model_adaptive: Whether to use model-adaptive thresholds
        user_overrides: User-specified threshold overrides (None = use defaults)
        max_session_rotations: Maximum rotations per conversation (0 = unlimited)
        rotation_timeout_seconds: Maximum time to wait for rotation (default: 30s)
        summarization_timeout_seconds: Maximum time for summarization (default: 10s)
    """

    version: str = "1.0.0"
    enabled: bool = True
    summarize_threshold_pct: float = 60.0
    rotate_threshold_pct: float = 70.0
    strategy: str = "summarize"  # "summarize" | "fork" | "restart"
    model_adaptive: bool = True
    user_overrides: dict[str, float] | None = None
    max_session_rotations: int = 0  # 0 = unlimited
    rotation_timeout_seconds: int = 30
    summarization_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        """Validate configuration."""
        # Validate thresholds
        if self.summarize_threshold_pct >= self.rotate_threshold_pct:
            msg = (
                f"summarize_threshold_pct ({self.summarize_threshold_pct}) must be < "
                f"rotate_threshold_pct ({self.rotate_threshold_pct})"
            )
            raise ValueError(msg)

        if not (0 <= self.summarize_threshold_pct <= 100):
            msg = f"summarize_threshold_pct must be 0-100, got {self.summarize_threshold_pct}"
            raise ValueError(msg)

        if not (0 <= self.rotate_threshold_pct <= 100):
            msg = f"rotate_threshold_pct must be 0-100, got {self.rotate_threshold_pct}"
            raise ValueError(msg)

        # Validate strategy
        if self.strategy not in ["summarize", "fork", "restart"]:
            msg = f"strategy must be 'summarize', 'fork', or 'restart', got '{self.strategy}'"
            raise ValueError(msg)

        # Validate timeouts
        if self.rotation_timeout_seconds <= 0:
            msg = f"rotation_timeout_seconds must be > 0, got {self.rotation_timeout_seconds}"
            raise ValueError(msg)

        if self.summarization_timeout_seconds <= 0:
            msg = f"summarization_timeout_seconds must be > 0, got {self.summarization_timeout_seconds}"
            raise ValueError(msg)


@dataclass(frozen=True)
class DuckDBConfig:
    """DuckDB state store configuration.

    Attributes:
        version: Configuration schema version (for migration compatibility)
        db_path: Path to DuckDB database file
        enable_wal: Whether to enable WAL mode
        memory_limit: Memory limit for DuckDB (e.g., "2GB", "512MB")
        threads: Number of threads for DuckDB
        wal_warning_threshold_mb: Threshold for WAL size warning (default 500MB)
        blobs_quota_mb: Maximum blob storage quota (default 1000MB)
        storage_check_interval_seconds: Interval for storage health checks (default 300s)
    """

    version: str = "1.0.0"
    # Default uses system temp dir for portability (Windows/Linux/Mac)
    db_path: str = ""  # Set in __post_init__
    enable_wal: bool = True
    memory_limit: str = "2GB"
    threads: int = 4
    wal_warning_threshold_mb: int = 500
    blobs_quota_mb: int = 1000
    storage_check_interval_seconds: int = 300

    def __post_init__(self) -> None:
        """Validate configuration."""
        # Set default db_path using system temp dir if not provided
        if not self.db_path:
            import tempfile
            from pathlib import Path

            self.db_path = str(Path(tempfile.gettempdir()) / "sibyl_state.duckdb")

        if self.threads <= 0:
            msg = f"threads must be > 0, got {self.threads}"
            raise ValueError(msg)

        if self.wal_warning_threshold_mb <= 0:
            msg = f"wal_warning_threshold_mb must be > 0, got {self.wal_warning_threshold_mb}"
            raise ValueError(msg)

        if self.blobs_quota_mb <= 0:
            msg = f"blobs_quota_mb must be > 0, got {self.blobs_quota_mb}"
            raise ValueError(msg)

        if self.storage_check_interval_seconds <= 0:
            msg = f"storage_check_interval_seconds must be > 0, got {self.storage_check_interval_seconds}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ObservabilityConfig:
    """Observability configuration.

    Attributes:
        version: Configuration schema version (for migration compatibility)
        metrics_enabled: Whether to export metrics
        metrics_export_interval_seconds: How often to export metrics
        structured_logging: Whether to use structured JSON logging
        trace_sampling_rate: Sampling rate for traces (0.0-1.0)
    """

    version: str = "1.0.0"
    metrics_enabled: bool = True
    metrics_export_interval_seconds: int = 60
    structured_logging: bool = False
    trace_sampling_rate: float = 0.1

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.trace_sampling_rate <= 1.0):
            msg = f"trace_sampling_rate must be 0.0-1.0, got {self.trace_sampling_rate}"
            raise ValueError(msg)


@dataclass(frozen=True)
class QualityControlConfig:
    """Quality control configuration.

    Attributes:
        version: Configuration schema version (for migration compatibility)
        enabled: Whether quality control validation is enabled
        max_retries: Maximum number of retry attempts on RED verdicts (default: 2)
        retry_on_yellow: Whether to retry on YELLOW verdicts (default: False)
        validators: List of validator names to enable (empty = all enabled)
        syntax_check_enabled: Whether to perform SQL syntax validation
        anti_pattern_check_enabled: Whether to check for SQL anti-patterns
        type_check_enabled: Whether to validate column types and functions
        schema_check_enabled: Whether to validate against source schemas
        timeout_seconds: Maximum time for validation (default: 10s)
    """

    version: str = "1.0.0"
    enabled: bool = True
    max_retries: int = 2
    retry_on_yellow: bool = False
    validators: tuple[str, ...] = field(
        default_factory=tuple
    )  # Use tuple for frozen (empty = all enabled)
    syntax_check_enabled: bool = True
    anti_pattern_check_enabled: bool = True
    type_check_enabled: bool = True
    schema_check_enabled: bool = False  # Requires external warehouse credentials
    timeout_seconds: int = 10

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_retries < 0:
            msg = f"max_retries must be >= 0, got {self.max_retries}"
            raise ValueError(msg)

        if self.timeout_seconds <= 0:
            msg = f"timeout_seconds must be > 0, got {self.timeout_seconds}"
            raise ValueError(msg)


# Re-export from new location
__all__ = [
    "CapabilitiesConfig",
    "Config",
    "ConnectionConfig",
    "DuckDBConfig",
    "ModelConfig",
    "ObservabilityConfig",
    "ProviderConfig",
    "ProvidersConfig",
    "QualityControlConfig",
    "RateLimitsConfig",
    "RotationConfig",
    "ServerConfig",
    "get_config",
    "load_config",
    "setup_hot_reload",
]


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration.

    Attributes:
        version: Configuration schema version (for migration compatibility)
        http_host: HTTP server bind address
        http_port: HTTP server port
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        workspace_root: Sibyl workspace root directory
        architecture_version: MCP architecture version ("v1" | "v2")
    """

    version: str = "1.0.0"
    http_host: str = "127.0.0.1"
    http_port: int = 8770
    log_level: str = "INFO"
    log_file: str = ""  # Set in __post_init__
    workspace_root: str | None = None
    architecture_version: str = "v1"

    def __post_init__(self) -> None:
        """Validate configuration."""
        # Set default log_file using system temp dir if not provided
        if not self.log_file:
            import tempfile
            from pathlib import Path

            self.log_file = str(Path(tempfile.gettempdir()) / "sibyl_mcp.log")
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            msg = f"log_level must be one of {valid_levels}, got '{self.log_level}'"
            raise ValueError(msg)

        # Validate architecture version
        if self.architecture_version not in ["v1", "v2"]:
            msg = f"architecture_version must be 'v1' or 'v2', got '{self.architecture_version}'"
            raise ValueError(msg)

        # Normalize workspace_root (use object.__setattr__ for frozen dataclass)
        if self.workspace_root:
            normalized_path = str(Path(self.workspace_root).expanduser().resolve())
            object.__setattr__(self, "workspace_root", normalized_path)


@dataclass
class Config:
    """Root configuration object.

    Attributes:
        rotation: Session rotation configuration
        server: Server configuration
        duckdb: DuckDB configuration
        observability: Observability configuration
        quality_control: Quality control configuration
        providers: Provider configuration
        _config_path: Path to config file (for hot-reload)
        _reload_callbacks: Callbacks to invoke on config reload
    """

    rotation: RotationConfig = field(default_factory=RotationConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    duckdb: DuckDBConfig = field(default_factory=DuckDBConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    quality_control: QualityControlConfig = field(default_factory=QualityControlConfig)
    providers: ProvidersConfig | None = None
    _config_path: Path | None = None
    _reload_callbacks: list = field(default_factory=list)

    def register_reload_callback(self, callback: Any) -> None:
        """Register a callback to be called on config reload.

        Args:
            callback: Async function(apply_to_existing: bool) -> None
        """
        self._reload_callbacks.append(callback)
        logger.info("Registered reload callback: %s", callback.__name__)

    def reload(self, apply_to_existing_sessions: bool = False) -> None:
        """Reload configuration from file and environment.

        This is called on SIGHUP for hot-reload. By default, only affects
        new sessions. Set apply_to_existing_sessions=True to update
        existing sessions (use with caution).

        Args:
            apply_to_existing_sessions: If True, update thresholds for existing sessions
        """
        if self._config_path and self._config_path.exists():
            if apply_to_existing_sessions:
                logger.warning(
                    "⚠️  Reloading config for EXISTING sessions - use with caution! "
                    "This will update thresholds for all active sessions."
                )
            else:
                logger.info("Reloading config for NEW sessions only (existing sessions unaffected)")

            logger.info("Reloading configuration from %s", self._config_path)
            reloaded_config = load_config(config_path=self._config_path)

            # Update in-place (use object.__setattr__ for frozen child configs)
            object.__setattr__(self, "rotation", reloaded_config.rotation)
            object.__setattr__(self, "server", reloaded_config.server)
            object.__setattr__(self, "duckdb", reloaded_config.duckdb)
            object.__setattr__(self, "observability", reloaded_config.observability)
            object.__setattr__(self, "quality_control", reloaded_config.quality_control)
            object.__setattr__(self, "providers", reloaded_config.providers)

            # Invoke reload callbacks
            if self._reload_callbacks:
                import asyncio

                logger.info("Invoking %s reload callbacks...", len(self._reload_callbacks))
                for callback in self._reload_callbacks:
                    try:
                        # Run callback
                        if asyncio.iscoroutinefunction(callback):
                            # Async callback - need event loop
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                            loop.run_until_complete(callback(apply_to_existing_sessions))
                        else:
                            # Sync callback
                            callback(apply_to_existing_sessions)

                        logger.info("✓ Reload callback %s completed", callback.__name__)
                    except Exception as e:
                        logger.exception("✗ Reload callback %s failed: %s", callback.__name__, e)

            logger.info("Configuration reloaded successfully")
        else:
            logger.warning("Config file not found, skipping reload")

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dict representation of config with version fields
        """
        return {
            "rotation": {
                "version": self.rotation.version,
                "enabled": self.rotation.enabled,
                "summarize_threshold_pct": self.rotation.summarize_threshold_pct,
                "rotate_threshold_pct": self.rotation.rotate_threshold_pct,
                "strategy": self.rotation.strategy,
                "model_adaptive": self.rotation.model_adaptive,
                "user_overrides": self.rotation.user_overrides,
                "max_session_rotations": self.rotation.max_session_rotations,
                "rotation_timeout_seconds": self.rotation.rotation_timeout_seconds,
                "summarization_timeout_seconds": self.rotation.summarization_timeout_seconds,
            },
            "server": {
                "version": self.server.version,
                "http_host": self.server.http_host,
                "http_port": self.server.http_port,
                "log_level": self.server.log_level,
                "log_file": self.server.log_file,
                "workspace_root": self.server.workspace_root,
                "architecture_version": self.server.architecture_version,
            },
            "duckdb": {
                "version": self.duckdb.version,
                "db_path": self.duckdb.db_path,
                "enable_wal": self.duckdb.enable_wal,
                "memory_limit": self.duckdb.memory_limit,
                "threads": self.duckdb.threads,
            },
            "observability": {
                "version": self.observability.version,
                "metrics_enabled": self.observability.metrics_enabled,
                "metrics_export_interval_seconds": self.observability.metrics_export_interval_seconds,
                "structured_logging": self.observability.structured_logging,
                "trace_sampling_rate": self.observability.trace_sampling_rate,
            },
            "quality_control": {
                "version": self.quality_control.version,
                "enabled": self.quality_control.enabled,
                "max_retries": self.quality_control.max_retries,
                "retry_on_yellow": self.quality_control.retry_on_yellow,
                "validators": list(
                    self.quality_control.validators
                ),  # Convert tuple to list for JSON
                "syntax_check_enabled": self.quality_control.syntax_check_enabled,
                "anti_pattern_check_enabled": self.quality_control.anti_pattern_check_enabled,
                "type_check_enabled": self.quality_control.type_check_enabled,
                "schema_check_enabled": self.quality_control.schema_check_enabled,
                "timeout_seconds": self.quality_control.timeout_seconds,
            },
            "providers": {
                "version": self.providers.version if self.providers else "1.0.0",
                "default_llm_provider": (
                    self.providers.default_llm_provider if self.providers else "anthropic"
                ),
                "default_embedding_provider": (
                    self.providers.default_embedding_provider
                    if self.providers
                    else "sentence-transformer"
                ),
            },
        }


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from YAML file and environment variables.

    Precedence (highest to lowest):
    1. Environment variables (MCP_*)
    2. YAML config file
    3. Default values

    Args:
        config_path: Optional path to config YAML file (default: ./sibyl_config.yml)

    Returns:
        Config object

    Environment variables:
        MCP_ROTATION_ENABLED: Enable/disable rotation (true/false)
        MCP_ROTATION_SUMMARIZE_PCT: Summarize threshold percentage
        MCP_ROTATION_ROTATE_PCT: Rotate threshold percentage
        MCP_ROTATION_STRATEGY: Rotation strategy (summarize/fork/restart)
        MCP_HTTP_HOST: HTTP server host
        MCP_HTTP_PORT: HTTP server port
        MCP_LOG_LEVEL: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        SIBYL_WORKSPACE_ROOT: Sibyl workspace root directory
        MCP_LAYOUT: Architecture version (v1/v2)
    """
    # Start with defaults
    config = Config()

    # Load from YAML if available
    if config_path is None:
        config_path = Path("sibyl_config.yml")

    if config_path.exists() and YAML_AVAILABLE:
        logger.info("Loading configuration from %s", config_path)
        try:
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f) or {}

            # Parse rotation config
            if "rotation" in yaml_config:
                rotation_dict = yaml_config["rotation"]
                config.rotation = RotationConfig(
                    version=rotation_dict.get("version", config.rotation.version),
                    enabled=rotation_dict.get("enabled", config.rotation.enabled),
                    summarize_threshold_pct=rotation_dict.get(
                        "summarize_threshold_pct", config.rotation.summarize_threshold_pct
                    ),
                    rotate_threshold_pct=rotation_dict.get(
                        "rotate_threshold_pct", config.rotation.rotate_threshold_pct
                    ),
                    strategy=rotation_dict.get("strategy", config.rotation.strategy),
                    model_adaptive=rotation_dict.get(
                        "model_adaptive", config.rotation.model_adaptive
                    ),
                    user_overrides=rotation_dict.get(
                        "user_overrides", config.rotation.user_overrides
                    ),
                    max_session_rotations=rotation_dict.get(
                        "max_session_rotations", config.rotation.max_session_rotations
                    ),
                    rotation_timeout_seconds=rotation_dict.get(
                        "rotation_timeout_seconds", config.rotation.rotation_timeout_seconds
                    ),
                    summarization_timeout_seconds=rotation_dict.get(
                        "summarization_timeout_seconds",
                        config.rotation.summarization_timeout_seconds,
                    ),
                )

            # Parse server config
            if "server" in yaml_config:
                server_dict = yaml_config["server"]
                config.server = ServerConfig(
                    version=server_dict.get("version", config.server.version),
                    http_host=server_dict.get("http_host", config.server.http_host),
                    http_port=server_dict.get("http_port", config.server.http_port),
                    log_level=server_dict.get("log_level", config.server.log_level),
                    log_file=server_dict.get("log_file", config.server.log_file),
                    workspace_root=server_dict.get("workspace_root", config.server.workspace_root),
                    architecture_version=server_dict.get(
                        "architecture_version", config.server.architecture_version
                    ),
                )

            # Parse DuckDB config
            if "duckdb" in yaml_config:
                duckdb_dict = yaml_config["duckdb"]
                config.duckdb = DuckDBConfig(
                    version=duckdb_dict.get("version", config.duckdb.version),
                    db_path=duckdb_dict.get("db_path", config.duckdb.db_path),
                    enable_wal=duckdb_dict.get("enable_wal", config.duckdb.enable_wal),
                    memory_limit=duckdb_dict.get("memory_limit", config.duckdb.memory_limit),
                    threads=duckdb_dict.get("threads", config.duckdb.threads),
                )

            # Parse observability config
            if "observability" in yaml_config:
                obs_dict = yaml_config["observability"]
                config.observability = ObservabilityConfig(
                    version=obs_dict.get("version", config.observability.version),
                    metrics_enabled=obs_dict.get(
                        "metrics_enabled", config.observability.metrics_enabled
                    ),
                    metrics_export_interval_seconds=obs_dict.get(
                        "metrics_export_interval_seconds",
                        config.observability.metrics_export_interval_seconds,
                    ),
                    structured_logging=obs_dict.get(
                        "structured_logging", config.observability.structured_logging
                    ),
                    trace_sampling_rate=obs_dict.get(
                        "trace_sampling_rate", config.observability.trace_sampling_rate
                    ),
                )

            # Parse quality control config
            if "quality_control" in yaml_config:
                qc_dict = yaml_config["quality_control"]

                config.quality_control = QualityControlConfig(
                    version=qc_dict.get("version", config.quality_control.version),
                    enabled=qc_dict.get("enabled", config.quality_control.enabled),
                    max_retries=qc_dict.get("max_retries", config.quality_control.max_retries),
                    retry_on_yellow=qc_dict.get(
                        "retry_on_yellow", config.quality_control.retry_on_yellow
                    ),
                    validators=qc_dict.get("validators", config.quality_control.validators),
                    syntax_check_enabled=qc_dict.get(
                        "syntax_check_enabled", config.quality_control.syntax_check_enabled
                    ),
                    anti_pattern_check_enabled=qc_dict.get(
                        "anti_pattern_check_enabled",
                        config.quality_control.anti_pattern_check_enabled,
                    ),
                    type_check_enabled=qc_dict.get(
                        "type_check_enabled", config.quality_control.type_check_enabled
                    ),
                    schema_check_enabled=qc_dict.get(
                        "schema_check_enabled", config.quality_control.schema_check_enabled
                    ),
                    timeout_seconds=qc_dict.get(
                        "timeout_seconds", config.quality_control.timeout_seconds
                    ),
                )

            # Parse providers config (complex nested structure)
            if "providers" in yaml_config:
                providers_dict = yaml_config["providers"]

                # Parse LLM providers
                llm_providers = {}
                if "llm" in providers_dict:
                    for provider_name, provider_data in providers_dict["llm"].items():
                        # Parse connection config
                        connection = ConnectionConfig(
                            api_key_env=provider_data.get("connection", {}).get("api_key_env"),
                            endpoint=provider_data.get("connection", {}).get("endpoint"),
                            timeout_seconds=provider_data.get("connection", {}).get(
                                "timeout_seconds", 30
                            ),
                            max_retries=provider_data.get("connection", {}).get("max_retries", 3),
                        )

                        # Parse capabilities config
                        caps_data = provider_data.get("capabilities", {})
                        capabilities = CapabilitiesConfig(
                            supports_structured=caps_data.get("supports_structured", False),
                            supports_seed=caps_data.get("supports_seed", False),
                            supports_streaming=caps_data.get("supports_streaming", False),
                            supports_tools=caps_data.get("supports_tools", False),
                            max_tokens_limit=caps_data.get("max_tokens_limit", 4096),
                            embedding_dim=caps_data.get("embedding_dim"),
                            token_counting_method=caps_data.get(
                                "token_counting_method", "estimate"
                            ),
                        )

                        # Parse rate limits config
                        rate_limits_data = provider_data.get("rate_limits", {})
                        rate_limits = RateLimitsConfig(
                            requests_per_minute=rate_limits_data.get("requests_per_minute"),
                            tokens_per_minute=rate_limits_data.get("tokens_per_minute"),
                            concurrent_requests=rate_limits_data.get("concurrent_requests", 10),
                        )

                        # Parse models
                        models = []
                        for model_data in provider_data.get("models", []):
                            model = ModelConfig(
                                name=model_data["name"],
                                cost_per_1k_input=model_data.get("cost_per_1k_input", 0.0),
                                cost_per_1k_output=model_data.get("cost_per_1k_output", 0.0),
                                max_tokens=model_data.get("max_tokens", 4096),
                                quality_score=model_data.get("quality_score", 5),
                                aliases=tuple(model_data.get("aliases", [])),
                            )
                            models.append(model)

                        # Create provider config
                        provider_config = ProviderConfig(
                            name=provider_name,
                            type=provider_data.get("type", "api"),
                            connection=connection,
                            capabilities=capabilities,
                            rate_limits=rate_limits,
                            models=tuple(models),
                            enabled=provider_data.get("enabled", True),
                        )

                        llm_providers[provider_name] = provider_config

                # Parse embedding providers (similar structure)
                embedding_providers = {}
                if "embedding" in providers_dict:
                    for provider_name, provider_data in providers_dict["embedding"].items():
                        connection = ConnectionConfig(
                            api_key_env=provider_data.get("connection", {}).get("api_key_env"),
                            endpoint=provider_data.get("connection", {}).get("endpoint"),
                        )

                        caps_data = provider_data.get("capabilities", {})
                        capabilities = CapabilitiesConfig(
                            embedding_dim=caps_data.get("embedding_dim", 384),
                            max_tokens_limit=caps_data.get("max_tokens_limit", 512),
                        )

                        provider_config = ProviderConfig(
                            name=provider_name,
                            type=provider_data.get("type", "local"),
                            connection=connection,
                            capabilities=capabilities,
                            enabled=provider_data.get("enabled", True),
                        )

                        embedding_providers[provider_name] = provider_config

                # Create ProvidersConfig
                config.providers = ProvidersConfig(
                    version=providers_dict.get("version", "1.0.0"),
                    llm=llm_providers,
                    embedding=embedding_providers,
                    default_llm_provider=providers_dict.get("default_llm_provider", "anthropic"),
                    default_embedding_provider=providers_dict.get(
                        "default_embedding_provider", "sentence-transformer"
                    ),
                )

                logger.info(
                    f"Loaded {len(llm_providers)} LLM providers, "
                    f"{len(embedding_providers)} embedding providers"
                )

            logger.info("Configuration loaded from %s", config_path)

        except Exception as e:
            logger.warning("Failed to load config from %s: %s", config_path, e)
            logger.info("Using default configuration with environment overrides")

    # Store config path for hot-reload
    config._config_path = config_path if config_path.exists() else None

    # Apply environment variable overrides (highest precedence)
    # Rotation config
    if os.getenv("MCP_ROTATION_ENABLED"):
        config.rotation = RotationConfig(
            **{
                **config.rotation.__dict__,
                "enabled": os.getenv("MCP_ROTATION_ENABLED").lower() == "true",
            }
        )

    if os.getenv("MCP_ROTATION_SUMMARIZE_PCT"):
        config.rotation = RotationConfig(
            **{
                **config.rotation.__dict__,
                "summarize_threshold_pct": float(os.getenv("MCP_ROTATION_SUMMARIZE_PCT")),
            }
        )

    if os.getenv("MCP_ROTATION_ROTATE_PCT"):
        config.rotation = RotationConfig(
            **{
                **config.rotation.__dict__,
                "rotate_threshold_pct": float(os.getenv("MCP_ROTATION_ROTATE_PCT")),
            }
        )

    if os.getenv("MCP_ROTATION_STRATEGY"):
        config.rotation = RotationConfig(
            **{**config.rotation.__dict__, "strategy": os.getenv("MCP_ROTATION_STRATEGY")}
        )

    # Server config
    if os.getenv("MCP_HTTP_HOST"):
        config.server = ServerConfig(
            **{**config.server.__dict__, "http_host": os.getenv("MCP_HTTP_HOST")}
        )

    if os.getenv("MCP_HTTP_PORT"):
        config.server = ServerConfig(
            **{**config.server.__dict__, "http_port": int(os.getenv("MCP_HTTP_PORT"))}
        )

    if os.getenv("MCP_LOG_LEVEL"):
        config.server = ServerConfig(
            **{**config.server.__dict__, "log_level": os.getenv("MCP_LOG_LEVEL")}
        )

    if os.getenv("SIBYL_WORKSPACE_ROOT"):
        config.server = ServerConfig(
            **{**config.server.__dict__, "workspace_root": os.getenv("SIBYL_WORKSPACE_ROOT")}
        )

    if os.getenv("MCP_LAYOUT"):
        config.server = ServerConfig(
            **{**config.server.__dict__, "architecture_version": os.getenv("MCP_LAYOUT")}
        )

    # DuckDB config
    if os.getenv("MCP_DUCKDB_PATH"):
        config.duckdb = DuckDBConfig(
            **{**config.duckdb.__dict__, "db_path": os.getenv("MCP_DUCKDB_PATH")}
        )

    # Final validation (recreate objects to trigger __post_init__ validation)
    try:
        config.rotation = RotationConfig(**config.rotation.__dict__)
        config.server = ServerConfig(**config.server.__dict__)
        config.duckdb = DuckDBConfig(**config.duckdb.__dict__)
        config.observability = ObservabilityConfig(**config.observability.__dict__)
        config.quality_control = QualityControlConfig(**config.quality_control.__dict__)
    except ValueError as e:
        logger.exception("Configuration validation failed: %s", e)
        raise

    return config


def setup_hot_reload(config: Config) -> None:
    """Setup SIGHUP handler for configuration hot-reload.

    Args:
        config: Config object to reload on signal

    Example:
        config = load_config()
        setup_hot_reload(config)
        # ... server runs ...
        # User sends: kill -HUP <pid>
        # → config.reload() is called
    """

    def handle_sighup(signum, frame: Any) -> None:
        """Handle SIGHUP signal."""
        logger.info("Received SIGHUP, reloading configuration...")
        try:
            config.reload()
        except Exception as e:
            logger.exception("Failed to reload configuration: %s", e)

    # Register signal handler
    signal.signal(signal.SIGHUP, handle_sighup)
    logger.info("Hot-reload enabled: send SIGHUP to reload configuration")


# Global config instance (lazy-loaded)
_global_config: Config | None = None


def get_config() -> Config:
    """Get global config instance (singleton pattern).

    Returns:
        Config object
    """
    global _global_config

    if _global_config is None:
        _global_config = load_config()

    return _global_config
