"""
Lightweight Sibyl facade used in operational scripts and feature-flag tests.

This class intentionally keeps behavior minimal: it selects which technique
would be used based on feature flags and returns a small dictionary describing
the decision. The goal is to make rollback and feature-flag tests deterministic
without pulling in heavier dependencies.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import warnings
from typing import Any

from sibyl.core.feature_flags import FeatureFlags


class Sibyl:
    """
    Facade exposing fix_sql and session helpers with feature-flag routing.

    By default, this attempts to invoke the real consensus/quorum pipelines
    but will gracefully fall back to a stubbed response if dependencies are
    unavailable in the current environment (e.g., tests without provider creds).
    """

    def __init__(
        self,
        use_real_pipeline: bool = True,
        global_config: dict[str, Any] | None = None,
        consensus_config: dict[str, Any] | None = None,
        quorum_config: dict[str, Any] | None = None,
    ) -> None:
        self.use_real_pipeline = use_real_pipeline
        self.global_config = self._merge_env_config("SIBYL_GLOBAL_CONFIG", global_config)
        self.consensus_config = self._merge_env_config("SIBYL_CONSENSUS_CONFIG", consensus_config)
        self.quorum_config = self._merge_env_config("SIBYL_QUORUM_CONFIG", quorum_config)

    def fix_sql(
        self,
        query: str,
        user_id: int | None = None,
        *,
        error_message: str | None = None,
        model_name: str = "default_model",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Select a technique based on feature flags and run the corresponding pipeline.

        Args:
            query: SQL string (not executed here)
            user_id: Optional user identifier to drive rollout bucketing
            error_message: Optional error text to pass to pipelines
            model_name: Model name for quorum pipeline
            context: Optional context dict forwarded to consensus
        """
        choice = FeatureFlags.choose_technique(user_id=user_id)
        technique_used = choice.technique

        if not choice.enabled:
            msg = "No techniques are enabled via feature flags"
            raise RuntimeError(msg)

        payload: dict[str, Any]
        error: Exception | None = None

        if self.use_real_pipeline:
            try:
                if technique_used == "consensus":
                    payload = self._run_consensus(
                        query=query,
                        error_message=error_message,
                        context=context,
                    )
                else:
                    payload = self._run_quorum(
                        query=query,
                        error_message=error_message,
                        model_name=model_name,
                    )
            except Exception as exc:  # pragma: no cover - defensive fallback
                error = exc
                # Attempt quorum fallback if consensus failed and quorum is enabled
                if technique_used == "consensus" and FeatureFlags.TECHNIQUES_ENABLED.get(
                    "quorum", False
                ):
                    try:
                        payload = self._run_quorum(
                            query=query,
                            error_message=error_message,
                            model_name=model_name,
                        )
                        technique_used = "quorum"
                    except Exception:
                        payload = self._stub_response(query, technique_used, choice, error)
                else:
                    payload = self._stub_response(query, technique_used, choice, error)
        else:
            payload = self._stub_response(query, technique_used, choice)

        # Ensure metadata is present
        payload.setdefault("technique_used", technique_used)
        payload.setdefault("rollout_bucket", choice.rollout_bucket)
        payload.setdefault("enabled", choice.enabled)
        payload.setdefault("query", query)
        if error:
            payload.setdefault("error", str(error))

        return payload

    def long_operation(self, duration: float = 1.0) -> dict[str, str]:
        """
        Simulate a long-running operation. Used to verify that mid-flight flag
        toggles do not break ongoing work.
        """
        time.sleep(duration)
        return {"status": "ok"}

    def list_sessions(self) -> list:
        """Placeholder session listing for integration with rollback scripts."""
        return []

    def _run_consensus(
        self,
        *,
        query: str,
        error_message: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Execute the consensus technique pipeline."""
        from sibyl.techniques.ai_generation.consensus import ConsensusTechnique

        technique = ConsensusTechnique()
        input_data = {
            "error_message": error_message or "Autogenerated error from Sibyl.fix_sql",
            "sql": query,
            "context": context or {},
            "model_name": "default",
        }
        result = technique.execute(
            input_data=input_data,
            subtechnique="quorum_voting",
            implementation="five_agent",
            config=self.consensus_config or None,
            global_config=self.global_config,
        )
        return self._normalize_result(result, "consensus")

    def _run_quorum(
        self,
        *,
        query: str,
        error_message: str | None,
        model_name: str,
    ) -> dict[str, Any]:
        """Execute the quorum pipeline (async) synchronously."""
        from sibyl.techniques.ai_generation.consensus.impls.core.pipeline import (
            QuorumPipeline,
            QuorumPipelineConfig,
        )
        from sibyl.techniques.ai_generation.consensus.impls.core.protocol import VotingPolicy

        policy_overrides = (
            self.quorum_config.get("voting_policy", {})
            if isinstance(self.quorum_config, dict)
            else {}
        )
        policy = VotingPolicy(**policy_overrides)

        config_kwargs = {
            "enable_red_flagging": self.quorum_config.get("enable_red_flagging", True),
            "enable_fallbacks": self.quorum_config.get("enable_fallbacks", True),
            "checkpoint_per_step": self.quorum_config.get("checkpoint_per_step", True),
            "max_cost_per_pipeline_cents": self.quorum_config.get(
                "max_cost_per_pipeline_cents", 5.0
            ),
            "per_step_cost_ceilings": self.quorum_config.get("per_step_cost_ceilings", None)
            or {
                "diagnosis": 0.5,
                "strategy": 0.4,
                "location": 0.8,
                "generation": 1.5,
                "validation": 0.3,
            },
        }

        config = QuorumPipelineConfig(voting_policy=policy, **config_kwargs)
        pipeline = QuorumPipeline()

        coroutine = pipeline.execute(
            error_message=error_message or "Autogenerated error from Sibyl.fix_sql",
            model_name=model_name,
            sql=query,
            config=config,
        )
        try:
            state = asyncio.run(coroutine)
        except RuntimeError:
            # If an event loop is already running, bubble up so the caller can fallback.
            raise
        return self._normalize_result(state, "quorum")

    def _normalize_result(self, result: Any, technique: str) -> dict[str, Any]:
        """Normalize pipeline outputs into a dict with technique metadata."""
        if hasattr(result, "dict"):
            payload = result.dict()
        elif isinstance(result, dict):
            payload = dict(result)
        else:
            payload = {"result": result}

        payload.setdefault("technique_used", technique)
        return payload

    def _stub_response(
        self, query: str, technique: str, choice: Any, error: Exception | None = None
    ) -> dict[str, Any]:
        """Fallback response when pipelines are unavailable."""
        payload = {
            "query": query,
            "technique_used": technique,
            "rollout_bucket": choice.rollout_bucket,
            "enabled": choice.enabled,
            "fallback": True,
        }
        if error:
            payload["error"] = str(error)
        return payload

    def _merge_env_config(self, env_var: str, override: dict[str, Any] | None) -> dict[str, Any]:
        """
        Merge JSON config from environment with a provided override.

        Env var, if present, must be a JSON object. Overrides take precedence.
        """
        base: dict[str, Any] = {}
        raw = os.getenv(env_var)
        if raw:
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    base.update(loaded)
            except json.JSONDecodeError:
                warnings.warn(f"Ignoring invalid JSON in {env_var}", stacklevel=2)

        if override:
            base.update(override)
        return base
