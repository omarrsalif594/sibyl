"""
Vote Aggregator for Quorum Engine

Aggregates votes from multiple agents with confidence weighting and tie-breaking.
"""

import json
from typing import Generic

from .protocol import ConsensusResult, DecisionT, VotingPolicy


class VoteAggregator(Generic[DecisionT]):
    """
    Aggregates votes from agents and determines consensus.

    Features:
    - Confidence-weighted voting
    - Tie-breaking by confidence sum
    - Consensus detection with minimum confidence requirement
    """

    def __init__(self, policy: VotingPolicy) -> None:
        """
        Args:
            policy: Voting policy with k thresholds and confidence requirements
        """
        self.policy = policy
        # votes: decision_key → [(decision, confidence, agent_id)]
        self.votes: dict[str, list[tuple[DecisionT, float, str]]] = {}
        self.vote_order: list[tuple[str, DecisionT, float, str]] = []  # For tie-breaking

    def add_vote(
        self,
        decision: DecisionT,
        confidence: float,
        agent_id: str,
    ) -> None:
        """
        Add a vote to the aggregator.

        Args:
            decision: Decision instance (must be JSON-serializable)
            confidence: Confidence score (0.0-1.0)
            agent_id: Identifier for the agent that voted
        """
        # Serialize decision for vote counting
        key = self._serialize_decision(decision)

        if key not in self.votes:
            self.votes[key] = []

        self.votes[key].append((decision, confidence, agent_id))
        self.vote_order.append((key, decision, confidence, agent_id))

    def check_consensus_with_confidence(
        self,
        k: int,
        min_avg_confidence: float,
    ) -> ConsensusResult[DecisionT] | None:
        """
        Check if any decision has ≥k votes with average confidence ≥ threshold.

        Args:
            k: Minimum votes needed
            min_avg_confidence: Minimum average confidence (0.0-1.0)

        Returns:
            ConsensusResult if consensus found, None otherwise
        """
        for _key, vote_list in self.votes.items():
            if len(vote_list) >= k:
                # Calculate average confidence
                avg_conf = sum(v[1] for v in vote_list) / len(vote_list)

                if avg_conf >= min_avg_confidence:
                    return ConsensusResult(
                        decision=vote_list[0][0],  # First instance of this decision
                        k=len(vote_list),
                        avg_confidence=avg_conf,
                    )

        return None

    def get_top_vote_with_tiebreak(self) -> tuple[DecisionT, int, float] | None:
        """
        Get the leading decision with tie-breaking.

        Tie-breaking rules (in order):
        1. Most votes
        2. Highest confidence-weighted sum
        3. First vote received (temporal tie-break)

        Returns:
            Tuple of (decision, vote_count, avg_confidence) or None if no votes
        """
        if not self.votes:
            return None

        # Build ranking: (decision, count, confidence_sum, avg_confidence, first_vote_index)
        ranked = []
        for key, vote_list in self.votes.items():
            count = len(vote_list)
            confidence_sum = sum(v[1] for v in vote_list)
            avg_confidence = confidence_sum / count

            # Find first vote index for temporal tie-breaking
            first_vote_index = next(i for i, (k, _, _, _) in enumerate(self.vote_order) if k == key)

            ranked.append(
                (
                    vote_list[0][0],  # decision
                    count,
                    confidence_sum,
                    avg_confidence,
                    first_vote_index,
                )
            )

        # Sort: count desc, then confidence_sum desc, then first_vote_index asc
        ranked.sort(key=lambda x: (x[1], x[2], -x[4]), reverse=True)

        top = ranked[0]
        return top[0], top[1], top[3]

    def get_vote_distribution(self) -> dict[str, int]:
        """
        Get vote distribution as {serialized_decision: count}.

        Returns:
            Dictionary mapping decision keys to vote counts
        """
        return {key: len(votes) for key, votes in self.votes.items()}

    def get_detailed_distribution(self) -> dict[str, dict]:
        """
        Get detailed vote distribution with confidence stats.

        Returns:
            Dictionary with vote counts, confidence stats, and agent IDs per decision
        """
        result = {}
        for key, vote_list in self.votes.items():
            confidences = [v[1] for v in vote_list]
            result[key] = {
                "count": len(vote_list),
                "avg_confidence": sum(confidences) / len(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences),
                "agent_ids": [v[2] for v in vote_list],
            }
        return result

    def get_consensus_strength(self, decision: DecisionT, total_agents: int) -> float:
        """
        Calculate consensus strength (k / n) for a specific decision.

        Args:
            decision: The decision to check
            total_agents: Total number of agents that voted

        Returns:
            Consensus strength (0.0-1.0)
        """
        key = self._serialize_decision(decision)
        vote_count = len(self.votes.get(key, []))
        return vote_count / total_agents if total_agents > 0 else 0.0

    def has_split_vote(self, threshold: float = 0.4) -> bool:
        """
        Check if vote is split (multiple options with significant support).

        Args:
            threshold: Minimum vote share to be considered "significant" (default 0.4 = 40%)

        Returns:
            True if multiple decisions have >= threshold vote share
        """
        if not self.votes:
            return False

        total_votes = sum(len(votes) for votes in self.votes.values())
        significant_options = sum(
            1 for votes in self.votes.values() if len(votes) / total_votes >= threshold
        )

        return significant_options >= 2

    def _serialize_decision(self, decision: DecisionT) -> str:
        """
        Serialize decision to string for vote counting.

        Uses JSON with sorted keys for deterministic comparison.
        """
        try:
            # Use pydantic's model_dump for consistent serialization
            data = decision.model_dump(exclude={"provenance"})  # Exclude provenance
            return json.dumps(data, sort_keys=True)
        except Exception:
            # Fallback to string representation
            return str(decision)

    def reset(self) -> None:
        """Clear all votes (for reuse in new voting round)"""
        self.votes.clear()
        self.vote_order.clear()

    def __len__(self) -> int:
        """Return total number of votes cast"""
        return sum(len(votes) for votes in self.votes.values())

    def __repr__(self) -> str:
        """String representation for debugging"""
        distribution = self.get_vote_distribution()
        return f"VoteAggregator(votes={len(self)}, distribution={distribution})"


class VoteAggregatorMetrics:
    """Track vote aggregator performance"""

    def __init__(self) -> None:
        self.total_rounds = 0
        self.consensus_reached = 0
        self.fallback_used = 0
        self.split_votes = 0
        self.avg_consensus_strength_sum = 0.0

    def record_round(
        self,
        consensus_reached: bool,
        fallback_used: bool,
        split_vote: bool,
        consensus_strength: float,
    ) -> None:
        """Record statistics for a voting round"""
        self.total_rounds += 1
        if consensus_reached:
            self.consensus_reached += 1
        if fallback_used:
            self.fallback_used += 1
        if split_vote:
            self.split_votes += 1
        self.avg_consensus_strength_sum += consensus_strength

    def get_consensus_rate(self) -> float:
        """Get rate of consensus achievement (0.0-1.0)"""
        if self.total_rounds == 0:
            return 0.0
        return self.consensus_reached / self.total_rounds

    def get_fallback_rate(self) -> float:
        """Get rate of fallback invocation (0.0-1.0)"""
        if self.total_rounds == 0:
            return 0.0
        return self.fallback_used / self.total_rounds

    def get_split_vote_rate(self) -> float:
        """Get rate of split votes (0.0-1.0)"""
        if self.total_rounds == 0:
            return 0.0
        return self.split_votes / self.total_rounds

    def get_avg_consensus_strength(self) -> float:
        """Get average consensus strength across rounds"""
        if self.total_rounds == 0:
            return 0.0
        return self.avg_consensus_strength_sum / self.total_rounds

    def get_summary(self) -> dict:
        """Get summary statistics"""
        return {
            "total_rounds": self.total_rounds,
            "consensus_rate": self.get_consensus_rate(),
            "fallback_rate": self.get_fallback_rate(),
            "split_vote_rate": self.get_split_vote_rate(),
            "avg_consensus_strength": self.get_avg_consensus_strength(),
        }
