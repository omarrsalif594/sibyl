"""
Consensus Technique Orchestrator

Multi-agent consensus and voting mechanisms for high-stakes decision-making.

Provides multiple consensus strategies:
- quorum_voting: Multi-agent k-voting with fallbacks (five_agent, three_agent, single_agent)
- weighted_voting: Weight votes by confidence/role (confidence_weighted, role_weighted)
- hybrid_consensus: Mix of voting and heuristics (voting_heuristic_mix)
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseTechnique


class ConsensusTechnique(BaseTechnique):
    """
    Consensus decision-making technique orchestrator.

    Provides multiple consensus strategies for high-stakes decisions:
    - quorum_voting: Multi-agent k-voting with fallbacks
    - weighted_voting: Weight votes by confidence/role
    - hybrid_consensus: Mix of voting and heuristics
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "consensus"
        self._description = "Multi-agent consensus and voting mechanisms"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, Any] = {}
        self._default_config = self._load_technique_config()
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def subtechniques(self) -> dict[str, Any]:
        return self._subtechniques

    def register_subtechnique(self, subtechnique: Any, implementation: str) -> None:
        """
        Register a subtechnique implementation.

        Args:
            subtechnique: Subtechnique instance
            implementation: Implementation name (e.g., "five_agent", "three_agent")
        """
        key = f"{subtechnique.name}:{implementation}"
        self._subtechniques[key] = subtechnique

    def execute(
        self,
        input_data: Any,
        subtechnique: str = "quorum_voting",
        implementation: str = "five_agent",
        config: dict | None = None,
        **kwargs,
    ) -> Any:
        """
        Execute consensus technique.

        Args:
            input_data: Input data (error, context, code, etc.)
            subtechnique: Subtechnique name (quorum_voting, weighted_voting, hybrid_consensus)
            implementation: Implementation name (five_agent, three_agent, single_agent, etc.)
            config: Optional config override
            **kwargs: Additional arguments (global_config, etc.)

        Returns:
            Consensus decision result

        Raises:
            ValueError: If subtechnique:implementation not found or config invalid
        """
        # Build configuration cascade
        cascade = ConfigCascade()
        merged_config = cascade.merge(
            global_config=kwargs.get("global_config", {}),
            technique_config=self._default_config,
            subtechnique_config=config or {},
        )

        # Get subtechnique implementation
        key = f"{subtechnique}:{implementation}"
        if key not in self._subtechniques:
            available = list(self._subtechniques.keys())
            msg = f"Unknown subtechnique:implementation '{key}'. Available: {', '.join(available)}"
            raise ValueError(msg)

        subtechnique_obj = self._subtechniques[key]

        # Validate config
        if not subtechnique_obj.validate_config(merged_config):
            msg = f"Invalid configuration for {key}"
            raise ValueError(msg)

        # Execute
        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=implementation,
            input_data=input_data,
            config=merged_config,
            executor=lambda: subtechnique_obj.execute(input_data, merged_config),
        )

    def get_config(self) -> dict[str, Any]:
        """Get the default configuration for this technique"""
        return self._default_config.copy()

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Loaded configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not config_path.exists():
            msg = f"Config file not found: {config_path}"
            raise FileNotFoundError(msg)

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config is None:
                    msg = "Config file is empty"
                    raise ValueError(msg)
                if not isinstance(config, dict):
                    msg = "Config must be a dictionary"
                    raise TypeError(msg)
                return config
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in config file: {e}"
            raise ValueError(msg) from None

    def list_subtechniques(self) -> list[str]:
        """
        List all available subtechnique names.

        Returns:
            List of subtechnique names (without implementation suffix)
        """
        # Extract unique subtechnique names (before the colon)
        names = set()
        for key in self._subtechniques:
            name = key.split(":")[0] if ":" in key else key
            names.add(name)
        return sorted(names)

    def list_implementations(self, subtechnique: str) -> list[str]:
        """
        List all available implementations for a specific subtechnique.

        Args:
            subtechnique: Subtechnique name

        Returns:
            List of implementation names
        """
        implementations = []
        for key in self._subtechniques:
            if key.startswith(f"{subtechnique}:"):
                impl = key.split(":", 1)[1]
                implementations.append(impl)
        return implementations

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register subtechniques."""
        # Register quorum_voting implementations
        try:
            from .subtechniques.quorum_voting.default.five_agent import (
                FiveAgentConsensus,
            )  # plugin registration
            from .subtechniques.quorum_voting.default.single_agent import (
                SingleAgentConsensus,
            )  # plugin registration
            from .subtechniques.quorum_voting.default.three_agent import (
                ThreeAgentConsensus,
            )  # plugin registration

            self.register_subtechnique(FiveAgentConsensus(), "five_agent")
            self.register_subtechnique(ThreeAgentConsensus(), "three_agent")
            self.register_subtechnique(SingleAgentConsensus(), "single_agent")
        except ImportError:
            # Log warning but don't fail - allow partial loading
            pass

        # TODO: Register weighted_voting implementations when available
        # try:
        #     from .subtechniques.weighted_voting.default.confidence_weighted import ConfidenceWeightedConsensus
        #     from .subtechniques.weighted_voting.default.role_weighted import RoleWeightedConsensus
        #     self.register_subtechnique(ConfidenceWeightedConsensus(), "confidence_weighted")
        #     self.register_subtechnique(RoleWeightedConsensus(), "role_weighted")
        # except ImportError:
        #     pass

        # TODO: Register hybrid_consensus implementations when available
        # try:
        #     from .subtechniques.hybrid_consensus.default.voting_heuristic_mix import VotingHeuristicMix
        #     self.register_subtechnique(VotingHeuristicMix(), "voting_heuristic_mix")
        # except ImportError:
        #     pass

    def _load_technique_config(self) -> dict[str, Any]:
        """Load technique-level configuration."""
        if not self._config_path.exists():
            return {}

        try:
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except (OSError, yaml.YAMLError):
            return {}
