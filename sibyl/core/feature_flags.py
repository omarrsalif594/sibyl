"""
Technique feature flags and rollout controls.

This module provides a minimal, test-friendly feature flag system that can
toggle techniques at runtime and support percentage rollouts for gradual
deployments. It is intentionally lightweight so it can be used in unit and
integration tests without external dependencies.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class TechniqueChoice:
    """Result of a technique selection."""

    technique: str
    rollout_bucket: int | None = None
    enabled: bool = True


class FeatureFlags:
    """
    Runtime toggles for techniques with percentage rollouts.

    Flags are stored at the class level to keep them process-wide and easy to
    reset in tests. Access is guarded with a lock to avoid races when tests
    toggle values concurrently.
    """

    # Technique enablement
    TECHNIQUES_ENABLED: dict[str, bool] = {"consensus": True, "quorum": True}

    # Percentage rollouts (0.0 - 1.0)
    TECHNIQUE_ROLLOUT_PERCENTAGE: dict[str, float] = {"consensus": 1.0}

    _lock = threading.Lock()

    @classmethod
    def reset(cls) -> None:
        """Reset all flags to defaults (used by tests)."""
        with cls._lock:
            cls.TECHNIQUES_ENABLED = {"consensus": True, "quorum": True}
            cls.TECHNIQUE_ROLLOUT_PERCENTAGE = {"consensus": 1.0}

    @classmethod
    def is_technique_enabled(cls, technique: str, user_id: int | None = None) -> bool:
        """
        Determine if a technique is enabled for a given user.

        Percentage rollouts are deterministic based on user_id so tests remain
        stable. If user_id is None, the rollout gate is skipped.
        """
        with cls._lock:
            return cls._is_enabled_locked(technique, user_id)

    @classmethod
    def choose_technique(cls, user_id: int | None = None) -> TechniqueChoice:
        """
        Decide which technique to use given current flags.

        Prefers consensus when enabled for the user; otherwise falls back to
        quorum. If both are disabled, returns the first enabled technique or
        marks as disabled.
        """
        with cls._lock:
            rollout_bucket = cls._user_bucket(user_id) if user_id is not None else None

            consensus_enabled = cls._is_enabled_locked("consensus", user_id=user_id)
            if consensus_enabled:
                return TechniqueChoice("consensus", rollout_bucket, enabled=True)

            if cls.TECHNIQUES_ENABLED.get("quorum", False):
                return TechniqueChoice("quorum", rollout_bucket, enabled=True)

            # Nothing enabled
            return TechniqueChoice("consensus", rollout_bucket, enabled=False)

    @classmethod
    def _user_bucket(cls, user_id: int) -> int:
        """Map user_id deterministically into a 0-99 bucket space."""
        return abs(hash(str(user_id))) % 100

    @classmethod
    def _is_enabled_locked(cls, technique: str, user_id: int | None = None) -> bool:
        """Internal helper that assumes caller already holds the lock."""
        if not cls.TECHNIQUES_ENABLED.get(technique, False):
            return False

        rollout = cls.TECHNIQUE_ROLLOUT_PERCENTAGE.get(technique, 1.0)
        if rollout >= 1.0 or user_id is None:
            return True

        bucket = cls._user_bucket(user_id)
        return bucket < int(rollout * 100)
