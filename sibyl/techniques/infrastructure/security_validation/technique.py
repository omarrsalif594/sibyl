"""
Security Validation Technique

Provides configurable security validation with multiple subtechniques:
- Input Validation (sanitization and checks)
- Secret Detection (API keys, tokens, credentials)
- Shape Validation (output conformance)

This technique eliminates hardcoded values from:
- security/validators/input.py:166 (max_length: 10000)
- security/secrets.py (min_entropy, min_length defaults)
"""

import logging
import os
from typing import Any

from sibyl.techniques.registry import BaseTechnique

logger = logging.getLogger(__name__)


class SecurityValidationTechnique(BaseTechnique):
    """
    Security validation technique with configurable parameters.

    Features:
    - Loads configuration from core config system
    - Supports multiple validation subtechniques
    - Environment variable overrides
    - Validation of configuration parameters

    Configuration Sources (in order of precedence):
    1. Environment variables: SIBYL_SECURITY_SECRETS_MIN_ENTROPY
    2. Core configuration: security.secrets.min_entropy
    3. Technique defaults: 3.0
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize security validation technique.

        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self.technique_id = "security_validation"

        # Load configuration from core config
        self._load_configuration()

        logger.info(
            f"Security validation technique initialized: "
            f"min_entropy={self.min_entropy}, "
            f"min_length={self.min_length}, "
            f"max_input_length={self.max_input_length}KB"
        )

    def _load_configuration(self) -> None:
        """Load security validation configuration from core config."""
        from sibyl.config.loader import load_core_config

        core_config = load_core_config()
        secrets_config = core_config.get("security", {}).get("secrets", {})
        input_validation_config = core_config.get("security", {}).get("input_validation", {})
        shape_validation_config = core_config.get("security", {}).get("shape_validation", {})

        # Load secret detection parameters with fallbacks
        self.min_entropy = self._get_param("min_entropy", secrets_config.get("min_entropy", 3.0))

        self.min_length = self._get_param("min_length", secrets_config.get("min_length", 16))

        self.enabled_detectors = self._get_param(
            "enabled_detectors",
            secrets_config.get("enabled_detectors", ["aws", "github", "generic_api_key"]),
        )

        # Load input validation parameters
        self.max_input_length = self._get_param(
            "max_input_length", input_validation_config.get("max_size_kb", 1024)
        )

        # Load shape validation parameters
        self.max_retry_attempts = self._get_param(
            "max_retry_attempts", shape_validation_config.get("max_retry_attempts", 3)
        )

        self.max_serialized_bytes = self._get_param(
            "max_serialized_bytes", shape_validation_config.get("max_serialized_bytes", 4000)
        )

        # Validate configuration
        self._validate_configuration()

    def _get_param(self, key: str, default: Any) -> Any:
        """
        Get parameter with environment variable override.

        Args:
            key: Parameter key
            default: Default value

        Returns:
            Parameter value from config, environment, or default
        """
        # Check config override first
        if key in self._config:
            return self._config[key]

        # Check environment variable
        env_key = f"SIBYL_SECURITY_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Parse environment value based on default type
            if isinstance(default, bool):
                return env_value.lower() in ("1", "true", "yes")
            if isinstance(default, int):
                return int(env_value)
            if isinstance(default, float):
                return float(env_value)
            if isinstance(default, list):
                return env_value.split(",")
            return env_value

        # Return default
        return default

    def _validate_configuration(self) -> None:
        """Validate security validation configuration."""
        if not (0.0 <= self.min_entropy <= 10.0):
            msg = f"min_entropy must be between 0.0 and 10.0, got {self.min_entropy}"
            raise ValueError(msg)

        if not (1 <= self.min_length <= 1000):
            msg = f"min_length must be between 1 and 1000, got {self.min_length}"
            raise ValueError(msg)

        if not (1 <= self.max_input_length <= 102400):
            msg = f"max_input_length must be between 1 and 102400 KB, got {self.max_input_length}"
            raise ValueError(msg)

        if not (1 <= self.max_retry_attempts <= 10):
            msg = f"max_retry_attempts must be between 1 and 10, got {self.max_retry_attempts}"
            raise ValueError(msg)

        if not isinstance(self.enabled_detectors, list):
            msg = f"enabled_detectors must be a list, got {type(self.enabled_detectors)}"
            raise TypeError(msg)

        if not (100 <= self.max_serialized_bytes <= 1000000):
            msg = (
                f"max_serialized_bytes must be between 100 and 1000000, "
                f"got {self.max_serialized_bytes}"
            )
            raise ValueError(msg)

    def execute(self, subtechnique: str = "input_validation", **kwargs) -> dict[str, Any]:
        """
        Execute security validation.

        Args:
            subtechnique: Validation subtechnique to use
            **kwargs: Additional parameters (text, input_data, etc.)

        Returns:
            Result dictionary with validation status
        """
        # Execute subtechnique
        if subtechnique == "input_validation":
            return self._execute_input_validation(**kwargs)
        if subtechnique == "secret_detection":
            return self._execute_secret_detection(**kwargs)
        if subtechnique == "shape_validation":
            return self._execute_shape_validation(**kwargs)
        msg = f"Unknown subtechnique: {subtechnique}"
        raise ValueError(msg)

    def _execute_input_validation(self, **kwargs) -> dict[str, Any]:
        """Execute input validation."""
        # Import here to avoid circular dependencies
        from sibyl.techniques.infrastructure.security_validation.subtechniques.input_validation.default.implementation import (
            execute_input_validation,
        )

        text = kwargs.pop("text", "")
        if not text:
            msg = "text is required for input validation"
            raise ValueError(msg)

        return execute_input_validation(
            text=text,
            max_length=self.max_input_length * 1024,  # Convert KB to bytes
            **kwargs,
        )

    def _execute_secret_detection(self, **kwargs) -> dict[str, Any]:
        """Execute secret detection."""
        text = kwargs.get("text", "")
        if not text:
            msg = "text is required for secret detection"
            raise ValueError(msg)

        # Use SecretsDetector with configuration
        from sibyl.core.infrastructure.security.secrets import SecretsDetector

        detector = SecretsDetector()
        findings = detector.detect(text)

        # Filter by entropy and length
        filtered_findings = []
        for pattern, matched_text, start, end in findings:
            # Check if detector is enabled
            detector_name = pattern.name.split("_")[0]  # e.g., "aws" from "aws_access_key"
            if detector_name not in self.enabled_detectors and "generic" not in pattern.name:
                continue

            # Apply entropy and length filters for generic patterns
            if "generic" in pattern.name:
                import math
                from collections import Counter

                # Calculate entropy
                counter = Counter(matched_text)
                total = len(matched_text)
                entropy = -sum(
                    (count / total) * math.log2(count / total) for count in counter.values()
                )

                if entropy < self.min_entropy or len(matched_text) < self.min_length:
                    continue

            filtered_findings.append(
                {
                    "pattern": pattern.name,
                    "text": matched_text,
                    "start": start,
                    "end": end,
                    "confidence": pattern.confidence,
                }
            )

        return {
            "has_secrets": len(filtered_findings) > 0,
            "findings": filtered_findings,
            "count": len(filtered_findings),
            "min_entropy": self.min_entropy,
            "min_length": self.min_length,
        }

    def _execute_shape_validation(self, **kwargs) -> dict[str, Any]:
        """Execute shape validation."""
        msg = "Shape validation not yet implemented"
        raise NotImplementedError(msg)

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "technique_id": self.technique_id,
            "min_entropy": self.min_entropy,
            "min_length": self.min_length,
            "enabled_detectors": self.enabled_detectors,
            "max_input_length": self.max_input_length,
            "max_retry_attempts": self.max_retry_attempts,
            "max_serialized_bytes": self.max_serialized_bytes,
        }
