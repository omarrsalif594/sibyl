"""
Default Threshold Voting Implementation

Implements k-voting with configurable thresholds and confidence requirements.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class VoteResult:
    """Result of a voting round."""

    decision: Any
    vote_count: int
    total_votes: int
    avg_confidence: float
    consensus_reached: bool
    fallback_used: bool


class ThresholdVotingImplementation:
    """
    Default implementation of threshold voting.

    Uses k-voting where at least k agents must agree on a decision
    with a minimum average confidence threshold.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize threshold voting.

        Args:
            config: Voting configuration with parameters like:
                - initial_n: Initial number of agents
                - k_threshold: Votes needed for consensus
                - min_avg_confidence: Minimum average confidence
        """
        self.config = config
        self.initial_n = config.get("initial_n", 3)
        self.max_n = config.get("max_n", 5)
        self.k_threshold = config.get("k_threshold", 3)
        self.min_k_fallback = config.get("min_k_fallback", 2)
        self.min_avg_confidence = config.get("min_avg_confidence", 0.6)
        self.split_vote_threshold = config.get("split_vote_threshold", 0.4)

    def execute(self, votes: list[dict[str, Any]], **kwargs) -> VoteResult:
        """
        Execute threshold voting on a list of votes.

        Args:
            votes: List of vote dictionaries with 'decision' and 'confidence'
            **kwargs: Additional parameters

        Returns:
            VoteResult with voting outcome
        """
        if not votes:
            return VoteResult(
                decision=None,
                vote_count=0,
                total_votes=0,
                avg_confidence=0.0,
                consensus_reached=False,
                fallback_used=True,
            )

        # Count votes for each decision
        decision_votes: dict[Any, list[float]] = {}
        for vote in votes:
            decision = vote.get("decision")
            confidence = vote.get("confidence", 1.0)

            if decision not in decision_votes:
                decision_votes[decision] = []
            decision_votes[decision].append(confidence)

        # Find decision with most votes
        top_decision = None
        max_votes = 0
        top_confidences = []

        for decision, confidences in decision_votes.items():
            vote_count = len(confidences)
            if vote_count > max_votes:
                max_votes = vote_count
                top_decision = decision
                top_confidences = confidences

        # Calculate average confidence
        avg_confidence = sum(top_confidences) / len(top_confidences) if top_confidences else 0.0

        # Check if consensus reached
        consensus_reached = (
            max_votes >= self.k_threshold and avg_confidence >= self.min_avg_confidence
        )

        # Check if fallback used
        fallback_used = max_votes < self.k_threshold and max_votes >= self.min_k_fallback

        return VoteResult(
            decision=top_decision,
            vote_count=max_votes,
            total_votes=len(votes),
            avg_confidence=avg_confidence,
            consensus_reached=consensus_reached,
            fallback_used=fallback_used,
        )

    def check_split_vote(self, votes: list[dict[str, Any]]) -> bool:
        """
        Check if vote is split (multiple options with significant support).

        Args:
            votes: List of votes

        Returns:
            True if split vote detected
        """
        if not votes:
            return False

        # Count votes for each decision
        decision_counts: dict[Any, int] = {}
        for vote in votes:
            decision = vote.get("decision")
            decision_counts[decision] = decision_counts.get(decision, 0) + 1

        total_votes = len(votes)
        significant_options = sum(
            1
            for count in decision_counts.values()
            if count / total_votes >= self.split_vote_threshold
        )

        return significant_options >= 2

    def __repr__(self) -> str:
        return (
            f"ThresholdVotingImplementation("
            f"k={self.k_threshold}, "
            f"min_confidence={self.min_avg_confidence})"
        )
