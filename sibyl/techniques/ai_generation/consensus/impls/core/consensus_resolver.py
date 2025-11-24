"""
Consensus Resolver for Quorum Engine

Determines consensus from votes and applies fallback strategies when needed.
Separated from orchestration logic for better SRP compliance.
"""

from typing import Any

from sibyl.techniques.ai_generation.consensus.impls.protocol import (
    DecisionT,
    FallbackStrategy,
    VotingPolicy,
    VotingResult,
)
from sibyl.techniques.ai_generation.consensus.impls.vote_aggregator import VoteAggregator


class ConsensusResolver:
    """
    Resolves consensus from vote aggregator with fallback strategies.

    Configuration loaded from voting technique (eliminates hardcoded values).
    All voting parameters (k_threshold, min_k_fallback, etc.) are sourced
    from VotingPolicy which can be created via VotingPolicy.from_technique().

    Responsibilities:
    - Check for consensus with confidence thresholds
    - Apply fallback k when primary k fails
    - Invoke fallback strategies when no consensus
    - Build VotingResult with complete metadata

    Does NOT:
    - Launch agents
    - Manage timeouts
    - Track costs
    - Handle red flags
    """

    def __init__(self) -> None:
        """
        Initialize consensus resolver.

        Configuration loaded from voting technique (eliminates hardcoded values).
        Uses VotingPolicy passed to methods for all threshold values.
        """

    def check_early_consensus(
        self,
        aggregator: VoteAggregator[DecisionT],
        policy: VotingPolicy,
        agents_launched: int,
        red_flagged_count: int,
        shape_violations_count: int,
        projected_cost_cents: float,
        cancelled_count: int,
        cancelled_tokens: int,
        elapsed_seconds: float,
    ) -> VotingResult[DecisionT] | None:
        """
        Check for early consensus during voting.

        Args:
            aggregator: Vote aggregator with current votes
            policy: Voting policy with thresholds
            agents_launched: Number of agents launched so far
            red_flagged_count: Number of red-flagged outputs
            shape_violations_count: Number of shape violations
            projected_cost_cents: Projected cost so far
            cancelled_count: Number of cancelled agents
            cancelled_tokens: Tokens saved by cancellation
            elapsed_seconds: Time elapsed since voting started

        Returns:
            VotingResult if consensus reached, None otherwise
        """
        if not policy.enable_early_commit:
            return None

        # Check for k consensus with confidence threshold
        consensus = aggregator.check_consensus_with_confidence(
            k=policy.k_threshold,
            min_avg_confidence=policy.min_avg_confidence,
        )

        if consensus:
            return VotingResult(
                decision=consensus.decision,
                vote_distribution=aggregator.get_vote_distribution(),
                consensus_time_seconds=elapsed_seconds,
                agents_used=agents_launched,
                red_flagged_count=red_flagged_count,
                shape_violations_count=shape_violations_count,
                consensus_strength=consensus.k / agents_launched,
                avg_confidence=consensus.avg_confidence,
                fallback_used=False,
                projected_cost_cents=projected_cost_cents,
                cancelled_agents_count=cancelled_count,
                cancelled_saved_tokens=cancelled_tokens,
            )

        return None

    def resolve_with_fallback_k(
        self,
        aggregator: VoteAggregator[DecisionT],
        policy: VotingPolicy,
        agents_launched: int,
        red_flagged_count: int,
        shape_violations_count: int,
        projected_cost_cents: float,
        cancelled_count: int,
        cancelled_tokens: int,
        elapsed_seconds: float,
    ) -> VotingResult[DecisionT] | None:
        """
        Try to resolve with fallback k threshold.

        Used when primary k cannot be reached but we have enough votes
        for a degraded consensus.

        Args:
            aggregator: Vote aggregator with current votes
            policy: Voting policy with fallback k threshold
            agents_launched: Number of agents launched
            red_flagged_count: Number of red-flagged outputs
            shape_violations_count: Number of shape violations
            projected_cost_cents: Projected cost
            cancelled_count: Number of cancelled agents
            cancelled_tokens: Tokens saved by cancellation
            elapsed_seconds: Time elapsed

        Returns:
            VotingResult if fallback consensus reached, None otherwise
        """
        # Try fallback k
        consensus = aggregator.check_consensus_with_confidence(
            k=policy.min_k_fallback,
            min_avg_confidence=policy.min_avg_confidence,
        )

        if consensus:
            return VotingResult(
                decision=consensus.decision,
                vote_distribution=aggregator.get_vote_distribution(),
                consensus_time_seconds=elapsed_seconds,
                agents_used=agents_launched,
                red_flagged_count=red_flagged_count,
                shape_violations_count=shape_violations_count,
                consensus_strength=consensus.k / agents_launched,
                avg_confidence=consensus.avg_confidence,
                fallback_used=True,
                fallback_reason="timeout_fallback_k",
                projected_cost_cents=projected_cost_cents,
                cancelled_agents_count=cancelled_count,
                cancelled_saved_tokens=cancelled_tokens,
            )

        return None

    def resolve_with_strategy(
        self,
        aggregator: VoteAggregator[DecisionT],
        fallback_strategy: FallbackStrategy[DecisionT],
        context: dict[str, Any],
        reason: str,
        agents_launched: int,
        red_flagged_count: int,
        shape_violations_count: int,
        projected_cost_cents: float,
        cancelled_count: int,
        cancelled_tokens: int,
        elapsed_seconds: float,
    ) -> VotingResult[DecisionT]:
        """
        Resolve using fallback strategy.

        Used when no consensus can be reached and a deterministic
        fallback decision is needed.

        Args:
            aggregator: Vote aggregator with current votes
            fallback_strategy: Fallback strategy to apply
            context: Decision context
            reason: Why fallback was triggered
            agents_launched: Number of agents launched
            red_flagged_count: Number of red-flagged outputs
            shape_violations_count: Number of shape violations
            projected_cost_cents: Projected cost
            cancelled_count: Number of cancelled agents
            cancelled_tokens: Tokens saved by cancellation
            elapsed_seconds: Time elapsed

        Returns:
            VotingResult with fallback decision
        """
        # Collect all votes for fallback
        votes = []
        for vote_list in aggregator.votes.values():
            votes.extend([v[0] for v in vote_list])

        fallback_result = fallback_strategy.apply(votes, context, reason)

        return VotingResult(
            decision=fallback_result.decision,
            vote_distribution=aggregator.get_vote_distribution(),
            consensus_time_seconds=elapsed_seconds,
            agents_used=agents_launched,
            red_flagged_count=red_flagged_count,
            shape_violations_count=shape_violations_count,
            consensus_strength=0.0,  # No consensus
            avg_confidence=fallback_result.confidence,
            fallback_used=True,
            fallback_reason=fallback_result.reason,
            projected_cost_cents=projected_cost_cents,
            cancelled_agents_count=cancelled_count,
            cancelled_saved_tokens=cancelled_tokens,
        )

    def resolve_with_top_vote(
        self,
        aggregator: VoteAggregator[DecisionT],
        agents_launched: int,
        red_flagged_count: int,
        shape_violations_count: int,
        projected_cost_cents: float,
        cancelled_count: int,
        cancelled_tokens: int,
        elapsed_seconds: float,
    ) -> VotingResult[DecisionT] | None:
        """
        Resolve using top vote as last resort.

        Used when fallback strategy is not available and we need
        to return something.

        Args:
            aggregator: Vote aggregator with current votes
            agents_launched: Number of agents launched
            red_flagged_count: Number of red-flagged outputs
            shape_violations_count: Number of shape violations
            projected_cost_cents: Projected cost
            cancelled_count: Number of cancelled agents
            cancelled_tokens: Tokens saved by cancellation
            elapsed_seconds: Time elapsed

        Returns:
            VotingResult with top vote, or None if no votes
        """
        top_vote = aggregator.get_top_vote_with_tiebreak()
        if top_vote:
            decision, count, avg_conf = top_vote
            return VotingResult(
                decision=decision,
                vote_distribution=aggregator.get_vote_distribution(),
                consensus_time_seconds=elapsed_seconds,
                agents_used=agents_launched,
                red_flagged_count=red_flagged_count,
                shape_violations_count=shape_violations_count,
                consensus_strength=count / agents_launched if agents_launched > 0 else 0.0,
                avg_confidence=avg_conf,
                fallback_used=True,
                fallback_reason="top_vote",
                projected_cost_cents=projected_cost_cents,
                cancelled_agents_count=cancelled_count,
                cancelled_saved_tokens=cancelled_tokens,
            )

        return None

    def resolve_final(
        self,
        aggregator: VoteAggregator[DecisionT],
        policy: VotingPolicy,
        context: dict[str, Any],
        fallback_strategy: FallbackStrategy[DecisionT] | None,
        agents_launched: int,
        red_flagged_count: int,
        shape_violations_count: int,
        projected_cost_cents: float,
        cancelled_count: int,
        cancelled_tokens: int,
        elapsed_seconds: float,
    ) -> VotingResult[DecisionT]:
        """
        Resolve voting with fallback cascade.

        Tries:
        1. Fallback k consensus
        2. Fallback strategy (if provided)
        3. Top vote
        4. Raise error if no votes at all

        Args:
            aggregator: Vote aggregator with current votes
            policy: Voting policy
            context: Decision context
            fallback_strategy: Optional fallback strategy
            agents_launched: Number of agents launched
            red_flagged_count: Number of red-flagged outputs
            shape_violations_count: Number of shape violations
            projected_cost_cents: Projected cost
            cancelled_count: Number of cancelled agents
            cancelled_tokens: Tokens saved by cancellation
            elapsed_seconds: Time elapsed

        Returns:
            VotingResult with resolved decision

        Raises:
            RuntimeError: If no votes received at all
        """
        # 1. Try fallback k
        result = self.resolve_with_fallback_k(
            aggregator,
            policy,
            agents_launched,
            red_flagged_count,
            shape_violations_count,
            projected_cost_cents,
            cancelled_count,
            cancelled_tokens,
            elapsed_seconds,
        )
        if result:
            return result

        # 2. Try fallback strategy
        if fallback_strategy:
            return self.resolve_with_strategy(
                aggregator,
                fallback_strategy,
                context,
                "low_consensus",
                agents_launched,
                red_flagged_count,
                shape_violations_count,
                projected_cost_cents,
                cancelled_count,
                cancelled_tokens,
                elapsed_seconds,
            )

        # 3. Try top vote
        result = self.resolve_with_top_vote(
            aggregator,
            agents_launched,
            red_flagged_count,
            shape_violations_count,
            projected_cost_cents,
            cancelled_count,
            cancelled_tokens,
            elapsed_seconds,
        )
        if result:
            return result

        # 4. No votes at all - error
        msg = (
            f"Voting failed: {agents_launched} agents launched, "
            f"{red_flagged_count} red-flagged, {shape_violations_count} shape violations, "
            "no valid votes received"
        )
        raise RuntimeError(msg)
