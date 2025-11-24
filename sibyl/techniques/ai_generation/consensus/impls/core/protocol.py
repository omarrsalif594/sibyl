"""
Protocols and Types for Quorum Engine

Defines the interfaces for atomic agents, voting, and fallback strategies.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

# Import VotingTechnique for configuration (eliminates hardcoded values)
from sibyl.techniques.ai_generation.voting import VotingTechnique

# Type variable for decision types
DecisionT = TypeVar("DecisionT", bound=BaseModel)


# ============================================================================
# Atomic Agent Protocol
# ============================================================================


@runtime_checkable
class AtomicAgent(Protocol, Generic[DecisionT]):
    """
    Protocol for atomic decision agents.

    Each agent makes exactly ONE decision with minimal context.
    Must return a contract-compliant output.
    """

    @abstractmethod
    async def decide(
        self,
        context: dict[str, Any],
        timeout: float = 5.0,
    ) -> DecisionT:
        """
        Make a single atomic decision.

        Args:
            context: Minimal context needed for this decision
            timeout: Maximum time to spend on decision (seconds)

        Returns:
            Decision instance conforming to the contract

        Raises:
            TimeoutError: If decision takes longer than timeout
            ShapeViolation: If output doesn't conform to contract
        """
        ...

    @abstractmethod
    def get_decision_type(self) -> type[DecisionT]:
        """Return the decision contract type (Pydantic model class)"""
        ...

    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """
        Minimum confidence to not auto-red-flag.

        Default: 0.3 (outputs with confidence < 0.3 are automatically flagged)
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the LLM model used by this agent"""
        ...


# ============================================================================
# Voting Types
# ============================================================================


@dataclass(frozen=True)
class VotingPolicy:
    """
    Configuration for voting behavior.

    Configuration loaded from voting technique (eliminates hardcoded values).
    Defaults are loaded from VotingTechnique but can be overridden at instantiation.
    """

    # Configuration loaded from voting technique (eliminates hardcoded values)
    initial_n: int = 3  # Start with N agents
    max_n: int = 5  # Escalate up to MAX_N if needed
    k_threshold: int = 3  # Votes needed for consensus
    min_k_fallback: int = 2  # Degrade to K_fallback if timeout
    timeout_seconds: float = 10.0  # Total voting timeout
    per_agent_timeout: float = 5.0  # Individual agent timeout
    red_flag_escalation_threshold: float = 0.3  # Spawn more if >30% flagged
    min_avg_confidence: float = 0.6  # k votes must average ≥ this
    cost_ceiling_cents: float = 2.0  # Per-step cost ceiling
    enable_early_commit: bool = True  # Cancel agents on early consensus

    @classmethod
    def from_technique(cls, **overrides) -> "VotingPolicy":
        """
        Create VotingPolicy from VotingTechnique configuration.

        Configuration loaded from voting technique (eliminates hardcoded values).

        Args:
            **overrides: Optional overrides for specific parameters

        Returns:
            VotingPolicy with technique-sourced defaults
        """
        technique = VotingTechnique()
        config = technique.get_voting_policy()

        # Merge technique config with any overrides
        config.update(overrides)

        return cls(
            initial_n=config.get("initial_n", 3),
            max_n=config.get("max_n", 5),
            k_threshold=config.get("k_threshold", 3),
            min_k_fallback=config.get("min_k_fallback", 2),
            timeout_seconds=config.get("timeout_seconds", 10.0),
            per_agent_timeout=config.get("per_agent_timeout", 5.0),
            red_flag_escalation_threshold=config.get("red_flag_escalation_threshold", 0.3),
            min_avg_confidence=config.get("min_avg_confidence", 0.6),
            cost_ceiling_cents=config.get("cost_ceiling_cents", 2.0),
            enable_early_commit=config.get("enable_early_commit", True),
        )


@dataclass
class VotingResult(Generic[DecisionT]):
    """Result of a voting round"""

    decision: DecisionT  # Winning decision
    vote_distribution: dict[str, int]  # Serialized decision → count
    consensus_time_seconds: float  # Time to reach consensus
    agents_used: int  # How many agents actually responded
    red_flagged_count: int  # Outputs that were red-flagged
    shape_violations_count: int  # Outputs that violated schema
    consensus_strength: float  # k / n (higher = stronger consensus)
    avg_confidence: float  # Average confidence of winning votes
    fallback_used: bool  # Whether deterministic fallback was invoked
    fallback_reason: str | None = None  # timeout | low_consensus | cost_ceiling
    projected_cost_cents: float = 0.0  # Estimated cost of this round
    cancelled_agents_count: int = 0  # Agents cancelled after early consensus
    cancelled_saved_tokens: int = 0  # Tokens saved by cancellation


@dataclass
class ConsensusResult(Generic[DecisionT]):
    """Intermediate result when checking for consensus"""

    decision: DecisionT
    k: int  # Number of votes
    avg_confidence: float  # Average confidence


# ============================================================================
# Fallback Strategy Protocol
# ============================================================================


@runtime_checkable
class FallbackStrategy(Protocol, Generic[DecisionT]):
    """
    Protocol for deterministic fallback when voting fails.

    Each decision type has a fallback strategy that produces a
    low-confidence decision when consensus cannot be reached.
    """

    @abstractmethod
    def apply(
        self,
        votes: list[DecisionT],
        context: dict[str, Any],
        reason: str,
    ) -> "FallbackResult[DecisionT]":
        """
        Apply fallback strategy.

        Args:
            votes: All votes received (may be empty)
            context: Decision context
            reason: Why fallback was triggered (timeout, low_consensus, cost_ceiling)

        Returns:
            FallbackResult with low-confidence decision
        """
        ...


@dataclass
class FallbackResult(Generic[DecisionT]):
    """Result of applying a fallback strategy"""

    decision: DecisionT
    fallback_type: str  # Name of strategy used (e.g., "error_classifier", "top_vote", "default")
    reason: str  # Why fallback was triggered
    confidence: float  # Always low (0.2-0.5)


# ============================================================================
# Red-Flag Types
# ============================================================================


@dataclass
class RedFlagResult:
    """Result of red-flag detection"""

    is_flagged: bool
    reason: str | None = None
    severity: str = "structural"  # structural | domain | heuristic


# ============================================================================
# Pipeline Types
# ============================================================================


@dataclass
class StepTrace:
    """Trace of a single pipeline step"""

    step: str  # diagnosis | strategy | location | fix | validation
    decision: dict  # Serialized decision
    vote_distribution: dict[str, int]
    consensus_time_seconds: float
    agents_used: int
    red_flagged_count: int
    consensus_strength: float
    avg_confidence: float
    fallback_used: bool
    fallback_reason: str | None = None
    cost_cents: float = 0.0
