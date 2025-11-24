"""
Single Agent Consensus Implementation

No consensus, single agent execution. Fastest and cheapest option.
Suitable for:
- Testing and development
- Non-critical applications
- Maximum speed/cost efficiency

Uses k=1 (no voting), no fallbacks, no red-flags.
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


class SingleAgentConsensus:
    """
    Single agent, no consensus. Fastest and cheapest option.

    This implementation uses k=1 (single execution per step) with:
    - No voting
    - No red-flag detection
    - No fallbacks (fails fast)
    - No checkpointing

    Suitable for development, testing, or non-critical use cases where
    speed and cost are more important than reliability.
    """

    def __init__(self) -> None:
        self._name = "single_agent"
        self._description = "Single agent, no voting (fastest, cheapest)"
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
        Execute the single-agent pipeline (no consensus).

        Args:
            input_data: Dict with required keys:
                - error_message: str - The error message to diagnose
                - model_name: str - The model name
                - sql: str - The full SQL code
                - context: Optional[Dict] - Additional context
            config: Merged configuration from cascade

        Returns:
            Dict with results (same format as FiveAgentConsensus)
        """
        # Validate input data
        self._validate_input(input_data)

        # Create minimal voting policy (k=1, no consensus)
        voting_policy = self._create_voting_policy(config)

        # Create pipeline config with minimal settings
        pipeline_config = QuorumPipelineConfig(
            voting_policy=voting_policy,
            enable_red_flagging=False,  # Disabled
            enable_fallbacks=False,  # Disabled
            checkpoint_per_step=False,  # Disabled
            max_cost_per_pipeline_cents=config.get(
                "max_cost_per_pipeline_cents", 2.0
            ),  # Low ceiling
            per_step_cost_ceilings=config.get(
                "budget_ceilings",
                {
                    "diagnosis": 0.2,
                    "strategy": 0.2,
                    "location": 0.3,
                    "generation": 0.6,
                    "validation": 0.15,
                },
            ),
        )

        # Initialize pipeline if not already done
        if self._pipeline is None:
            self._pipeline = QuorumPipeline(checkpoint_dir=None)

        # Execute the pipeline
        result = asyncio.run(
            self._pipeline.execute(
                error_message=input_data["error_message"],
                model_name=input_data["model_name"],
                sql=input_data["sql"],
                config=pipeline_config,
                resume_state=None,  # No resume support
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
        # For single-agent, k_voting must be 1
        if "k_voting" in config:
            k = config["k_voting"]
            if k != 1:
                msg = f"k_voting must be 1 for single-agent, got: {k}"
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
        """Create VotingPolicy from configuration with single-agent defaults"""
        return VotingPolicy(
            initial_n=1,  # Single agent
            max_n=1,  # No escalation
            k_threshold=1,  # No consensus needed
            min_k_fallback=1,  # No fallback
            timeout_seconds=config.get("timeout_seconds", 5.0),  # Short timeout
            per_agent_timeout=config.get("per_agent_timeout", 3.0),
            red_flag_escalation_threshold=1.0,  # Disabled
            min_avg_confidence=0.0,  # Accept any confidence
            cost_ceiling_cents=config.get("cost_ceiling_cents", 0.5),
            enable_early_commit=False,  # Not applicable for single agent
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
