"""
Base adapter class providing common functionality for all adapters.

This module standardizes config resolution, parameter defaulting, and result
normalization across all adapter types (LLM, embedding, opencode, etc.).
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """Standardized result format for all adapters."""

    status: Literal["success", "error"]
    data: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    fingerprint: dict[str, Any] | None = None

    def is_success(self) -> bool:
        """Check if the adapter call was successful."""
        return self.status == "success"

    def is_error(self) -> bool:
        """Check if the adapter call resulted in an error."""
        return self.status == "error"


@dataclass
class AdapterConfig:
    """Base configuration for all adapters."""

    adapter_type: str
    config_dict: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """
    Base adapter class providing standardized config resolution, parameter
    defaulting, and result normalization.

    All adapters (LLM, embedding, opencode, etc.) should inherit from this
    class to ensure consistent behavior across the framework.
    """

    def __init__(
        self,
        adapter_type: str,
        config: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize base adapter.

        Args:
            adapter_type: Type identifier (e.g., "openai", "anthropic", "mcp_llm")
            config: Adapter-specific configuration
            defaults: Default values for this adapter type
        """
        self.adapter_type = adapter_type
        self._raw_config = config or {}
        self._defaults = defaults or {}
        self._resolved_config = self._resolve_config()

        logger.debug(
            "Initialized %s adapter with config: %s", self.adapter_type, self._resolved_config
        )

    def _resolve_config(self) -> dict[str, Any]:
        """
        Resolve configuration with environment variable substitution.

        Supports:
        - ${ENV_VAR} syntax for environment variable references
        - Nested dictionary traversal
        - Default values from adapter defaults

        Returns:
            Resolved configuration dictionary
        """
        resolved = {}

        # Start with defaults
        resolved.update(self._defaults)

        # Apply user configuration
        for key, value in self._raw_config.items():
            resolved[key] = self._resolve_value(value)

        return resolved

    def _resolve_value(self, value: Any) -> Any:
        """
        Resolve a single configuration value.

        Args:
            value: Value to resolve (may contain env var references)

        Returns:
            Resolved value
        """
        if isinstance(value, str):
            # Check for environment variable reference
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved = os.getenv(env_var)
                if resolved is None:
                    logger.warning("Environment variable %s not set", env_var)
                    return None
                return resolved
            return value

        if isinstance(value, dict):
            return {k: self._resolve_value(v) for k, v in value.items()}

        if isinstance(value, list):
            return [self._resolve_value(v) for v in value]

        return value

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with optional default.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._resolved_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def merge_params(
        self, runtime_params: dict[str, Any] | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Merge parameters with precedence: runtime > adapter config > defaults.

        Args:
            runtime_params: Runtime parameter overrides
            **kwargs: Additional parameter overrides

        Returns:
            Merged parameters dictionary
        """
        merged = {}

        # Start with defaults
        merged.update(self._defaults)

        # Apply adapter configuration
        merged.update(self._resolved_config)

        # Apply runtime parameters
        if runtime_params:
            merged.update(runtime_params)

        # Apply kwargs (highest priority)
        merged.update(kwargs)

        return merged

    def normalize_result(
        self,
        raw_result: Any,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        fingerprint: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        Normalize adapter result to standard format.

        Args:
            raw_result: Raw result from adapter execution
            duration_ms: Execution duration in milliseconds
            metadata: Additional metadata about the execution
            fingerprint: Result fingerprint for tracking

        Returns:
            Normalized AdapterResult
        """
        return AdapterResult(
            status="success",
            data=raw_result,
            error=None,
            metadata=metadata or {"adapter_type": self.adapter_type},
            duration_ms=duration_ms or 0,
            fingerprint=fingerprint,
        )

    def normalize_error(
        self,
        error: Exception,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        Normalize adapter error to standard format.

        Args:
            error: Exception that occurred
            duration_ms: Execution duration in milliseconds
            metadata: Additional metadata about the execution

        Returns:
            Normalized AdapterResult with error status
        """
        error_metadata = metadata or {"adapter_type": self.adapter_type}
        error_metadata["error_type"] = type(error).__name__

        return AdapterResult(
            status="error",
            data=None,
            error=str(error),
            metadata=error_metadata,
            duration_ms=duration_ms or 0,
            fingerprint=None,
        )

    def execute_with_timing(self, func: Any, *args: Any, **kwargs: Any) -> tuple[Any, int]:
        """
        Execute a function and measure its duration.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (result, duration_ms)
        """
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            return result, duration_ms
        except Exception:
            duration_ms = int((time.time() - start_time) * 1000)
            raise

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> AdapterResult:
        """
        Execute adapter operation.

        This method must be implemented by concrete adapter classes.

        Returns:
            AdapterResult with operation result or error
        """

    def validate_config(self) -> bool:
        """
        Validate adapter configuration.

        Override this method to add adapter-specific validation.

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check for this adapter.

        Override this method to add adapter-specific health checks.

        Returns:
            Health status dictionary
        """
        return {
            "healthy": True,
            "adapter_type": self.adapter_type,
            "config_valid": self.validate_config(),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.adapter_type})"


class LLMAdapterBase(BaseAdapter):
    """Base class for LLM adapters (OpenAI, Anthropic, etc.)."""

    def __init__(
        self,
        adapter_type: str,
        config: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        # Default LLM parameters
        llm_defaults = {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 4096,
            "timeout_ms": 30000,
        }
        llm_defaults.update(defaults or {})

        super().__init__(adapter_type, config, llm_defaults)


class EmbeddingAdapterBase(BaseAdapter):
    """Base class for embedding adapters."""

    def __init__(
        self,
        adapter_type: str,
        config: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        # Default embedding parameters
        embedding_defaults = {
            "batch_size": 32,
            "dimension": 384,
        }
        embedding_defaults.update(defaults or {})

        super().__init__(adapter_type, config, embedding_defaults)


class VectorStoreAdapterBase(BaseAdapter):
    """Base class for vector store adapters."""

    def __init__(
        self,
        adapter_type: str,
        config: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        # Default vector store parameters
        vector_defaults = {
            "distance_metric": "cosine",
            "auto_create": True,
        }
        vector_defaults.update(defaults or {})

        super().__init__(adapter_type, config, vector_defaults)
