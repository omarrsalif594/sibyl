"""
Voting Coordinator for Quorum Engine

Coordinates agent execution with red-flag filtering and consensus checking.
Delegates consensus resolution to ConsensusResolver for better SRP compliance.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from sibyl.core.infrastructure.security.validators.llm_output_gate import RedFlagDetector
from sibyl.core.infrastructure.security.validators.shape_gate import ShapeGate, ShapeViolation
from sibyl.techniques.ai_generation.consensus.impls.protocol import (
    AtomicAgent,
    DecisionT,
    FallbackStrategy,
    VotingPolicy,
    VotingResult,
)
from sibyl.techniques.ai_generation.consensus.impls.vote_aggregator import VoteAggregator

from .consensus_resolver import ConsensusResolver


class VotingCoordinator:
    """
    Coordinates multi-agent voting with budget awareness.

    Configuration loaded from voting technique (eliminates hardcoded values).
    All voting parameters (initial_n, max_n, k_threshold, etc.) are sourced
    from VotingPolicy which can be created via VotingPolicy.from_technique().

    Responsibilities:
    - Launch and manage agent tasks
    - Track state (launched, cost, cancelled)
    - Handle timeouts and cancellation
    - Validate outputs (shape gate + red flags)
    - Spawn replacements for invalid outputs
    - Delegate consensus checking to ConsensusResolver

    Does NOT:
    - Determine consensus (delegates to ConsensusResolver)
    - Apply fallback strategies (delegates to ConsensusResolver)
    - Aggregate votes (delegates to VoteAggregator)

    Algorithm:
    1. Launch initial_n agents in parallel (from policy)
    2. Track projected cost
    3. For each output:
       a. Validate shape (raises ShapeViolation)
       b. Check red flags
       c. Spawn replacements if needed
       d. Add clean votes to aggregator
       e. Check for early consensus (via ConsensusResolver)
    4. On timeout or completion:
       - Delegate final resolution to ConsensusResolver
    """

    def __init__(
        self,
        shape_gate: ShapeGate | None = None,
        red_flag_detector: RedFlagDetector | None = None,
        consensus_resolver: ConsensusResolver | None = None,
        enable_cancellation: bool = True,
    ) -> None:
        """
        Initialize voting coordinator.

        Configuration loaded from voting technique (eliminates hardcoded values).
        Uses VotingPolicy passed to vote_on_decision() for all voting parameters.

        Args:
            shape_gate: Shape gate for schema validation
            red_flag_detector: Red-flag detector for output filtering
            consensus_resolver: Consensus resolver for decision resolution
            enable_cancellation: Enable early cancellation on consensus
        """
        self.shape_gate = shape_gate or ShapeGate()
        self.red_flag_detector = red_flag_detector or RedFlagDetector()
        self.consensus_resolver = consensus_resolver or ConsensusResolver()
        self.enable_cancellation = enable_cancellation

        # Cost estimation (approximate)
        # TODO: Integrate with actual LLM pricing from router
        self.cost_per_agent_cents = {
            "gpt-4o-mini": 0.05,  # ~50 tokens in + 50 out = $0.0005
            "claude-haiku": 0.03,
            "gpt-4o": 0.2,
        }

    async def vote_on_decision(
        self,
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        fallback_strategy: FallbackStrategy[DecisionT] | None = None,
    ) -> VotingResult[DecisionT]:
        """
        Coordinate voting across multiple agents.

        Args:
            agent_factory: Factory function that creates agent instances
            context: Context to pass to agents
            policy: Voting policy configuration
            fallback_strategy: Optional fallback if consensus fails

        Returns:
            VotingResult with winning decision and metadata
        """
        start_time = time.time()

        # Initialize voting state
        state = self._initialize_voting_state(agent_factory, policy)
        aggregator = VoteAggregator[DecisionT](policy)

        # Launch initial agents
        tasks = self._launch_initial_agents(agent_factory, context, policy, state)

        # Process results as they arrive
        try:
            await self._process_voting_results(
                tasks, aggregator, agent_factory, context, policy, state, start_time
            )
        except TimeoutError:
            # Timeout - cancel remaining tasks
            self._cancel_remaining_tasks(tasks, state)

        # No early consensus - delegate final resolution
        elapsed = time.time() - start_time
        return self.consensus_resolver.resolve_final(
            aggregator,
            policy,
            context,
            fallback_strategy,
            state["agents_launched"],
            state["red_flagged_count"],
            state["shape_violations_count"],
            state["projected_cost"],
            state["cancelled_count"],
            state["cancelled_tokens"],
            elapsed,
        )

    def _initialize_voting_state(
        self,
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        policy: VotingPolicy,
    ) -> dict[str, Any]:
        """
        Initialize voting state with sample agent and cost estimates.

        Args:
            agent_factory: Factory function that creates agent instances
            policy: Voting policy configuration

        Returns:
            Dictionary with initial state
        """
        # Get sample agent to determine model and decision type
        sample_agent = agent_factory()
        model_name = sample_agent.get_model_name()
        decision_type = sample_agent.get_decision_type()
        cost_per_agent = self.cost_per_agent_cents.get(model_name, 0.1)

        return {
            "agents_launched": 0,
            "projected_cost": 0.0,
            "red_flagged_count": 0,
            "shape_violations_count": 0,
            "cancelled_count": 0,
            "cancelled_tokens": 0,
            "model_name": model_name,
            "decision_type": decision_type,
            "cost_per_agent": cost_per_agent,
        }

    def _launch_initial_agents(
        self,
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        state: dict[str, Any],
    ) -> set[asyncio.Task]:
        """
        Launch initial batch of agent tasks.

        Args:
            agent_factory: Factory function that creates agent instances
            context: Context to pass to agents
            policy: Voting policy configuration
            state: Voting state dictionary

        Returns:
            Set of asyncio tasks
        """
        tasks: set[asyncio.Task] = set()

        for _i in range(policy.initial_n):
            if self._can_spawn_agent(state, policy):
                agent = agent_factory()
                task = asyncio.create_task(
                    self._run_agent_with_timeout(
                        agent,
                        context,
                        policy.per_agent_timeout,
                        agent_id=f"{state['model_name']}-{state['agents_launched']}",
                    )
                )
                tasks.add(task)
                state["agents_launched"] += 1
                state["projected_cost"] += state["cost_per_agent"]

        return tasks

    async def _process_voting_results(
        self,
        tasks: set[asyncio.Task],
        aggregator: VoteAggregator[DecisionT],
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        state: dict[str, Any],
        start_time: float,
    ) -> None:
        """
        Process voting results as tasks complete.

        Args:
            tasks: Set of agent tasks
            aggregator: Vote aggregator
            agent_factory: Factory for creating replacement agents
            context: Context to pass to agents
            policy: Voting policy configuration
            state: Voting state dictionary
            start_time: Start time for elapsed calculation
        """
        while tasks:
            # Wait for any task to complete
            done, _pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED, timeout=policy.timeout_seconds
            )

            # Process completed tasks
            for task in done:
                tasks.remove(task)

                try:
                    result = task.result()
                    await self._process_agent_result(
                        result,
                        aggregator,
                        agent_factory,
                        context,
                        policy,
                        tasks,
                        state,
                        start_time,
                    )
                except Exception:
                    # Agent failed - continue with others
                    continue

    async def _process_agent_result(
        self,
        result: dict,
        aggregator: VoteAggregator[DecisionT],
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        tasks: set[asyncio.Task],
        state: dict[str, Any],
        start_time: float,
    ) -> None:
        """
        Process a single agent result through validation and consensus check.

        Args:
            result: Agent result dictionary
            aggregator: Vote aggregator
            agent_factory: Factory for creating replacement agents
            context: Context to pass to agents
            policy: Voting policy configuration
            tasks: Set of agent tasks
            state: Voting state dictionary
            start_time: Start time for elapsed calculation
        """
        # Step 1: Validate shape
        if not self._validate_shape(result, state, agent_factory, context, policy, tasks):
            return

        # Step 2: Check red flags
        validated = result["validated"]
        if not self._check_red_flags(validated, context, state, agent_factory, policy, tasks):
            return

        # Step 3: Add clean vote
        aggregator.add_vote(
            decision=validated,
            confidence=validated.confidence,
            agent_id=result["agent_id"],
        )

        # Step 4: Check for early consensus
        if await self._check_early_consensus(aggregator, policy, state, tasks, start_time):
            return  # Early consensus reached

        # Step 5: Adaptive escalation (if split vote)
        self._handle_adaptive_escalation(aggregator, agent_factory, context, policy, tasks, state)

    def _validate_shape(
        self,
        result: dict,
        state: dict[str, Any],
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        tasks: set[asyncio.Task],
    ) -> bool:
        """
        Validate shape of agent output.

        Args:
            result: Agent result dictionary
            state: Voting state dictionary
            agent_factory: Factory for replacement agents
            context: Context to pass to agents
            policy: Voting policy configuration
            tasks: Set of agent tasks

        Returns:
            True if validation passed, False if failed (replacement spawned)
        """
        try:
            validated = self.shape_gate.validate(
                result["raw_output"],
                state["decision_type"],
                context,
            )
            result["validated"] = validated
            return True
        except ShapeViolation:
            state["shape_violations_count"] += 1
            # Spawn replacement if budget allows
            self._spawn_replacement_agent(agent_factory, context, policy, tasks, state)
            return False

    def _check_red_flags(
        self,
        validated: Any,
        context: dict[str, Any],
        state: dict[str, Any],
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        policy: VotingPolicy,
        tasks: set[asyncio.Task],
    ) -> bool:
        """
        Check for red flags in validated output.

        Args:
            validated: Validated output
            context: Context for red flag detection
            state: Voting state dictionary
            agent_factory: Factory for replacement agents
            policy: Voting policy configuration
            tasks: Set of agent tasks

        Returns:
            True if no red flags, False if red-flagged (replacement spawned)
        """
        red_flag_result = self.red_flag_detector.check_all(validated, context)
        if red_flag_result:
            state["red_flagged_count"] += 1
            # Spawn replacement if budget allows and red-flag rate not too high
            red_flag_rate = state["red_flagged_count"] / max(state["agents_launched"], 1)
            if red_flag_rate < policy.red_flag_escalation_threshold:
                self._spawn_replacement_agent(agent_factory, context, policy, tasks, state)
            return False
        return True

    async def _check_early_consensus(
        self,
        aggregator: VoteAggregator[DecisionT],
        policy: VotingPolicy,
        state: dict[str, Any],
        tasks: set[asyncio.Task],
        start_time: float,
    ) -> bool:
        """
        Check for early consensus and handle cancellation.

        Args:
            aggregator: Vote aggregator
            policy: Voting policy configuration
            state: Voting state dictionary
            tasks: Set of agent tasks
            start_time: Start time for elapsed calculation

        Returns:
            True if early consensus reached, False otherwise
        """
        elapsed = time.time() - start_time
        consensus_result = self.consensus_resolver.check_early_consensus(
            aggregator,
            policy,
            state["agents_launched"],
            state["red_flagged_count"],
            state["shape_violations_count"],
            state["projected_cost"],
            state["cancelled_count"],
            state["cancelled_tokens"],
            elapsed,
        )

        if consensus_result:
            # Cancel remaining tasks
            if self.enable_cancellation:
                for pending_task in tasks:
                    pending_task.cancel()
                    state["cancelled_count"] += 1
                    state["cancelled_tokens"] += self._estimate_tokens_per_agent(
                        state["model_name"]
                    )
            return True

        return False

    def _handle_adaptive_escalation(
        self,
        aggregator: VoteAggregator[DecisionT],
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        tasks: set[asyncio.Task],
        state: dict[str, Any],
    ) -> None:
        """
        Handle adaptive escalation when votes are split.

        Args:
            aggregator: Vote aggregator
            agent_factory: Factory for creating agents
            context: Context to pass to agents
            policy: Voting policy configuration
            tasks: Set of agent tasks
            state: Voting state dictionary
        """
        if aggregator.has_split_vote() and state["agents_launched"] < policy.max_n:
            self._spawn_replacement_agent(agent_factory, context, policy, tasks, state)

    def _spawn_replacement_agent(
        self,
        agent_factory: Callable[[], AtomicAgent[DecisionT]],
        context: dict[str, Any],
        policy: VotingPolicy,
        tasks: set[asyncio.Task],
        state: dict[str, Any],
    ) -> None:
        """
        Spawn a replacement agent if budget allows.

        Args:
            agent_factory: Factory function that creates agent instances
            context: Context to pass to agents
            policy: Voting policy configuration
            tasks: Set of agent tasks to add to
            state: Voting state dictionary
        """
        if self._can_spawn_agent(state, policy):
            agent = agent_factory()
            new_task = asyncio.create_task(
                self._run_agent_with_timeout(
                    agent,
                    context,
                    policy.per_agent_timeout,
                    f"{state['model_name']}-{state['agents_launched']}",
                )
            )
            tasks.add(new_task)
            state["agents_launched"] += 1
            state["projected_cost"] += state["cost_per_agent"]

    def _can_spawn_agent(
        self,
        state: dict[str, Any],
        policy: VotingPolicy,
    ) -> bool:
        """
        Check if we can spawn another agent within budget.

        Args:
            state: Voting state dictionary
            policy: Voting policy configuration

        Returns:
            True if within budget, False otherwise
        """
        return (
            state["agents_launched"] < policy.max_n
            and state["projected_cost"] + state["cost_per_agent"] <= policy.cost_ceiling_cents
        )

    def _cancel_remaining_tasks(
        self,
        tasks: set[asyncio.Task],
        state: dict[str, Any],
    ) -> None:
        """
        Cancel all remaining tasks on timeout.

        Args:
            tasks: Set of agent tasks to cancel
            state: Voting state dictionary
        """
        for task in tasks:
            task.cancel()
            state["cancelled_count"] += 1

    async def _run_agent_with_timeout(
        self,
        agent: AtomicAgent,
        context: dict,
        timeout: float,
        agent_id: str,
    ) -> dict:
        """
        Run a single agent with timeout.

        Returns:
            Dict with raw_output and agent_id
        """
        try:
            decision = await asyncio.wait_for(
                agent.decide(context, timeout=timeout),
                timeout=timeout,
            )
            return {
                "raw_output": decision.model_dump(),
                "agent_id": agent_id,
            }
        except TimeoutError:
            msg = f"Agent {agent_id} exceeded timeout of {timeout}s"
            raise TimeoutError(msg) from None

    def _estimate_tokens_per_agent(self, model_name: str) -> int:
        """Estimate tokens per agent (rough approximation)"""
        # Typical: 50 tokens input + 50 tokens output = 100 tokens
        return 100

    def _estimate_agent_cost(self, model_name: str) -> float:
        """Estimate cost per agent in cents"""
        return self.cost_per_agent_cents.get(model_name, 0.1)
