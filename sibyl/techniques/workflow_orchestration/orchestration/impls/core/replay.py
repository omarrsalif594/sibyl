"""Replay engine for deterministic workflow replay."""

import logging
from typing import Any

from sibyl.core.infrastructure.state import StateFacade

from .base import MainOrchestrator
from .context import ContextEnvelope

logger = logging.getLogger(__name__)


class ReplayEngine:
    """Engine for replaying workflows from checkpoints.

    Modes:
    - "reuse": Reuse stored responses (deterministic)
    - "recompute": Re-execute LLM calls (verify determinism)
    """

    def __init__(self, state_store: StateFacade) -> None:
        """Initialize replay engine.

        Args:
            state_store: State store for loading history
        """
        self.state = state_store

    async def replay(
        self,
        conversation_id: str,
        from_phase: str,
        mode: str = "reuse",
        orchestrator: MainOrchestrator | None = None,
    ) -> dict[str, Any]:
        """Replay workflow from checkpoint.

        Args:
            conversation_id: Conversation to replay
            from_phase: Phase to resume from
            mode: "reuse" or "recompute"
            orchestrator: Orchestrator instance (required for recompute)

        Returns:
            Replay results dict

        Raises:
            ValueError: If mode invalid or orchestrator missing for recompute
            RuntimeError: If conversation or checkpoint not found
        """
        logger.info(
            "Replaying conversation %s from phase %s (mode=%s)", conversation_id, from_phase, mode
        )

        if mode not in ("reuse", "recompute"):
            msg = f"Invalid replay mode: {mode}"
            raise ValueError(msg)

        if mode == "recompute" and orchestrator is None:
            msg = "Orchestrator required for recompute mode"
            raise ValueError(msg)

        # Load conversation
        conversation = await self.state.get_conversation(conversation_id)
        if not conversation:
            msg = f"Conversation not found: {conversation_id}"
            raise RuntimeError(msg)

        # Load checkpoints
        checkpoints = await self._load_checkpoints(conversation_id)

        # Find target checkpoint
        target_checkpoint = None
        for checkpoint in checkpoints:
            if checkpoint["phase"] == from_phase:
                target_checkpoint = checkpoint
                break

        if not target_checkpoint:
            msg = f"Checkpoint not found for phase: {from_phase}"
            raise RuntimeError(msg)

        # Load context at checkpoint
        target_checkpoint["context_hash"]
        # TODO: Load context from hash (need context storage)

        if mode == "reuse":
            return await self._replay_reuse(
                conversation_id, from_phase, checkpoints, target_checkpoint
            )
        return await self._replay_recompute(
            conversation_id,
            from_phase,
            checkpoints,
            target_checkpoint,
            orchestrator,
        )

    async def _replay_reuse(
        self,
        conversation_id: str,
        from_phase: str,
        checkpoints: list[dict[str, Any]],
        target_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        """Replay by reusing stored responses.

        Args:
            conversation_id: Conversation ID
            from_phase: Starting phase
            checkpoints: All checkpoints
            target_checkpoint: Starting checkpoint

        Returns:
            Replay results
        """
        logger.info("Reuse mode: Loading stored responses from phase %s", from_phase)

        # Get all subagent calls after this checkpoint
        subagent_calls = await self.state.query_subagent_calls(conversation_id=conversation_id)

        # Filter calls from target phase onwards
        target_phase_num = target_checkpoint["phase_number"]
        relevant_calls = [
            call
            for call in subagent_calls
            if self._get_phase_number(call["phase"], checkpoints) >= target_phase_num
        ]

        logger.info("Found %s subagent calls to replay", len(relevant_calls))

        # Reconstruct results from stored calls
        results = {}
        for call in relevant_calls:
            phase = call["phase"]
            if phase not in results:
                results[phase] = []

            results[phase].append(
                {
                    "call_id": call["id"],
                    "agent_type": call["agent_type"],
                    "response_ref": call["response_ref"],
                    "tokens_used": call["tokens_in_actual"] + call["tokens_out_actual"],
                    "finish_reason": call["finish_reason"],
                }
            )

        return {
            "mode": "reuse",
            "conversation_id": conversation_id,
            "from_phase": from_phase,
            "results": results,
            "total_calls_replayed": len(relevant_calls),
        }

    async def _replay_recompute(
        self,
        conversation_id: str,
        from_phase: str,
        checkpoints: list[dict[str, Any]],
        target_checkpoint: dict[str, Any],
        orchestrator: MainOrchestrator,
    ) -> dict[str, Any]:
        """Replay by recomputing LLM calls.

        Args:
            conversation_id: Conversation ID
            from_phase: Starting phase
            checkpoints: All checkpoints
            target_checkpoint: Starting checkpoint
            orchestrator: Orchestrator to execute

        Returns:
            Replay results with diffs
        """
        logger.info("Recompute mode: Re-executing from phase %s", from_phase)

        # Get original calls
        original_calls = await self.state.query_subagent_calls(conversation_id=conversation_id)

        # Get phases to re-execute
        target_phase_num = target_checkpoint["phase_number"]
        remaining_phases = [
            cp["phase"] for cp in checkpoints if cp["phase_number"] >= target_phase_num
        ]

        logger.info("Re-executing phases: %s", remaining_phases)

        # TODO: Load context envelope from checkpoint
        # For now, create empty context
        context = ContextEnvelope()

        # Create new conversation ID for replay
        replay_conversation_id = f"{conversation_id}_replay"

        # Execute phases
        replay_results = await orchestrator.execute(
            conversation_id=replay_conversation_id,
            initial_context=context,
            phases=remaining_phases,
        )

        # Get new calls
        new_calls = await self.state.query_subagent_calls(conversation_id=replay_conversation_id)

        # Compare outputs
        differ = ReplayDiffer()
        diffs = differ.compare_calls(original_calls, new_calls)

        return {
            "mode": "recompute",
            "conversation_id": conversation_id,
            "replay_conversation_id": replay_conversation_id,
            "from_phase": from_phase,
            "results": replay_results,
            "diffs": diffs,
            "total_calls_original": len(original_calls),
            "total_calls_new": len(new_calls),
        }

    async def _load_checkpoints(self, conversation_id: str) -> list[dict[str, Any]]:
        """Load all checkpoints for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of checkpoint dicts (sorted by phase_number)
        """
        # Query checkpoints from state store
        return await self.state._writer.query_async(
            "SELECT * FROM phase_checkpoints WHERE conversation_id = ? ORDER BY phase_number",
            (conversation_id,),
        )

    def _get_phase_number(self, phase_name: str, checkpoints: list[dict[str, Any]]) -> int:
        """Get phase number for a phase name.

        Args:
            phase_name: Phase name
            checkpoints: List of checkpoints

        Returns:
            Phase number
        """
        for checkpoint in checkpoints:
            if checkpoint["phase"] == phase_name:
                return checkpoint["phase_number"]
        return 0


class ReplayDiffer:
    """Compare outputs between original and replayed calls."""

    def compare_calls(
        self, original_calls: list[dict[str, Any]], new_calls: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compare original and new subagent calls.

        Args:
            original_calls: Original calls
            new_calls: New (replayed) calls

        Returns:
            Diff dict with:
            - identical_count: Number of identical responses
            - different_count: Number of different responses
            - diffs: List of diffs
        """
        identical = 0
        different = 0
        diffs = []

        # Match calls by call_key (idempotent key)
        original_by_key = {call["call_key"]: call for call in original_calls}
        new_by_key = {call["call_key"]: call for call in new_calls}

        # Compare matched calls
        for call_key in original_by_key:
            if call_key in new_by_key:
                original = original_by_key[call_key]
                new = new_by_key[call_key]

                if self._are_responses_identical(original, new):
                    identical += 1
                else:
                    different += 1
                    diffs.append(
                        {
                            "call_key": call_key,
                            "agent_type": original["agent_type"],
                            "original_response_ref": original.get("response_ref"),
                            "new_response_ref": new.get("response_ref"),
                            "original_tokens": original.get("tokens_in_actual", 0)
                            + original.get("tokens_out_actual", 0),
                            "new_tokens": new.get("tokens_in_actual", 0)
                            + new.get("tokens_out_actual", 0),
                        }
                    )

        logger.info(
            "Replay diff: %s identical, %s different, %s diffs", identical, different, len(diffs)
        )

        return {
            "identical_count": identical,
            "different_count": different,
            "diffs": diffs,
        }

    def _are_responses_identical(self, call1: dict[str, Any], call2: dict[str, Any]) -> bool:
        """Check if two calls have identical responses.

        Args:
            call1: First call
            call2: Second call

        Returns:
            True if responses are identical
        """
        # Compare response refs (SHA256 hashes)
        return call1.get("response_ref") == call2.get("response_ref")


def verify_replay_determinism(diffs: dict[str, Any]) -> bool:
    """Verify if replay was deterministic.

    Args:
        diffs: Diffs from ReplayDiffer

    Returns:
        True if deterministic (no diffs), False otherwise
    """
    return diffs["different_count"] == 0
