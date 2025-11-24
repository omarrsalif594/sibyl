"""Profile Configuration Validation

Validates routing, compression, and profile configurations.
Provides clear error messages for misconfiguration scenarios.

Features:
- Routing configuration validation
- Compression configuration validation
- Profile configuration validation
- Clear, actionable error messages
- Integration with existing validation system
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RoutingStrategy(str, Enum):
    """Supported routing strategies."""

    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    LEAST_LOAD = "least_load"
    FAILOVER = "failover"


class CompressionAlgorithm(str, Enum):
    """Supported compression algorithms."""

    GZIP = "gzip"
    BROTLI = "brotli"
    ZSTD = "zstd"
    NONE = "none"


@dataclass
class ValidationError:
    """Validation error with context."""

    code: str
    message: str
    hint: str
    context: dict[str, Any]
    field_path: str | None = None


@dataclass
class ValidationResult:
    """Result of validation."""

    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]


class RoutingConfigValidator:
    """Validates routing configuration."""

    @staticmethod
    def validate(config: dict[str, Any], context: dict[str, Any] | None = None) -> ValidationResult:
        """Validate routing configuration.

        Args:
            config: Routing configuration dict
            context: Optional context (workspace, provider names, etc.)

        Returns:
            ValidationResult with any errors/warnings
        """
        errors = []
        warnings = []
        ctx = context or {}

        # Check if routing is enabled
        if not config.get("enabled", False):
            # Routing disabled is valid, but note it
            warnings.append(
                ValidationError(
                    code="ROUTING_DISABLED",
                    message="Routing is disabled",
                    hint="Set 'enabled: true' to enable routing features",
                    context={"config": config},
                )
            )
            return ValidationResult(valid=True, errors=[], warnings=warnings)

        # Validate strategy
        strategy = config.get("strategy")
        if not strategy:
            errors.append(
                ValidationError(
                    code="ROUTING_MISSING_STRATEGY",
                    message="Routing strategy not specified",
                    hint="Add 'strategy' field with one of: round_robin, priority, least_load, failover",
                    context={"config": config},
                    field_path="routing.strategy",
                )
            )
        elif strategy not in [s.value for s in RoutingStrategy]:
            errors.append(
                ValidationError(
                    code="ROUTING_INVALID_STRATEGY",
                    message=f"Invalid routing strategy: {strategy}",
                    hint=f"Valid strategies are: {', '.join(s.value for s in RoutingStrategy)}",
                    context={
                        "strategy": strategy,
                        "valid_strategies": [s.value for s in RoutingStrategy],
                    },
                    field_path="routing.strategy",
                )
            )

        # Validate providers list
        providers = config.get("providers", [])
        if not providers:
            errors.append(
                ValidationError(
                    code="ROUTING_NO_PROVIDERS",
                    message="No providers specified for routing",
                    hint="Add 'providers' list with at least 2 provider names to route between",
                    context={"config": config},
                    field_path="routing.providers",
                )
            )
        elif len(providers) < 2:
            warnings.append(
                ValidationError(
                    code="ROUTING_SINGLE_PROVIDER",
                    message="Only 1 provider specified for routing",
                    hint="Routing requires at least 2 providers. Add more providers or disable routing.",
                    context={"providers": providers},
                    field_path="routing.providers",
                )
            )

        # Validate provider names exist in workspace
        if ctx.get("available_providers"):
            available = set(ctx["available_providers"])
            for provider in providers:
                if provider not in available:
                    errors.append(
                        ValidationError(
                            code="ROUTING_UNKNOWN_PROVIDER",
                            message=f"Routing provider not found in workspace: {provider}",
                            hint=f"Provider '{provider}' must be defined in workspace.providers. Available: {', '.join(sorted(available))}",
                            context={
                                "provider": provider,
                                "available_providers": sorted(available),
                            },
                            field_path=f"routing.providers[{providers.index(provider)}]",
                        )
                    )

        # Strategy-specific validation
        if strategy == RoutingStrategy.PRIORITY.value:
            priorities = config.get("priorities", {})
            if not priorities:
                errors.append(
                    ValidationError(
                        code="ROUTING_PRIORITY_NO_PRIORITIES",
                        message="Priority strategy requires 'priorities' mapping",
                        hint="Add 'priorities' dict mapping provider names to priority values (higher = higher priority)",
                        context={"strategy": strategy, "providers": providers},
                        field_path="routing.priorities",
                    )
                )
            else:
                # Check all providers have priorities
                for provider in providers:
                    if provider not in priorities:
                        warnings.append(
                            ValidationError(
                                code="ROUTING_PRIORITY_MISSING",
                                message=f"Provider '{provider}' has no priority set",
                                hint=f"Add priority for '{provider}' in routing.priorities (default will be 0)",
                                context={"provider": provider, "priorities": priorities},
                                field_path="routing.priorities",
                            )
                        )

        # Validate timeout
        timeout = config.get("timeout_s")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            errors.append(
                ValidationError(
                    code="ROUTING_INVALID_TIMEOUT",
                    message=f"Invalid routing timeout: {timeout}",
                    hint="Timeout must be a positive number (seconds)",
                    context={"timeout": timeout},
                    field_path="routing.timeout_s",
                )
            )

        # Validate fallback config
        fallback = config.get("fallback", {})
        if fallback and fallback.get("enabled") and not fallback.get("on_error"):
            warnings.append(
                ValidationError(
                    code="ROUTING_FALLBACK_NO_STRATEGY",
                    message="Fallback enabled but no error handling strategy specified",
                    hint="Add 'on_error' field with strategy: next_provider, all_providers, or fail",
                    context={"fallback": fallback},
                    field_path="routing.fallback",
                )
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


class CompressionConfigValidator:
    """Validates compression configuration."""

    @staticmethod
    def validate(config: dict[str, Any], context: dict[str, Any] | None = None) -> ValidationResult:
        """Validate compression configuration.

        Args:
            config: Compression configuration dict
            context: Optional context

        Returns:
            ValidationResult with any errors/warnings
        """
        errors = []
        warnings = []

        # Check if compression is enabled
        if not config.get("enabled", False):
            warnings.append(
                ValidationError(
                    code="COMPRESSION_DISABLED",
                    message="Compression is disabled",
                    hint="Set 'enabled: true' to enable response compression",
                    context={"config": config},
                )
            )
            return ValidationResult(valid=True, errors=[], warnings=warnings)

        # Validate algorithm
        algorithm = config.get("algorithm", "gzip")
        if algorithm not in [a.value for a in CompressionAlgorithm]:
            errors.append(
                ValidationError(
                    code="COMPRESSION_INVALID_ALGORITHM",
                    message=f"Invalid compression algorithm: {algorithm}",
                    hint=f"Valid algorithms are: {', '.join(a.value for a in CompressionAlgorithm)}",
                    context={
                        "algorithm": algorithm,
                        "valid_algorithms": [a.value for a in CompressionAlgorithm],
                    },
                    field_path="compression.algorithm",
                )
            )

        # Validate threshold
        threshold = config.get("threshold_bytes", 100 * 1024)  # Default 100KB
        if not isinstance(threshold, int) or threshold < 0:
            errors.append(
                ValidationError(
                    code="COMPRESSION_INVALID_THRESHOLD",
                    message=f"Invalid compression threshold: {threshold}",
                    hint="Threshold must be a non-negative integer (bytes). Typical: 100KB = 102400",
                    context={"threshold": threshold},
                    field_path="compression.threshold_bytes",
                )
            )
        elif threshold < 1024:
            warnings.append(
                ValidationError(
                    code="COMPRESSION_LOW_THRESHOLD",
                    message=f"Very low compression threshold: {threshold} bytes",
                    hint="Compressing small responses may hurt performance. Consider threshold >= 1KB",
                    context={"threshold": threshold},
                    field_path="compression.threshold_bytes",
                )
            )

        # Validate level (if specified)
        level = config.get("level")
        if level is not None:
            if not isinstance(level, int):
                errors.append(
                    ValidationError(
                        code="COMPRESSION_INVALID_LEVEL",
                        message=f"Invalid compression level: {level}",
                        hint="Compression level must be an integer. Range depends on algorithm (e.g., gzip: 1-9)",
                        context={"level": level, "algorithm": algorithm},
                        field_path="compression.level",
                    )
                )
            # Algorithm-specific level validation
            elif algorithm == CompressionAlgorithm.GZIP.value and (level < 1 or level > 9):
                errors.append(
                    ValidationError(
                        code="COMPRESSION_LEVEL_OUT_OF_RANGE",
                        message=f"Gzip compression level out of range: {level}",
                        hint="Gzip level must be 1-9 (1=fastest, 9=best compression)",
                        context={"level": level, "algorithm": algorithm, "valid_range": "1-9"},
                        field_path="compression.level",
                    )
                )
            elif algorithm == CompressionAlgorithm.BROTLI.value and (level < 0 or level > 11):
                errors.append(
                    ValidationError(
                        code="COMPRESSION_LEVEL_OUT_OF_RANGE",
                        message=f"Brotli compression level out of range: {level}",
                        hint="Brotli level must be 0-11 (0=fastest, 11=best compression)",
                        context={"level": level, "algorithm": algorithm, "valid_range": "0-11"},
                        field_path="compression.level",
                    )
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


class ProfileConfigValidator:
    """Validates profile configuration."""

    RESERVED_PROFILE_NAMES = {"default", "base", "system"}

    @staticmethod
    def validate(config: dict[str, Any], context: dict[str, Any] | None = None) -> ValidationResult:
        """Validate profile configuration.

        Args:
            config: Profile configuration dict
            context: Optional context (available profiles, etc.)

        Returns:
            ValidationResult with any errors/warnings
        """
        errors = []
        warnings = []
        ctx = context or {}

        # Validate profile name
        profile_name = config.get("name")
        if not profile_name:
            errors.append(
                ValidationError(
                    code="PROFILE_NO_NAME",
                    message="Profile has no name",
                    hint="Add 'name' field with a unique profile identifier",
                    context={"config": config},
                    field_path="profile.name",
                )
            )
        elif profile_name in ProfileConfigValidator.RESERVED_PROFILE_NAMES:
            errors.append(
                ValidationError(
                    code="PROFILE_RESERVED_NAME",
                    message=f"Profile name is reserved: {profile_name}",
                    hint=f"Cannot use reserved names: {', '.join(ProfileConfigValidator.RESERVED_PROFILE_NAMES)}",
                    context={
                        "name": profile_name,
                        "reserved_names": list(ProfileConfigValidator.RESERVED_PROFILE_NAMES),
                    },
                    field_path="profile.name",
                )
            )

        # Validate extends (inheritance)
        extends = config.get("extends")
        if extends:
            available_profiles = ctx.get("available_profiles", [])
            if available_profiles and extends not in available_profiles:
                errors.append(
                    ValidationError(
                        code="PROFILE_UNKNOWN_PARENT",
                        message=f"Profile extends unknown profile: {extends}",
                        hint=f"Parent profile '{extends}' must be defined. Available: {', '.join(available_profiles)}",
                        context={"extends": extends, "available_profiles": available_profiles},
                        field_path="profile.extends",
                    )
                )

            # Check for circular inheritance (simple check)
            if extends == profile_name:
                errors.append(
                    ValidationError(
                        code="PROFILE_CIRCULAR_INHERITANCE",
                        message=f"Profile cannot extend itself: {profile_name}",
                        hint="Remove 'extends' field or reference a different profile",
                        context={"name": profile_name},
                        field_path="profile.extends",
                    )
                )

        # Validate overrides
        overrides = config.get("overrides", {})
        if not overrides and not extends:
            warnings.append(
                ValidationError(
                    code="PROFILE_EMPTY",
                    message=f"Profile '{profile_name}' has no overrides and doesn't extend another profile",
                    hint="Add 'overrides' dict with configuration values or 'extends' to inherit from another profile",
                    context={"name": profile_name},
                )
            )

        # Validate routing override if present
        if "routing" in overrides:
            routing_result = RoutingConfigValidator.validate(overrides["routing"], context)
            errors.extend(routing_result.errors)
            warnings.extend(routing_result.warnings)

        # Validate compression override if present
        if "compression" in overrides:
            compression_result = CompressionConfigValidator.validate(
                overrides["compression"], context
            )
            errors.extend(compression_result.errors)
            warnings.extend(compression_result.warnings)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_profile_config(
    workspace_config: dict[str, Any], strict: bool = False
) -> ValidationResult:
    """Validate all profile configuration.

    Args:
        workspace_config: Complete workspace configuration
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult with all errors and warnings
    """
    all_errors = []
    all_warnings = []

    # Extract config sections
    routing_config = workspace_config.get("routing", {})
    compression_config = workspace_config.get("compression", {})
    profiles_config = workspace_config.get("profiles", {})

    # Build context for validation
    context = {
        "available_providers": list(workspace_config.get("providers", {}).get("mcp", {}).keys()),
        "available_profiles": list(profiles_config.keys()),
    }

    # Validate routing
    if routing_config:
        routing_result = RoutingConfigValidator.validate(routing_config, context)
        all_errors.extend(routing_result.errors)
        all_warnings.extend(routing_result.warnings)

    # Validate compression
    if compression_config:
        compression_result = CompressionConfigValidator.validate(compression_config, context)
        all_errors.extend(compression_result.errors)
        all_warnings.extend(compression_result.warnings)

    # Validate profiles
    for _profile_name, profile_config in profiles_config.items():
        profile_result = ProfileConfigValidator.validate(profile_config, context)
        all_errors.extend(profile_result.errors)
        all_warnings.extend(profile_result.warnings)

    # In strict mode, treat warnings as errors
    if strict:
        all_errors.extend(all_warnings)
        all_warnings = []

    return ValidationResult(valid=len(all_errors) == 0, errors=all_errors, warnings=all_warnings)


def format_validation_error(error: ValidationError) -> str:
    """Format validation error for display.

    Args:
        error: ValidationError to format

    Returns:
        Formatted error message
    """
    lines = [f"[{error.code}] {error.message}"]

    if error.hint:
        lines.append(f"Hint: {error.hint}")

    if error.field_path:
        lines.append(f"Field: {error.field_path}")

    if error.context:
        context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
        lines.append(f"Context: {context_str}")

    return "\n".join(lines)


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result for display.

    Args:
        result: ValidationResult to format

    Returns:
        Formatted result message
    """
    lines = []

    if result.valid:
        lines.append("✓ Configuration is valid")
    else:
        lines.append("✗ Configuration has errors")

    if result.errors:
        lines.append(f"\n{len(result.errors)} error(s):")
        for i, error in enumerate(result.errors, 1):
            lines.append(f"\nError {i}:")
            lines.append(format_validation_error(error))

    if result.warnings:
        lines.append(f"\n{len(result.warnings)} warning(s):")
        for i, warning in enumerate(result.warnings, 1):
            lines.append(f"\nWarning {i}:")
            lines.append(format_validation_error(warning))

    return "\n".join(lines)
