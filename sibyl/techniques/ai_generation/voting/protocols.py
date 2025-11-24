"""
Protocols and Types for Voting Technique

Defines the interfaces for voting and aggregation strategies.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

# Type variable for vote types
VoteT = TypeVar("VoteT")


@dataclass
class Vote:
    """Represents a single vote"""

    value: Any
    confidence: float = 1.0
    voter_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class VotingResult:
    """Result of a voting process"""

    winner: Any
    votes: list[Vote]
    confidence: float
    vote_distribution: dict[Any, int]
    metadata: dict[str, Any] | None = None


class VotingStrategy(Protocol):
    """
    Protocol for voting strategies.

    Each strategy aggregates multiple votes to produce a consensus result.
    """

    @abstractmethod
    def aggregate(
        self, votes: list[Vote], threshold: float | None = None, **kwargs
    ) -> VotingResult:
        """
        Aggregate votes to produce a result.

        Args:
            votes: List of votes to aggregate
            threshold: Optional threshold for consensus
            **kwargs: Additional aggregation parameters

        Returns:
            Voting result with winner and metadata
        """
        ...

    @abstractmethod
    def validate_votes(self, votes: list[Vote]) -> bool:
        """
        Validate that votes are compatible with this strategy.

        Args:
            votes: Votes to validate

        Returns:
            True if votes are valid
        """
        ...
