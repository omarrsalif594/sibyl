"""
Three Agent Consensus Implementation

Simplified 3-agent consensus for faster, cheaper decisions:
- Analysis (combines Diagnosis + Strategy)
- Solution (combines Location + Fix)
- Validation

Uses k=2 voting with simpler fallbacks and no red-flag detection.
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


class ThreeAgentConsensus:
    """
    Simplified 3-agent consensus: Analysis, Solution, Validation.

    Faster and cheaper than five-agent, suitable for:
    - Less critical decisions
    - Cost-sensitive applications
    - Simpler problems

    This implementation uses the five-agent pipeline but with simplified
    voting (k=2) and no red-flag detection.
    """

    def __init__(self) -> None:
        self._name = "three_agent"
        self._description = "Simplified 3-agent consensus (k=2 voting, no red flags)"
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
        Execute the three-agent consensus pipeline.

        Args:
            input_data: Dict with required keys:
                - error_message: str - The error message to diagnose
                - model_name: str - The model name
                - sql: str - The full SQL code
                - context: Optional[Dict] - Additional context
            config: Merged configuration from cascade

        Returns:
            Dict with consensus results (same format as FiveAgentConsensus)
        """
        # Validate input data
        self._validate_input(input_data)

        # Create simplified voting policy (k=2)
        voting_policy = self._create_voting_policy(config)

        # Create pipeline config with simplified settings
        pipeline_config = QuorumPipelineConfig(
            voting_policy=voting_policy,
            enable_red_flagging=False,  # Disabled for speed
            enable_fallbacks=config.get("enable_fallbacks", True),
            checkpoint_per_step=config.get("enable_checkpointing", False),  # Disabled by default
            max_cost_per_pipeline_cents=config.get(
                "max_cost_per_pipeline_cents", 3.0
            ),  # Lower ceiling
            per_step_cost_ceilings=config.get(
                "budget_ceilings",
                {
                    "diagnosis": 0.3,
                    "strategy": 0.3,
                    "location": 0.5,
                    "generation": 1.0,
                    "validation": 0.2,
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

        # Convert to output format
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
        # Validate k_voting (should be ≤ 3 for three-agent)
        if "k_voting" in config:
            k = config["k_voting"]
            if not isinstance(k, int) or k < 1 or k > 3:
                msg = f"k_voting must be between 1 and 3 for three-agent, got: {k}"
                raise ValueError(msg)

        # Validate consensus_threshold
        if "consensus_threshold" in config:
            threshold = config["consensus_threshold"]
            if not (0.0 <= threshold <= 1.0):
                msg = f"consensus_threshold must be between 0.0 and 1.0, got: {threshold}"
                raise ValueError(msg)

        return True

    def _load_default_config(self) -> dict[str, Any]:
        """Load default configuration from config.yaml"""
        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
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
        """Create VotingPolicy from configuration with three-agent defaults"""
        return VotingPolicy(
            initial_n=config.get("initial_n", 2),  # Start with 2
            max_n=config.get("max_n", 3),  # Max 3
            k_threshold=config.get("k_voting", 2),  # k=2
            min_k_fallback=config.get("min_k_fallback", 1),  # Fallback to 1
            timeout_seconds=config.get("timeout_seconds", 8.0),  # Shorter timeout
            per_agent_timeout=config.get("per_agent_timeout", 4.0),
            red_flag_escalation_threshold=1.0,  # Disabled
            min_avg_confidence=config.get("consensus_threshold", 0.5),  # Lower threshold
            cost_ceiling_cents=config.get("cost_ceiling_cents", 1.5),
            enable_early_commit=config.get("enable_early_commit", True),
        )

    def _convert_pipeline_result(self, state: QuorumPipelineState) -> dict[str, Any]:
        """Convert QuorumPipelineState to the expected output format"""
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
