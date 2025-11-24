"""
Five Agent Consensus Implementation

Full 5-agent Quorum pipeline with k-voting, fallbacks, and red-flag detection.
This implementation wraps the existing QuorumPipeline infrastructure while
providing the new pluggable technique interface.

Agents:
1. Diagnosis - Classify error category
2. Strategy - Choose fix approach
3. Location - Identify exact line range
4. Fix - Generate the fix code
5. Validation - Validate the fix
"""

import asyncio
from pathlib import Path
from typing import Any

import yaml

# Import from the existing quorum infrastructure
from sibyl.techniques.ai_generation.consensus import (
    QuorumPipeline,
    QuorumPipelineConfig,
    QuorumPipelineState,
    VotingPolicy,
)

# Import shared consensus protocols and contracts


class FiveAgentConsensus:
    """
    Five atomic agent consensus with k-voting, fallbacks, and red-flag detection.

    This is the full Quorum pipeline implementation with:
    - 5 atomic agents: Diagnosis, Strategy, Location, Fix, Validation
    - k-voting with configurable k (default: 3)
    - Deterministic fallbacks for each step
    - Red-flag filtering for quality control
    - Checkpointing for resumability
    - Budget tracking per step

    This implementation delegates to the existing QuorumPipeline while providing
    a clean interface for the pluggable technique architecture.
    """

    def __init__(self) -> None:
        self._name = "five_agent"
        self._description = "Full 5-agent Quorum pipeline with consensus voting"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._pipeline: QuorumPipeline | None = None
        self._default_config = self._load_default_config()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the five-agent consensus pipeline.

        Args:
            input_data: Dict with required keys:
                - error_message: str - The error message to diagnose
                - model_name: str - The model name (e.g., "my_model")
                - sql: str - The full SQL code
                - context: Optional[Dict] - Additional context
            config: Merged configuration from cascade

        Returns:
            Dict with:
                - diagnosis: DiagnosisDecision
                - strategy: StrategyDecision
                - location: LocationDecision
                - fix: FixDecision
                - validation: ValidationDecision
                - pipeline_state: QuorumPipelineState
                - total_cost_cents: float
                - traces: List[StepTrace]
        """
        # Validate input data
        self._validate_input(input_data)

        # Create voting policy from config
        voting_policy = self._create_voting_policy(config)

        # Create pipeline config
        pipeline_config = QuorumPipelineConfig(
            voting_policy=voting_policy,
            enable_red_flagging=config.get("enable_red_flags", True),
            enable_fallbacks=config.get("enable_fallbacks", True),
            checkpoint_per_step=config.get("enable_checkpointing", True),
            max_cost_per_pipeline_cents=config.get("max_cost_per_pipeline_cents", 5.0),
            per_step_cost_ceilings=config.get(
                "budget_ceilings",
                {
                    "diagnosis": 0.5,
                    "strategy": 0.4,
                    "location": 0.8,
                    "generation": 1.5,
                    "validation": 0.3,
                },
            ),
        )

        # Initialize pipeline if not already done
        if self._pipeline is None:
            checkpoint_dir = config.get("checkpoint_dir")
            if checkpoint_dir:
                checkpoint_dir = Path(checkpoint_dir)
            self._pipeline = QuorumPipeline(checkpoint_dir=checkpoint_dir)

        # Execute the pipeline
        # Note: The QuorumPipeline.execute is async, so we need to handle that
        result = asyncio.run(
            self._pipeline.execute(
                error_message=input_data["error_message"],
                model_name=input_data["model_name"],
                sql=input_data["sql"],
                config=pipeline_config,
                resume_state=input_data.get("resume_state"),
                error_classifier=input_data.get("error_classifier"),
            )
        )

        # Convert QuorumPipelineState to the expected output format
        return self._convert_pipeline_result(result)

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
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
        # Validate k_voting
        if "k_voting" in config:
            k = config["k_voting"]
            if not isinstance(k, int) or k < 1:
                msg = f"k_voting must be a positive integer, got: {k}"
                raise ValueError(msg)

        # Validate consensus_threshold
        if "consensus_threshold" in config:
            threshold = config["consensus_threshold"]
            if not (0.0 <= threshold <= 1.0):
                msg = f"consensus_threshold must be between 0.0 and 1.0, got: {threshold}"
                raise ValueError(msg)

        # Validate budget ceilings
        if "budget_ceilings" in config:
            ceilings = config["budget_ceilings"]
            if not isinstance(ceilings, dict):
                msg = "budget_ceilings must be a dictionary"
                raise ValueError(msg)

            for step, ceiling in ceilings.items():
                if not isinstance(ceiling, (int, float)) or ceiling < 0:
                    msg = f"Budget ceiling for {step} must be a non-negative number, got: {ceiling}"
                    raise ValueError(msg)

        # Validate agent configs
        if "agents" in config:
            agents = config["agents"]
            if not isinstance(agents, dict):
                msg = "agents must be a dictionary"
                raise ValueError(msg)

            expected_agents = ["diagnosis", "strategy", "location", "fix", "validation"]
            for agent_name in agents:
                if agent_name not in expected_agents:
                    msg = f"Unknown agent: {agent_name}. Expected one of: {expected_agents}"
                    raise ValueError(msg)

        return True

    def _load_default_config(self) -> dict[str, Any]:
        """Load default configuration from config.yaml"""
        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
                # Return subtechnique-specific config if available
                if isinstance(config, dict):
                    return config.get("quorum_voting", {})
                return config if config else {}
        return {}

    def _validate_input(self, input_data: Any) -> None:
        """Validate input data structure"""
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary"
            raise TypeError(msg)

        required_keys = ["error_message", "model_name", "sql"]
        for key in required_keys:
            if key not in input_data:
                msg = f"input_data missing required key: {key}"
                raise ValueError(msg)

        if not isinstance(input_data["error_message"], str):
            msg = "error_message must be a string"
            raise TypeError(msg)

        if not isinstance(input_data["model_name"], str):
            msg = "model_name must be a string"
            raise TypeError(msg)

        if not isinstance(input_data["sql"], str):
            msg = "sql must be a string"
            raise TypeError(msg)

    def _create_voting_policy(self, config: dict[str, Any]) -> VotingPolicy:
        """Create VotingPolicy from configuration"""
        return VotingPolicy(
            initial_n=config.get("initial_n", 3),
            max_n=config.get("max_n", 5),
            k_threshold=config.get("k_voting", 3),
            min_k_fallback=config.get("min_k_fallback", 2),
            timeout_seconds=config.get("timeout_seconds", 10.0),
            per_agent_timeout=config.get("per_agent_timeout", 5.0),
            red_flag_escalation_threshold=config.get("red_flag_escalation_threshold", 0.3),
            min_avg_confidence=config.get("consensus_threshold", 0.6),
            cost_ceiling_cents=config.get("cost_ceiling_cents", 2.0),
            enable_early_commit=config.get("enable_early_commit", True),
        )

    def _convert_pipeline_result(self, state: QuorumPipelineState) -> dict[str, Any]:
        """
        Convert QuorumPipelineState to the expected output format.

        Args:
            state: The pipeline state from QuorumPipeline

        Returns:
            Dict with consensus results
        """
        return {
            "operation_id": state.operation_id,
            "diagnosis": state.diagnosis,
            "strategy": state.strategy,
            "location": state.location,
            "fix": state.fix,
            "validation": state.validation,
            "total_cost_cents": state.total_cost_cents,
            "traces": state.step_traces,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "is_complete": state.is_complete(),
        }
