"""
Rotation-based Session Management Implementation

This implementation provides session lifecycle management with:
- Token-based rotation triggers with configurable thresholds
- Circuit breaker for graceful degradation on failures
- Operation draining to ensure clean rotation boundaries
- Generation counters for atomic session swaps

Configuration Sources:
- sibyl/core/config/core_defaults.yaml::session.rotation
- sibyl/core/config/core_defaults.yaml::session.circuit_breaker

Eliminates Hardcoded Constants From:
- sibyl/core/session/rotation_manager.py (lines 77, 79-80, 217-218, 268, 337, 413)
- sibyl/core/session/circuit_breaker.py (lines 105-107)
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class RotationStatus(str, Enum):
    """Status of rotation check."""

    CONTINUE = "continue"  # Below thresholds, continue with current session
    SHOULD_SUMMARIZE = "should_summarize"  # Early threshold reached, summarize context
    SHOULD_ROTATE = "should_rotate"  # Force threshold reached, rotate session
    ROTATION_IN_PROGRESS = "rotation_in_progress"  # Rotation already in progress
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker open, degraded mode


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RotationCheckResult:
    """Result of rotation check."""

    status: RotationStatus
    reason: str
    utilization_pct: float
    tokens_used: int
    tokens_budget: int
    circuit_state: CircuitState
    should_rotate: bool
    should_summarize: bool
    metadata: dict[str, Any]


@dataclass
class SessionRotationConfig:
    """Parsed configuration for session rotation."""

    operation_poll_ms: int
    status_log_interval_seconds: int
    early_rotation_threshold: float
    force_rotation_threshold: float
    rotation_timeout_seconds: int
    failure_threshold: int
    recovery_timeout_seconds: int
    half_open_max_calls: int

    # Session defaults
    default_tokens_budget: int
    default_model_name: str
    enable_generation_counter: bool
    enable_operation_tracking: bool

    # Observability
    log_rotation_events: bool
    log_circuit_breaker_events: bool
    emit_metrics: bool
    enable_tracing: bool


class RotationManagerImplementation:
    """
    Rotation-based session management implementation.

    This implementation manages session lifecycle with:
    1. Token-based rotation triggers (early warning + force rotation)
    2. Circuit breaker for graceful degradation
    3. Operation draining for clean boundaries
    4. Generation counters for atomic swaps

    Configuration is loaded from:
    - Technique config (config.yaml)
    - Global config (core_defaults.yaml::session.*)
    - Environment variables (SIBYL_SESSION_*)

    Eliminates hardcoded values from:
    - rotation_manager.py: poll interval (100ms), thresholds (60%, 70%), timeout (30s)
    - circuit_breaker.py: failure threshold (3), recovery timeout (30s), half-open calls (1)
    """

    def __init__(self) -> None:
        self._name = "rotation_manager"
        self._description = "Session rotation with circuit breaker and operation draining"
        self._config_path = Path(__file__).parent / "config.yaml"
        self._default_config = self._load_default_config()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> RotationCheckResult:
        """
        Execute rotation check and return decision.

        Args:
            input_data: Dict with:
                - tokens_used: Current token usage
                - tokens_budget: Total token budget
                - session_id: Session identifier
                - rotation_in_progress: Whether rotation is already in progress
                - circuit_state: Current circuit breaker state (optional)
                - generation: Current session generation (optional)
            config: Merged configuration (cascade result)

        Returns:
            RotationCheckResult with decision and metadata

        Raises:
            ValueError: If input_data is invalid
        """
        # Validate input
        self._validate_input(input_data)

        # Parse configuration with environment variable overrides
        parsed_config = self._parse_config(config)

        # Extract input data
        tokens_used = input_data.get("tokens_used", 0)
        tokens_budget = input_data.get("tokens_budget", parsed_config.default_tokens_budget)
        session_id = input_data.get("session_id", "unknown")
        rotation_in_progress = input_data.get("rotation_in_progress", False)
        circuit_state_str = input_data.get("circuit_state", "closed")
        generation = input_data.get("generation", 1)

        # Parse circuit state
        try:
            circuit_state = CircuitState(circuit_state_str)
        except ValueError:
            circuit_state = CircuitState.CLOSED

        # Calculate utilization percentage
        utilization_pct = (tokens_used / tokens_budget * 100.0) if tokens_budget > 0 else 0.0

        # Build metadata
        metadata = {
            "session_id": session_id,
            "generation": generation,
            "early_rotation_threshold_pct": parsed_config.early_rotation_threshold * 100,
            "force_rotation_threshold_pct": parsed_config.force_rotation_threshold * 100,
            "operation_poll_ms": parsed_config.operation_poll_ms,
            "rotation_timeout_seconds": parsed_config.rotation_timeout_seconds,
            "failure_threshold": parsed_config.failure_threshold,
            "recovery_timeout_seconds": parsed_config.recovery_timeout_seconds,
        }

        # Check circuit breaker state first
        if circuit_state == CircuitState.OPEN:
            if parsed_config.log_circuit_breaker_events:
                logger.warning("[%s] Circuit breaker OPEN, using degraded mode", session_id)
            return RotationCheckResult(
                status=RotationStatus.CIRCUIT_OPEN,
                reason="Circuit breaker is OPEN, using fallback behavior",
                utilization_pct=utilization_pct,
                tokens_used=tokens_used,
                tokens_budget=tokens_budget,
                circuit_state=circuit_state,
                should_rotate=False,
                should_summarize=False,
                metadata=metadata,
            )

        # Check if rotation already in progress
        if rotation_in_progress:
            if parsed_config.log_rotation_events:
                logger.info("[%s] Rotation already in progress, skipping check", session_id)
            return RotationCheckResult(
                status=RotationStatus.ROTATION_IN_PROGRESS,
                reason="Rotation already in progress for this session",
                utilization_pct=utilization_pct,
                tokens_used=tokens_used,
                tokens_budget=tokens_budget,
                circuit_state=circuit_state,
                should_rotate=False,
                should_summarize=False,
                metadata=metadata,
            )

        # Convert thresholds to percentages for comparison
        early_threshold_pct = parsed_config.early_rotation_threshold * 100
        force_threshold_pct = parsed_config.force_rotation_threshold * 100

        # Determine rotation status based on utilization
        if utilization_pct >= force_threshold_pct:
            # Force rotation threshold exceeded
            status = RotationStatus.SHOULD_ROTATE
            reason = (
                f"Token usage {utilization_pct:.1f}% exceeds force rotation "
                f"threshold {force_threshold_pct:.1f}%"
            )
            should_rotate = True
            should_summarize = False

            if parsed_config.log_rotation_events:
                logger.warning(
                    f"[{session_id}] Force rotation triggered: "
                    f"{tokens_used}/{tokens_budget} tokens ({utilization_pct:.1f}%)"
                )

        elif utilization_pct >= early_threshold_pct:
            # Early rotation threshold exceeded - trigger summarization
            status = RotationStatus.SHOULD_SUMMARIZE
            reason = (
                f"Token usage {utilization_pct:.1f}% exceeds early rotation "
                f"threshold {early_threshold_pct:.1f}%"
            )
            should_rotate = False
            should_summarize = True

            if parsed_config.log_rotation_events:
                logger.info(
                    f"[{session_id}] Early rotation warning, should summarize: "
                    f"{tokens_used}/{tokens_budget} tokens ({utilization_pct:.1f}%)"
                )

        else:
            # Below thresholds, continue normal operation
            status = RotationStatus.CONTINUE
            reason = (
                f"Token usage {utilization_pct:.1f}% below rotation thresholds "
                f"(early: {early_threshold_pct:.1f}%, force: {force_threshold_pct:.1f}%)"
            )
            should_rotate = False
            should_summarize = False

            if parsed_config.log_rotation_events:
                logger.debug(
                    f"[{session_id}] Session healthy: "
                    f"{tokens_used}/{tokens_budget} tokens ({utilization_pct:.1f}%)"
                )

        return RotationCheckResult(
            status=status,
            reason=reason,
            utilization_pct=utilization_pct,
            tokens_used=tokens_used,
            tokens_budget=tokens_budget,
            circuit_state=circuit_state,
            should_rotate=should_rotate,
            should_summarize=should_summarize,
            metadata=metadata,
        )

    def get_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return self._default_config.copy()

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate rotation thresholds
        rotation = config.get("rotation", {})

        early_threshold = rotation.get("early_rotation_threshold", 0.60)
        force_threshold = rotation.get("force_rotation_threshold", 0.70)

        if not (0.0 <= early_threshold <= 1.0):
            msg = f"early_rotation_threshold must be between 0.0 and 1.0, got {early_threshold}"
            raise ValueError(msg)

        if not (0.0 <= force_threshold <= 1.0):
            msg = f"force_rotation_threshold must be between 0.0 and 1.0, got {force_threshold}"
            raise ValueError(msg)

        if early_threshold >= force_threshold:
            msg = (
                f"early_rotation_threshold ({early_threshold}) must be < "
                f"force_rotation_threshold ({force_threshold})"
            )
            raise ValueError(msg)

        # Validate poll interval
        poll_ms = rotation.get("operation_poll_ms", 100)
        if not isinstance(poll_ms, int) or poll_ms <= 0:
            msg = f"operation_poll_ms must be a positive integer, got {poll_ms}"
            raise ValueError(msg)

        # Validate circuit breaker settings
        circuit_breaker = config.get("circuit_breaker", {})

        failure_threshold = circuit_breaker.get("failure_threshold", 3)
        if not isinstance(failure_threshold, int) or failure_threshold <= 0:
            msg = f"failure_threshold must be a positive integer, got {failure_threshold}"
            raise ValueError(msg)

        recovery_timeout = circuit_breaker.get("recovery_timeout_seconds", 30)
        if not isinstance(recovery_timeout, (int, float)) or recovery_timeout <= 0:
            msg = f"recovery_timeout_seconds must be a positive number, got {recovery_timeout}"
            raise ValueError(msg)

        half_open_calls = circuit_breaker.get("half_open_max_calls", 1)
        if not isinstance(half_open_calls, int) or half_open_calls <= 0:
            msg = f"half_open_max_calls must be a positive integer, got {half_open_calls}"
            raise ValueError(msg)

        return True

    def _load_default_config(self) -> dict[str, Any]:
        """Load default configuration from config.yaml."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
                return config or {}

        # Return hardcoded defaults if config file missing
        return {
            "rotation": {
                "operation_poll_ms": 100,
                "status_log_interval_seconds": 5,
                "early_rotation_threshold": 0.60,
                "force_rotation_threshold": 0.70,
                "rotation_timeout_seconds": 30,
            },
            "circuit_breaker": {
                "failure_threshold": 3,
                "recovery_timeout_seconds": 30,
                "half_open_max_calls": 1,
            },
            "session_defaults": {
                "default_tokens_budget": 200000,
                "default_model_name": "claude-sonnet-4.5",
                "enable_generation_counter": True,
                "enable_operation_tracking": True,
            },
            "observability": {
                "log_rotation_events": True,
                "log_circuit_breaker_events": True,
                "emit_metrics": True,
                "enable_tracing": False,
            },
        }

    def _parse_config(self, config: dict[str, Any]) -> SessionRotationConfig:
        """
        Parse configuration with environment variable overrides.

        Environment variables take precedence over config file values:
        - SIBYL_SESSION_ROTATION_OPERATION_POLL_MS
        - SIBYL_SESSION_ROTATION_EARLY_ROTATION_THRESHOLD
        - SIBYL_SESSION_ROTATION_FORCE_ROTATION_THRESHOLD
        - SIBYL_SESSION_CIRCUIT_BREAKER_FAILURE_THRESHOLD
        - SIBYL_SESSION_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS

        Args:
            config: Configuration dictionary

        Returns:
            Parsed SessionRotationConfig
        """
        rotation = config.get("rotation", {})
        circuit_breaker = config.get("circuit_breaker", {})
        session_defaults = config.get("session_defaults", {})
        observability = config.get("observability", {})

        # Apply environment variable overrides if enabled
        env_overrides_enabled = config.get("env_overrides_enabled", True)

        if env_overrides_enabled:
            # Rotation overrides
            if "SIBYL_SESSION_ROTATION_OPERATION_POLL_MS" in os.environ:
                rotation["operation_poll_ms"] = int(
                    os.environ["SIBYL_SESSION_ROTATION_OPERATION_POLL_MS"]
                )

            if "SIBYL_SESSION_ROTATION_EARLY_ROTATION_THRESHOLD" in os.environ:
                rotation["early_rotation_threshold"] = float(
                    os.environ["SIBYL_SESSION_ROTATION_EARLY_ROTATION_THRESHOLD"]
                )

            if "SIBYL_SESSION_ROTATION_FORCE_ROTATION_THRESHOLD" in os.environ:
                rotation["force_rotation_threshold"] = float(
                    os.environ["SIBYL_SESSION_ROTATION_FORCE_ROTATION_THRESHOLD"]
                )

            # Circuit breaker overrides
            if "SIBYL_SESSION_CIRCUIT_BREAKER_FAILURE_THRESHOLD" in os.environ:
                circuit_breaker["failure_threshold"] = int(
                    os.environ["SIBYL_SESSION_CIRCUIT_BREAKER_FAILURE_THRESHOLD"]
                )

            if "SIBYL_SESSION_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS" in os.environ:
                circuit_breaker["recovery_timeout_seconds"] = int(
                    os.environ["SIBYL_SESSION_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS"]
                )

        return SessionRotationConfig(
            operation_poll_ms=rotation.get("operation_poll_ms", 100),
            status_log_interval_seconds=rotation.get("status_log_interval_seconds", 5),
            early_rotation_threshold=rotation.get("early_rotation_threshold", 0.60),
            force_rotation_threshold=rotation.get("force_rotation_threshold", 0.70),
            rotation_timeout_seconds=rotation.get("rotation_timeout_seconds", 30),
            failure_threshold=circuit_breaker.get("failure_threshold", 3),
            recovery_timeout_seconds=circuit_breaker.get("recovery_timeout_seconds", 30),
            half_open_max_calls=circuit_breaker.get("half_open_max_calls", 1),
            default_tokens_budget=session_defaults.get("default_tokens_budget", 200000),
            default_model_name=session_defaults.get("default_model_name", "claude-sonnet-4.5"),
            enable_generation_counter=session_defaults.get("enable_generation_counter", True),
            enable_operation_tracking=session_defaults.get("enable_operation_tracking", True),
            log_rotation_events=observability.get("log_rotation_events", True),
            log_circuit_breaker_events=observability.get("log_circuit_breaker_events", True),
            emit_metrics=observability.get("emit_metrics", True),
            enable_tracing=observability.get("enable_tracing", False),
        )

    def _validate_input(self, input_data: Any) -> None:
        """
        Validate input data structure.

        Args:
            input_data: Input data to validate

        Raises:
            ValueError: If input_data is invalid
        """
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        # tokens_used is required
        if "tokens_used" not in input_data:
            msg = "input_data must contain 'tokens_used'"
            raise ValueError(msg)

        tokens_used = input_data["tokens_used"]
        if not isinstance(tokens_used, int) or tokens_used < 0:
            msg = f"tokens_used must be a non-negative integer, got {tokens_used}"
            raise ValueError(msg)

        # tokens_budget is optional but must be valid if provided
        if "tokens_budget" in input_data:
            tokens_budget = input_data["tokens_budget"]
            if not isinstance(tokens_budget, int) or tokens_budget <= 0:
                msg = f"tokens_budget must be a positive integer, got {tokens_budget}"
                raise ValueError(msg)
