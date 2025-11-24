"""
Rate Limiting Technique

Provides configurable rate limiting with multiple algorithms:
- Sliding Window (default)
- Fixed Window
- Token Bucket

This technique eliminates hardcoded values from security/rate_limiter.py:40-41
"""

import logging
from typing import Any

from sibyl.techniques.registry import BaseTechnique

logger = logging.getLogger(__name__)


class RateLimitingTechnique(BaseTechnique):
    """
    Rate limiting technique with configurable algorithms.

    Features:
    - Loads configuration from core config system
    - Supports multiple rate limiting algorithms
    - Environment variable overrides
    - Validation of configuration parameters

    Configuration Sources (in order of precedence):
    1. Environment variables: SIBYL_SECURITY_RATE_LIMITER_DEFAULT_RPM
    2. Core configuration: security.rate_limiter.default_rpm
    3. Technique defaults: 100 requests/minute
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize rate limiting technique.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.technique_id = "rate_limiting"

        # Load configuration from core config
        self._load_configuration()

        logger.info(
            f"Rate limiting technique initialized: "
            f"default_rpm={self.default_rpm}, "
            f"window={self.window_seconds}s"
        )

    def _load_configuration(self) -> None:
        """Load rate limiting configuration from core config."""
        import os  # can be moved to top

        from sibyl.config.loader import load_core_config

        core_config = load_core_config()
        rate_limiter_config = core_config.get("security", {}).get("rate_limiter", {})

        # Load parameters with fallbacks (env vars take precedence)
        self.default_rpm = int(
            os.environ.get(
                "SIBYL_SECURITY_RATE_LIMITER_DEFAULT_RPM",
                rate_limiter_config.get("default_rpm", 100),
            )
        )

        self.window_seconds = int(
            os.environ.get(
                "SIBYL_SECURITY_RATE_LIMITER_WINDOW_SECONDS",
                rate_limiter_config.get("window_seconds", 60),
            )
        )

        self.cleanup_interval_seconds = int(
            os.environ.get(
                "SIBYL_SECURITY_RATE_LIMITER_CLEANUP_INTERVAL_SECONDS",
                rate_limiter_config.get("cleanup_interval_seconds", 300),
            )
        )

        # Exempt IPs can't easily come from env, so just use config
        self.exempt_ips = rate_limiter_config.get("exempt_ips", ["localhost", "127.0.0.1", "::1"])

        # Validate configuration
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate rate limiting configuration."""
        if not (1 <= self.default_rpm <= 10000):
            msg = f"default_rpm must be between 1 and 10000, got {self.default_rpm}"
            raise ValueError(msg)

        if not (1 <= self.window_seconds <= 3600):
            msg = f"window_seconds must be between 1 and 3600, got {self.window_seconds}"
            raise ValueError(msg)

        if not (60 <= self.cleanup_interval_seconds <= 86400):
            msg = (
                f"cleanup_interval_seconds must be between 60 and 86400, "
                f"got {self.cleanup_interval_seconds}"
            )
            raise ValueError(msg)

        if not isinstance(self.exempt_ips, list):
            msg = f"exempt_ips must be a list, got {type(self.exempt_ips)}"
            raise TypeError(msg)

    def execute(self, subtechnique: str = "sliding_window", **kwargs) -> dict[str, Any]:
        """
        Execute rate limiting check.

        Args:
            subtechnique: Rate limiting algorithm to use
            **kwargs: Additional parameters (client_ip, endpoint, etc.)

        Returns:
            Result dictionary with rate limit status
        """
        client_ip = kwargs.get("client_ip")
        endpoint = kwargs.get("endpoint", "/")

        if not client_ip:
            msg = "client_ip is required for rate limiting"
            raise ValueError(msg)

        # Check if IP is exempt
        if client_ip in self.exempt_ips:
            return {
                "allowed": True,
                "reason": "exempt_ip",
                "limit": self.default_rpm,
                "remaining": self.default_rpm,
            }

        # Execute subtechnique
        if subtechnique == "sliding_window":
            return self._execute_sliding_window(client_ip, endpoint, **kwargs)
        if subtechnique == "fixed_window":
            return self._execute_fixed_window(client_ip, endpoint, **kwargs)
        if subtechnique == "token_bucket":
            return self._execute_token_bucket(client_ip, endpoint, **kwargs)
        msg = f"Unknown subtechnique: {subtechnique}"
        raise ValueError(msg)

    def _execute_sliding_window(self, client_ip: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Execute sliding window rate limiting."""
        # Import here to avoid circular dependencies
        from sibyl.techniques.infrastructure.rate_limiting.subtechniques.sliding_window.default.implementation import (
            execute_sliding_window,
        )

        return execute_sliding_window(
            client_ip=client_ip,
            endpoint=endpoint,
            default_rpm=self.default_rpm,
            window_seconds=self.window_seconds,
            **kwargs,
        )

    def _execute_fixed_window(self, client_ip: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Execute fixed window rate limiting."""
        msg = "Fixed window rate limiting not yet implemented"
        raise NotImplementedError(msg)

    def _execute_token_bucket(self, client_ip: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Execute token bucket rate limiting."""
        msg = "Token bucket rate limiting not yet implemented"
        raise NotImplementedError(msg)

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "technique_id": self.technique_id,
            "default_rpm": self.default_rpm,
            "window_seconds": self.window_seconds,
            "cleanup_interval_seconds": self.cleanup_interval_seconds,
            "exempt_ips": self.exempt_ips,
        }
