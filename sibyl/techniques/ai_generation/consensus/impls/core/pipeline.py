"""
Quorum Pipeline Orchestrator

Executes the complete 5-step atomic decision pipeline:
1. Diagnosis → 2. Strategy → 3. Location → 4. Fix → 5. Validation

Features:
- Per-step cost ceilings and budget tracking
- Checkpointing after each step for resume capability
- Context hash validation for idempotence
- Operation boundary enforcement (no rotation mid-pipeline)
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .atomic_agents import create_agent
from .contracts import (
    DiagnosisDecision,
    FixDecision,
    LocationDecision,
    StrategyDecision,
    ValidationDecision,
)
from .fallbacks import FallbackFactory
from .protocol import VotingPolicy
from .voting_orchestrator import VotingOrchestrator


@dataclass
class QuorumPipelineConfig:
    """Configuration for Quorum pipeline execution"""

    voting_policy: VotingPolicy
    enable_red_flagging: bool = True
    enable_fallbacks: bool = True
    checkpoint_per_step: bool = True
    max_cost_per_pipeline_cents: float = field(default_factory=lambda: _get_max_cost_per_pipeline())
    per_step_cost_ceilings: dict[str, float] = field(
        default_factory=lambda: _get_per_step_cost_ceilings()
    )


def _get_max_cost_per_pipeline() -> float:
    """Load max cost per pipeline from configuration."""
    try:
        from sibyl.config.loader import load_core_config

        config = load_core_config()
        consensus_config = config.get("consensus", {})
        return consensus_config.get("max_cost_per_pipeline_cents", 5.0)
    except Exception:
        return 5.0


def _get_per_step_cost_ceilings() -> dict[str, float]:
    """Load per-step cost ceilings from configuration."""
    try:
        from sibyl.config.loader import load_core_config

        config = load_core_config()
        consensus_config = config.get("consensus", {})
        pipeline_costs = consensus_config.get("pipeline_costs", {})

        # If config is empty, use fallback defaults
        if not pipeline_costs:
            return {
                "diagnosis": 0.5,
                "strategy": 0.4,
                "location": 0.8,
                "generation": 1.5,
                "validation": 0.3,
            }

        return pipeline_costs
    except Exception:
        # Fallback to hardcoded values
        return {
            "diagnosis": 0.5,
            "strategy": 0.4,
            "location": 0.8,
            "generation": 1.5,
            "validation": 0.3,
        }


class QuorumPipelineState(BaseModel):
    """
    State of pipeline execution.

    Persisted after each step for resume capability.
    """

    operation_id: str
    model_name: str
    error_message: str
    sql: str
    context_hash: str  # SHA256(sql + error_message) for idempotence check

    # Step outputs (None if not yet executed)
    diagnosis: DiagnosisDecision | None = None
    strategy: StrategyDecision | None = None
    location: LocationDecision | None = None
    fix: FixDecision | None = None
    validation: ValidationDecision | None = None

    # Tracking
    total_cost_cents: float = 0.0
    step_traces: list[dict] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def verify_resume_idempotence(self, sql: str, error_message: str) -> bool:
        """Verify context hasn't changed since checkpoint"""
        new_hash = hashlib.sha256(f"{sql}{error_message}".encode()).hexdigest()
        return new_hash == self.context_hash

    def is_complete(self) -> bool:
        """Check if all steps are complete"""
        return all(
            [
                self.diagnosis is not None,
                self.strategy is not None,
                self.location is not None,
                self.fix is not None,
                self.validation is not None,
            ]
        )

    def get_next_step(self) -> str | None:
        """Get the next step to execute"""
        if not self.diagnosis:
            return "diagnosis"
        if not self.strategy:
            return "strategy"
        if not self.location:
            return "location"
        if not self.fix:
            return "fix"
        if not self.validation:
            return "validation"
        return None  # Complete

    class Config:
        arbitrary_types_allowed = True


class QuorumPipeline:
    """
    Orchestrates the 5-step Quorum decision pipeline.

    Each step uses voting with k-voting, red-flagging, and fallbacks.
    Pipeline maintains total cost tracking and enforces ceilings.
    """

    def __init__(
        self,
        voting_orchestrator: VotingOrchestrator | None = None,
        fallback_factory: FallbackFactory | None = None,
        checkpoint_dir: Path | None = None,
    ) -> None:
        """
        Args:
            voting_orchestrator: Orchestrator for k-voting
            fallback_factory: Factory for fallback strategies
            checkpoint_dir: Directory for checkpoint storage
        """
        self.voting_orchestrator = voting_orchestrator or VotingOrchestrator()
        self.fallback_factory = fallback_factory or FallbackFactory()
        # Use system temp dir for portability (Windows/Linux/Mac)
        if checkpoint_dir is None:
            import tempfile

            checkpoint_dir = Path(tempfile.gettempdir()) / "quorum_checkpoints"
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        error_message: str,
        model_name: str,
        sql: str,
        config: QuorumPipelineConfig,
        resume_state: QuorumPipelineState | None = None,
        error_classifier: any | None = None,
    ) -> QuorumPipelineState:
        """
        Execute full 5-step pipeline with voting at each step.

        Args:
            error_message: SQL error to fix
            model_name: ExampleDomain model name
            sql: Full SQL content
            config: Pipeline configuration
            resume_state: Optional state to resume from
            error_classifier: Optional ErrorClassifier for fallback

        Returns:
            Final pipeline state with all decisions
        """
        # Initialize or resume state
        if resume_state:
            if not resume_state.verify_resume_idempotence(sql, error_message):
                msg = (
                    f"Cannot resume {resume_state.operation_id}: context has changed. "
                    "Create new operation or accept context drift."
                )
                raise ValueError(msg)
            state = resume_state
        else:
            state = QuorumPipelineState(
                operation_id=f"quorum-{model_name}-{int(time.time())}",
                model_name=model_name,
                error_message=error_message,
                sql=sql,
                context_hash=hashlib.sha256(f"{sql}{error_message}".encode()).hexdigest(),
            )

        # Update fallback factory with error classifier
        if error_classifier:
            self.fallback_factory.error_classifier = error_classifier

        # Execute each step
        remaining_budget = config.max_cost_per_pipeline_cents - state.total_cost_cents

        # Step 1: Diagnosis
        if not state.diagnosis:
            result = await self._execute_step(
                step_name="diagnosis",
                context={
                    "error_message": error_message,
                    "line_number": self._extract_error_line(error_message),
                    "code_snippet": self._extract_code_snippet(sql, error_message),
                },
                config=config,
                remaining_budget=remaining_budget,
            )
            state.diagnosis = result.decision
            state.total_cost_cents += result.cost_cents
            state.step_traces.append(result.trace)
            remaining_budget -= result.cost_cents

            if config.checkpoint_per_step:
                await self._save_checkpoint(state)

        # Step 2: Strategy
        if not state.strategy:
            result = await self._execute_step(
                step_name="strategy",
                context={
                    "diagnosis": state.diagnosis,
                    "error_message": error_message,
                    "available_strategies": [],
                },
                config=config,
                remaining_budget=remaining_budget,
            )
            state.strategy = result.decision
            state.total_cost_cents += result.cost_cents
            state.step_traces.append(result.trace)
            remaining_budget -= result.cost_cents

            if config.checkpoint_per_step:
                await self._save_checkpoint(state)

        # Step 3: Location
        if not state.location:
            result = await self._execute_step(
                step_name="location",
                context={
                    "sql": sql,
                    "diagnosis": state.diagnosis,
                    "error_line": self._extract_error_line(error_message),
                },
                config=config,
                remaining_budget=remaining_budget,
            )
            state.location = result.decision
            state.total_cost_cents += result.cost_cents
            state.step_traces.append(result.trace)
            remaining_budget -= result.cost_cents

            if config.checkpoint_per_step:
                await self._save_checkpoint(state)

        # Step 4: Fix Generation
        if not state.fix:
            result = await self._execute_step(
                step_name="fix",
                context={
                    "location": state.location,
                    "strategy": state.strategy,
                    "context_snippet": state.location.context_lines,
                },
                config=config,
                remaining_budget=remaining_budget,
            )
            state.fix = result.decision
            state.total_cost_cents += result.cost_cents
            state.step_traces.append(result.trace)
            remaining_budget -= result.cost_cents

            if config.checkpoint_per_step:
                await self._save_checkpoint(state)

        # Step 5: Validation
        if not state.validation:
            result = await self._execute_step(
                step_name="validation",
                context={
                    "original_code": sql,
                    "proposed_fix": state.fix,
                    "diagnosis": state.diagnosis,
                },
                config=config,
                remaining_budget=remaining_budget,
            )
            state.validation = result.decision
            state.total_cost_cents += result.cost_cents
            state.step_traces.append(result.trace)

            if config.checkpoint_per_step:
                await self._save_checkpoint(state)

        # Mark complete
        state.completed_at = time.time()
        await self._save_checkpoint(state)

        return state

    async def _execute_step(
        self,
        step_name: str,
        context: dict,
        config: QuorumPipelineConfig,
        remaining_budget: float,
    ) -> "StepResult":
        """
        Execute a single pipeline step with voting.

        Args:
            step_name: One of: diagnosis, strategy, location, fix, validation
            context: Context for this step
            config: Pipeline config
            remaining_budget: Remaining budget for pipeline

        Returns:
            StepResult with decision, cost, and trace
        """
        # Apply cost ceiling
        step_ceiling = config.per_step_cost_ceilings.get(step_name, 1.0)
        effective_ceiling = min(step_ceiling, remaining_budget)

        # Adjust voting policy for ceiling
        step_policy = self._apply_cost_ceiling(
            config.voting_policy,
            effective_ceiling,
        )

        # Create agent factory for this step
        def agent_factory() -> Any:
            return create_agent(step_name, config=None, llm_client=None)

        # Get fallback strategy
        fallback = self.fallback_factory.get_fallback(step_name)

        # Run voting
        start_time = time.time()
        voting_result = await self.voting_orchestrator.vote_on_decision(
            agent_factory=agent_factory,
            context=context,
            policy=step_policy,
            fallback_strategy=fallback if config.enable_fallbacks else None,
        )
        elapsed = time.time() - start_time

        # Create trace
        trace = {
            "step": step_name,
            "decision": voting_result.decision.model_dump(exclude={"provenance"}),
            "vote_distribution": voting_result.vote_distribution,
            "consensus_time_seconds": elapsed,
            "agents_used": voting_result.agents_used,
            "red_flagged_count": voting_result.red_flagged_count,
            "shape_violations_count": voting_result.shape_violations_count,
            "consensus_strength": voting_result.consensus_strength,
            "avg_confidence": voting_result.avg_confidence,
            "fallback_used": voting_result.fallback_used,
            "fallback_reason": voting_result.fallback_reason,
            "cost_cents": voting_result.projected_cost_cents,
        }

        return StepResult(
            decision=voting_result.decision,
            cost_cents=voting_result.projected_cost_cents,
            trace=trace,
        )

    def _apply_cost_ceiling(
        self,
        policy: VotingPolicy,
        effective_ceiling: float,
    ) -> VotingPolicy:
        """Adjust voting policy to respect cost ceiling"""
        # If ceiling very tight, reduce max_n
        if effective_ceiling < 1.0:
            return VotingPolicy(
                initial_n=min(policy.initial_n, 3),
                max_n=3,
                k_threshold=policy.k_threshold,
                min_k_fallback=policy.min_k_fallback,
                timeout_seconds=policy.timeout_seconds,
                per_agent_timeout=policy.per_agent_timeout,
                red_flag_escalation_threshold=policy.red_flag_escalation_threshold,
                min_avg_confidence=policy.min_avg_confidence,
                cost_ceiling_cents=effective_ceiling,
                enable_early_commit=policy.enable_early_commit,
            )

        return VotingPolicy(**{**asdict(policy), "cost_ceiling_cents": effective_ceiling})

    def _extract_error_line(self, error_message: str) -> int:
        """Extract line number from error message (heuristic)"""
        import re

        match = re.search(r"line (\d+)", error_message, re.IGNORECASE)
        return int(match.group(1)) if match else 1

    def _extract_code_snippet(self, sql: str, error_message: str) -> str:
        """Extract ±3 lines around error"""
        error_line = self._extract_error_line(error_message)
        lines = sql.split("\n")
        start = max(0, error_line - 4)  # -3 lines
        end = min(len(lines), error_line + 3)  # +2 lines
        return "\n".join(lines[start:end])

    async def _save_checkpoint(self, state: QuorumPipelineState) -> None:
        """Save pipeline state to checkpoint file"""
        checkpoint_file = self.checkpoint_dir / f"{state.operation_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(state.model_dump(), f, indent=2, default=str)

    async def load_checkpoint(self, operation_id: str) -> QuorumPipelineState | None:
        """Load pipeline state from checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file) as f:
            data = json.load(f)
            return QuorumPipelineState(**data)

    def cleanup_checkpoint(self, operation_id: str) -> None:
        """Delete checkpoint file after completion"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()


@dataclass
class StepResult:
    """Result of executing a single pipeline step"""

    decision: BaseModel
    cost_cents: float
    trace: dict
