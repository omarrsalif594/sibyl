"""
Voting Technique Orchestrator

Provides voting algorithms and threshold-based consensus mechanisms.
Eliminates hardcoded voting parameters from consensus/protocol.py.

Key Features:
- Threshold voting with configurable k-voting
- Confidence-weighted voting
- Adaptive voting (dynamic parameter adjustment)
- Integration with core configuration system
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.config import get_consensus_config

logger = logging.getLogger(__name__)


class VotingTechnique:
    """
    Voting technique orchestrator.

    Provides multiple voting strategies:
    - threshold_voting: k-voting with configurable thresholds
    - confidence_voting: Weight votes by confidence scores
    - adaptive_voting: Dynamically adjust parameters
    """

    def __init__(self, config_path: Path | None = None, use_core_config: bool = True) -> None:
        """
        Initialize voting technique.

        Args:
            config_path: Optional path to technique-specific config
            use_core_config: If True, load defaults from core config (recommended)
        """
        self._name = "voting"
        self._description = "Voting algorithms and threshold-based consensus"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._use_core_config = use_core_config
        self._subtechniques: dict[str, Any] = {}

        # Load configuration
        self._technique_config = self._load_technique_config()
        self._voting_config = self._load_voting_config()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def subtechniques(self) -> dict[str, Any]:
        return self._subtechniques

    def _load_technique_config(self) -> dict[str, Any]:
        """Load technique-specific configuration."""
        if not self._config_path.exists():
            return {}

        with open(self._config_path) as f:
            return yaml.safe_load(f)

    def _load_voting_config(self) -> dict[str, Any]:
        """
        Load voting configuration with cascading precedence:
        1. Core config (if use_core_config=True)
        2. Technique config
        3. Subtechnique config
        """
        config = {}

        # Load from core config first (lowest priority for overrides)
        if self._use_core_config:
            try:
                core_config = get_consensus_config()
                config.update(
                    {
                        "initial_n": core_config.get("initial_n", 3),
                        "max_n": core_config.get("max_n", 5),
                        "k_threshold": core_config.get("k_threshold", 3),
                        "min_k_fallback": core_config.get("min_k_fallback", 2),
                        "timeout_seconds": core_config.get("timeout_seconds", 10.0),
                        "per_agent_timeout": core_config.get("per_agent_timeout", 5.0),
                        "min_avg_confidence": core_config.get("min_avg_confidence", 0.6),
                        "red_flag_escalation_threshold": core_config.get(
                            "red_flag_escalation_threshold", 0.3
                        ),
                        "cost_ceiling_cents": core_config.get("cost_ceiling_cents", 2.0),
                        "enable_early_commit": core_config.get("enable_early_commit", True),
                        "split_vote_threshold": core_config.get("split_vote_threshold", 0.4),
                    }
                )
            except Exception:
                # Fallback to technique config if core config unavailable
                logger.debug("Core config unavailable, using technique config")

        # Override with technique config (medium priority)
        threshold_voting = self._technique_config.get("threshold_voting", {})
        voting_policy = threshold_voting.get("voting_policy", {})
        if voting_policy:
            config.update(voting_policy)

        # Split detection config
        split_detection = threshold_voting.get("split_detection", {})
        if split_detection:
            config["split_vote_threshold"] = split_detection.get(
                "threshold", config.get("split_vote_threshold", 0.4)
            )

        return config

    def get_voting_policy(self) -> dict[str, Any]:
        """
        Get current voting policy configuration.

        Returns:
            Dictionary with all voting parameters
        """
        return self._voting_config.copy()

    def execute(
        self, subtechnique: str = "threshold_voting", implementation: str = "default", **kwargs
    ) -> dict[str, Any]:
        """
        Execute voting algorithm.

        Args:
            subtechnique: Voting subtechnique to use
            implementation: Specific implementation
            **kwargs: Additional parameters

        Returns:
            Voting result with decision and metadata
        """
        # Get configuration for this execution
        config = self.get_voting_policy()
        config.update(kwargs)

        # Execute the appropriate subtechnique
        if subtechnique == "threshold_voting":
            return self._execute_threshold_voting(config)
        if subtechnique == "confidence_voting":
            return self._execute_confidence_voting(config)
        if subtechnique == "adaptive_voting":
            return self._execute_adaptive_voting(config)
        msg = f"Unknown voting subtechnique: {subtechnique}"
        raise ValueError(msg)

    def _execute_threshold_voting(self, config: dict[str, Any]) -> dict[str, Any]:
        """Execute k-voting with thresholds."""
        return {
            "subtechnique": "threshold_voting",
            "config": config,
            "initial_n": config["initial_n"],
            "max_n": config["max_n"],
            "k_threshold": config["k_threshold"],
            "status": "ready",
        }

    def _execute_confidence_voting(self, config: dict[str, Any]) -> dict[str, Any]:
        """Execute confidence-weighted voting."""
        confidence_config = self._technique_config.get("confidence_voting", {})
        weighting = confidence_config.get("weighting", {})

        return {
            "subtechnique": "confidence_voting",
            "config": config,
            "weighting_method": weighting.get("method", "linear"),
            "status": "ready",
        }

    def _execute_adaptive_voting(self, config: dict[str, Any]) -> dict[str, Any]:
        """Execute adaptive voting with dynamic parameters."""
        adaptive_config = self._technique_config.get("adaptive_voting", {})
        adaptation = adaptive_config.get("adaptation", {})

        return {
            "subtechnique": "adaptive_voting",
            "config": config,
            "dynamic_n_enabled": adaptation.get("enable_dynamic_n", True),
            "dynamic_k_enabled": adaptation.get("enable_dynamic_k", True),
            "status": "ready",
        }

    def validate_config(self) -> bool:
        """
        Validate current voting configuration.

        Returns:
            True if valid, False otherwise
        """
        config = self._voting_config

        # Validate required fields
        required = ["initial_n", "max_n", "k_threshold", "timeout_seconds"]
        for field in required:
            if field not in config:
                return False

        # Validate ranges
        if config["initial_n"] < 1 or config["initial_n"] > config["max_n"]:
            return False

        if config["k_threshold"] < 1 or config["k_threshold"] > config["max_n"]:
            return False

        if config["timeout_seconds"] <= 0:
            return False

        # Validate confidence thresholds
        return 0.0 <= config.get("min_avg_confidence", 0.6) <= 1.0

    def get_subtechnique_config(self, subtechnique: str) -> dict[str, Any]:
        """Get configuration for a specific subtechnique."""
        return self._technique_config.get(subtechnique, {})

    def __repr__(self) -> str:
        return f"VotingTechnique(subtechniques={list(self._technique_config.keys())})"
