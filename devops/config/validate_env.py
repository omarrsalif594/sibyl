"""Environment validation script for startup checks.

This script validates that all required environment variables and secrets
are properly configured before the MCP server starts.

It provides two modes:
- Strict mode: Fails on any unknown environment variables
- Permissive mode: Warns on unknown environment variables

Usage:
    # Strict mode (fail on unknown vars)
    python validate_env.py --strict

    # Permissive mode (warn only)
    python validate_env.py

    # Check specific environment
    python validate_env.py --env production --strict

Exit codes:
    0: All validations passed
    1: Validation failed (missing required vars, invalid values, or unknown vars in strict mode)
    2: Warnings present (unknown vars in permissive mode, but not fatal)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Any

from infrastructure.security.secrets_manager import get_secrets_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Required environment variables/secrets by deployment environment
REQUIRED_VARS = {
    "development": [
        ("MCP_HTTP_PORT", "8770", "HTTP server port"),
        ("MCP_LOG_LEVEL", "INFO", "Logging level"),
    ],
    "staging": [
        ("MCP_HTTP_PORT", None, "HTTP server port"),
        ("MCP_LOG_LEVEL", "INFO", "Logging level"),
        ("MCP_API_KEYS", None, "API keys for authentication (REQUIRED, no default)"),
        ("DUCKDB_MEMORY_LIMIT", "2GB", "DuckDB memory limit"),
    ],
    "production": [
        # S104: 0.0.0.0 is intentional for production (binds all interfaces)
        # Security: Ensure firewall rules and authentication are configured
        ("MCP_HTTP_HOST", "0.0.0.0", "HTTP server host"),
        ("MCP_HTTP_PORT", None, "HTTP server port"),
        ("MCP_LOG_LEVEL", "WARNING", "Logging level"),
        ("MCP_API_KEYS", None, "API keys for authentication (REQUIRED, no default)"),
        ("MCP_JSON_LOGS", "true", "Enable JSON logging"),
        ("DUCKDB_MEMORY_LIMIT", "2GB", "DuckDB memory limit"),
        ("DUCKDB_CACHE_DIR", "/var/cache/mcp/duckdb", "DuckDB cache directory"),
        ("GRAFANA_PASSWORD", None, "Grafana admin password (REQUIRED, no default)"),
    ],
}

# Known optional environment variables
OPTIONAL_VARS = [
    "SIBYL_WORKSPACE_ROOT",
    "SIBYL_DB_PATH",
    "SIBYL_DEBUG",
    "MCP_LAYOUT",
    "MCP_ROTATION_ENABLED",
    "MCP_ROTATION_SUMMARIZE_PCT",
    "MCP_ROTATION_ROTATE_PCT",
    "MCP_ROTATION_STRATEGY",
    "MCP_DUCKDB_PATH",
    "QUORUM_BUDGET_USD",
    "QUORUM_TRACE_DIR",
    "TRACE_RETENTION_DAYS",
    "MCP_QC_ENABLED",
    "MCP_QC_MAX_RETRIES",
    "MCP_METRICS_ENABLED",
    "MCP_LOG_FILE",
    "GRAFANA_PASSWORD",
    "GRAFANA_USER",
]

# Environment variable naming conventions
ENV_PREFIXES = ["MCP_", "DUCKDB_", "USE_", "QUORUM_", "TRACE_", "SIBYL_", "GRAFANA_"]


class ValidationError(Exception):
    """Validation error."""


def validate_env_value(key: str, value: str, env: str) -> list[str]:
    """Validate environment variable value.

    Args:
        key: Environment variable name
        value: Environment variable value
        env: Deployment environment (development/staging/production)

    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []

    # Type-specific validation
    if "PORT" in key:
        try:
            port = int(value)
            if not (1 <= port <= 65535):  # noqa: PLR2004
                warnings.append(f"{key}={value} is not a valid port (must be 1-65535)")
        except ValueError:
            warnings.append(f"{key}={value} is not a valid integer")

    if "LOG_LEVEL" in key:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() not in valid_levels:
            warnings.append(
                f"{key}={value} is not a valid log level (must be one of {valid_levels})"
            )

    if "MEMORY_LIMIT" in key and value[-2:] not in ["GB", "MB", "KB"]:
        warnings.append(f"{key}={value} should end with GB, MB, or KB")

    if "ENABLED" in key or key.endswith("_JSON_LOGS"):
        if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
            warnings.append(f"{key}={value} should be a boolean (true/false)")

    # Security checks
    if "API_KEY" in key or "SECRET" in key or "PASSWORD" in key or "TOKEN" in key:
        if len(value) < 16:  # noqa: PLR2004
            warnings.append(f"{key} is too short (should be at least 16 characters)")
        if value in ["test", "dev", "changeme", "password", "secret"]:
            warnings.append(f"⚠️  SECURITY: {key} uses an insecure default value!")

    # Production-specific checks
    if env == "production":
        if key == "MCP_HTTP_HOST" and value == "127.0.0.1":
            warnings.append(f"{key}=127.0.0.1 in production will only accept localhost connections")

        if key == "MCP_LOG_LEVEL" and value in ["DEBUG", "TRACE"]:
            warnings.append(
                f"{key}={value} in production may impact performance and leak sensitive data"
            )

    return warnings


def check_required_vars(env: str, secrets_manager: Any) -> tuple[bool, list[str]]:
    """Check that all required variables are present.

    Args:
        env: Deployment environment
        secrets_manager: SecretsManager instance

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []
    required_vars = REQUIRED_VARS.get(env, REQUIRED_VARS["development"])

    for var_name, default_value, description in required_vars:
        value = secrets_manager.get(var_name, default=default_value)

        if value is None:
            errors.append(
                f"❌ REQUIRED: {var_name} is not set\n"
                f"   Description: {description}\n"
                f"   Set via: environment variable, Docker secret, or .mcp_keys file"
            )
        else:
            # Validate the value
            warnings = validate_env_value(var_name, value, env)
            if warnings:
                for warning in warnings:
                    logger.warning("⚠️  %s", warning)

            # Show what was used (without revealing the value)
            if var_name in os.environ:
                logger.info("✓ %s: loaded from environment variable", var_name)
            elif Path(f"/run/secrets/{var_name}").exists():
                logger.info("✓ %s: loaded from Docker secret", var_name)
            else:
                logger.info("✓ %s: using default value", var_name)

    return len(errors) == 0, errors


def check_unknown_vars(strict: bool) -> tuple[bool, list[str]]:
    """Check for unknown environment variables.

    Args:
        strict: If True, fail on unknown vars; if False, warn only

    Returns:
        Tuple of (success: bool, warnings: list[str])
    """
    warnings = []
    all_known_vars = set()

    # Collect all known vars
    for env_vars in REQUIRED_VARS.values():
        for var_name, _, _ in env_vars:
            all_known_vars.add(var_name)
    all_known_vars.update(OPTIONAL_VARS)

    # Check for unknown MCP_* vars
    unknown_vars = []
    for key in os.environ:
        # Only check variables with our prefixes
        if any(key.startswith(prefix) for prefix in ENV_PREFIXES):
            if key not in all_known_vars and not key.endswith("_FILE"):
                unknown_vars.append(key)

    if unknown_vars:
        msg = (
            f"Unknown environment variables found: {', '.join(unknown_vars)}\n"
            f"   This may be a typo or outdated configuration.\n"
            f"   Known variables: {', '.join(sorted(all_known_vars))}"
        )
        warnings.append(msg)

        if strict:
            logger.error("❌ %s", msg)
            return False, warnings
        logger.warning("⚠️  %s", msg)
        return True, warnings

    return True, []


def check_file_permissions(env: str) -> tuple[bool, list[str]]:
    """Check file and directory permissions.

    Args:
        env: Deployment environment

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []

    # Check DuckDB directory
    import tempfile  # noqa: PLC0415

    default_db = Path(tempfile.gettempdir()) / "sibyl_state.duckdb"
    duckdb_path = os.getenv("MCP_DUCKDB_PATH", str(default_db))
    duckdb_dir = Path(duckdb_path).parent

    if not duckdb_dir.exists():
        try:
            duckdb_dir.mkdir(parents=True, exist_ok=True)
            logger.info("✓ Created DuckDB directory: %s", duckdb_dir)
        except Exception as e:
            errors.append(f"❌ Cannot create DuckDB directory {duckdb_dir}: {e}")
    elif not os.access(duckdb_dir, os.W_OK):
        errors.append(f"❌ DuckDB directory {duckdb_dir} is not writable")

    # Check log directory
    default_log = Path(tempfile.gettempdir()) / "sibyl_mcp.log"
    log_file = os.getenv("MCP_LOG_FILE", str(default_log))
    log_dir = Path(log_file).parent

    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.info("✓ Created log directory: %s", log_dir)
        except Exception as e:
            errors.append(f"❌ Cannot create log directory {log_dir}: {e}")
    elif not os.access(log_dir, os.W_OK):
        errors.append(f"❌ Log directory {log_dir} is not writable")

    # Check cache directory (if specified)
    cache_dir_str = os.getenv("DUCKDB_CACHE_DIR")
    if cache_dir_str:
        cache_dir = Path(cache_dir_str)
        if not cache_dir.exists():
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info("✓ Created cache directory: %s", cache_dir)
            except Exception as e:
                errors.append(f"❌ Cannot create cache directory {cache_dir}: {e}")

    return len(errors) == 0, errors


def check_security_config(env: str, secrets_manager: Any) -> tuple[bool, list[str]]:
    """Check security configuration.

    Args:
        env: Deployment environment
        secrets_manager: SecretsManager instance

    Returns:
        Tuple of (success: bool, warnings: list[str])
    """
    warnings = []

    # Check API keys in staging/production
    if env in ["staging", "production"]:
        api_keys = secrets_manager.get_api_keys("MCP_API_KEYS")
        if not api_keys:
            warnings.append("❌ SECURITY: No API keys configured in staging/production!")
        elif len(api_keys) == 1 and len(api_keys[0]) < 32:  # noqa: PLR2004
            warnings.append("⚠️  SECURITY: API key is too short (should be at least 32 characters)")

        # Check if using insecure mode (file fallback)
        if not secrets_manager.is_secure_mode():
            warnings.append(
                f"⚠️  SECURITY: Running in {env} without Docker Secrets. "
                "Secrets are loaded from environment variables or files."
            )

    # Check Docker secrets in production
    if env == "production" and not secrets_manager.is_secure_mode():
        warnings.append(
            "⚠️  SECURITY RECOMMENDATION: Use Docker Secrets in production for better secret management."
        )

    return len(warnings) == 0, warnings


def validate_environment(
    env: str = "development",
    strict: bool = False,
    allow_file_fallback: bool | None = None,
) -> int:
    """Validate environment configuration.

    Args:
        env: Deployment environment (development/staging/production)
        strict: If True, fail on unknown environment variables
        allow_file_fallback: Allow file-based secrets (auto-detect if None)

    Returns:
        Exit code (0=success, 1=error, 2=warnings)
    """
    logger.info("🔍 Validating %s environment configuration...", env)
    logger.info("   Strict mode: %s", "ENABLED" if strict else "DISABLED")

    # Initialize secrets manager
    if allow_file_fallback is None:
        allow_file_fallback = env == "development"

    try:
        secrets_manager = get_secrets_manager(allow_file_fallback=allow_file_fallback)
        logger.info("   Secrets manager: %s", [p.name for p in secrets_manager.providers])
    except Exception as e:
        logger.exception("❌ Failed to initialize secrets manager: %s", e)
        return 1

    # Run validation checks
    all_success = True
    has_warnings = False

    # 1. Check required variables
    logger.info("\n1️⃣  Checking required variables...")
    success, errors = check_required_vars(env, secrets_manager)
    if not success:
        all_success = False
        for error in errors:
            logger.error(error)

    # 2. Check unknown variables
    logger.info("\n2️⃣  Checking for unknown variables...")
    success, warnings = check_unknown_vars(strict)
    if not success:
        all_success = False
    if warnings:
        has_warnings = True

    # 3. Check file permissions
    logger.info("\n3️⃣  Checking file permissions...")
    success, errors = check_file_permissions(env)
    if not success:
        all_success = False
        for error in errors:
            logger.error(error)

    # 4. Check security configuration
    logger.info("\n4️⃣  Checking security configuration...")
    success, warnings = check_security_config(env, secrets_manager)
    if warnings:
        has_warnings = True
        for warning in warnings:
            logger.warning(warning)

    # Summary
    logger.info("\n" + "=" * 60)
    if all_success and not has_warnings:
        logger.info("✅ All validation checks passed!")
        return 0
    if all_success and has_warnings:
        logger.warning("⚠️  Validation passed with warnings")
        return 2
    logger.error("❌ Validation FAILED")
    logger.error("   Fix the errors above before starting the server")
    return 1


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate MCP server environment configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="Deployment environment (default: development)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail on unknown environment variables",
    )
    parser.add_argument(
        "--allow-file-fallback",
        type=lambda x: x.lower() in ["true", "1", "yes"],
        default=None,
        help="Allow file-based secrets fallback (auto-detect if not specified)",
    )

    args = parser.parse_args()

    exit_code = validate_environment(
        env=args.env,
        strict=args.strict,
        allow_file_fallback=args.allow_file_fallback,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
