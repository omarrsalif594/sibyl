"""Context management with 3-tier hashing and optimization."""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from sibyl.core.contracts.providers import LLMProvider

logger = logging.getLogger(__name__)


# Module-level config cache
_CONTEXT_CONFIG: dict[str, Any] | None = None


def _get_context_config() -> dict[str, Any]:
    """Get cached context management config."""
    global _CONTEXT_CONFIG
    if _CONTEXT_CONFIG is None:
        config_path = Path(__file__).parent / "context_config.yaml"
        try:
            if config_path.exists():
                with open(config_path) as f:
                    _CONTEXT_CONFIG = yaml.safe_load(f) or {}
            else:
                _CONTEXT_CONFIG = {}
        except Exception as e:
            logger.warning("Failed to load context config: %s", e)
            _CONTEXT_CONFIG = {}

    return _CONTEXT_CONFIG


@dataclass
class ContextEnvelope:
    """Three-tier context structure with content-addressed hashing.

    Tier 1: Stable inputs (rarely change) - ExampleDomain models, schemas
    Tier 2: Dynamic observations (per phase) - compile outputs, errors
    Tier 3: Summaries (LLM/heuristic) - compressed context
    """

    # Tier 1: Stable inputs
    stable_inputs: dict[str, Any] = field(default_factory=dict)
    stable_hash: str = field(default="")

    # Tier 2: Dynamic observations
    dynamic_observations: dict[str, Any] = field(default_factory=dict)
    dynamic_hash: str = field(default="")

    # Tier 3: Summaries
    summaries: dict[str, Any] = field(default_factory=dict)
    summary_version: str = field(default="1.0")
    summary_hash: str = field(default="")

    def __post_init__(self) -> None:
        """Compute hashes if not provided."""
        if not self.stable_hash:
            self.stable_hash = self._compute_hash(self.stable_inputs)
        if not self.dynamic_hash:
            self.dynamic_hash = self._compute_hash(self.dynamic_observations)
        if not self.summary_hash:
            self.summary_hash = self._compute_hash(self.summaries)

    @property
    def global_hash(self) -> str:
        """Combined hash of all tiers.

        Returns:
            SHA256 hex digest of all tier hashes
        """
        combined = f"{self.stable_hash}:{self.dynamic_hash}:{self.summary_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def slice_for_agent(self, agent_type: str, phase: str) -> dict[str, Any]:
        """Return only relevant context slice for an agent.

        Args:
            agent_type: Agent type ("sql_error_analyst", "type_validator", etc.)
            phase: Current phase ("compile", "test", "fix", etc.)

        Returns:
            Context slice dict with only relevant data
        """
        # Load agent-specific configuration
        config = _get_context_config()
        slicing_config = config.get("agent_context_slicing", {})
        agent_config = slicing_config.get(agent_type, slicing_config.get("default", {}))

        context_slice = {}

        # Include stable inputs if configured
        if agent_config.get("include_stable_inputs", True):
            context_slice["stable_inputs"] = self.stable_inputs

        # Include phase-specific observations if configured
        if agent_config.get("include_dynamic_observations", True):
            if phase in self.dynamic_observations:
                context_slice["observations"] = self.dynamic_observations[phase]
            else:
                context_slice["dynamic_observations"] = self.dynamic_observations

        # Include summaries if configured
        if agent_config.get("include_summaries", True):
            context_slice["summaries"] = self.summaries

        # Add specific fields if configured
        specific_fields = agent_config.get("specific_fields", [])
        for field in specific_fields:
            # Try to get from dynamic observations first, then stable inputs
            if field in self.dynamic_observations:
                context_slice[field] = self.dynamic_observations[field]
            elif field in self.stable_inputs:
                context_slice[field] = self.stable_inputs[field]
            # Also check nested phase observations
            elif phase in self.dynamic_observations and field in self.dynamic_observations[phase]:
                context_slice[field] = self.dynamic_observations[phase][field]

        return context_slice

    def update_observations(self, phase: str, observations: dict[str, Any]) -> None:
        """Update dynamic observations for a phase.

        Args:
            phase: Phase name
            observations: Observations dict
        """
        self.dynamic_observations[phase] = observations
        self.dynamic_hash = self._compute_hash(self.dynamic_observations)

    def update_summary(self, phase: str, summary: str) -> None:
        """Update summary for a phase.

        Args:
            phase: Phase name
            summary: Summary text
        """
        self.summaries[phase] = summary
        self.summary_hash = self._compute_hash(self.summaries)

    @staticmethod
    def _compute_hash(data: dict[str, Any]) -> str:
        """Compute SHA256 hash of dict.

        Args:
            data: Dict to hash

        Returns:
            SHA256 hex digest
        """
        # Canonical JSON (sorted keys)
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def to_cache_context(self) -> dict[str, Any]:
        """Convert to cache context dict for SummaryCache.compute_key().

        Returns:
            Dict with stable_hash, dynamic_hash, stable_inputs, dynamic_observations
        """
        return {
            "stable_hash": self.stable_hash,
            "dynamic_hash": self.dynamic_hash,
            "stable_inputs": self.stable_inputs,
            "dynamic_observations": self.dynamic_observations,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict.

        Returns:
            Dict representation
        """
        return {
            "stable_inputs": self.stable_inputs,
            "stable_hash": self.stable_hash,
            "dynamic_observations": self.dynamic_observations,
            "dynamic_hash": self.dynamic_hash,
            "summaries": self.summaries,
            "summary_version": self.summary_version,
            "summary_hash": self.summary_hash,
            "global_hash": self.global_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextEnvelope":
        """Deserialize from dict.

        Args:
            data: Dict representation

        Returns:
            ContextEnvelope instance
        """
        return cls(
            stable_inputs=data.get("stable_inputs", {}),
            stable_hash=data.get("stable_hash", ""),
            dynamic_observations=data.get("dynamic_observations", {}),
            dynamic_hash=data.get("dynamic_hash", ""),
            summaries=data.get("summaries", {}),
            summary_version=data.get("summary_version", "1.0"),
            summary_hash=data.get("summary_hash", ""),
        )


class ContextOptimizer:
    """Context optimization with delta compression and summarization.

    Enhanced with SummaryCache integration for idempotent, cache-aware summarization.
    """

    @property
    def SUMMARY_SCHEMA(self) -> dict[str, Any]:
        """Get summary schema from configuration."""
        config = _get_context_config()
        return config.get(
            "summary_schema",
            {
                "type": "object",
                "properties": {
                    "key_points": {"type": "array", "items": {"type": "string"}},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "decisions": {"type": "array", "items": {"type": "string"}},
                    "metrics": {"type": "object"},
                },
                "required": ["key_points"],
            },
        )

    def __init__(self, summary_cache: Any | None = None) -> None:
        """Initialize context optimizer.

        Args:
            summary_cache: Optional SummaryCache instance for caching summaries.
                          If None, caching is disabled (falls back to direct LLM calls).
        """
        self.summary_cache = summary_cache

        if summary_cache:
            logger.info("ContextOptimizer initialized with SummaryCache")
        else:
            logger.info("ContextOptimizer initialized without caching")

    def compute_delta(
        self, prev_envelope: ContextEnvelope, curr_envelope: ContextEnvelope
    ) -> dict[str, Any]:
        """Compute minimal delta between checkpoints.

        Args:
            prev_envelope: Previous context envelope
            curr_envelope: Current context envelope

        Returns:
            Delta dict with only changed data
        """
        delta = {}

        # Check if dynamic observations changed
        if prev_envelope.dynamic_hash != curr_envelope.dynamic_hash:
            delta["observations_delta"] = self._diff_dicts(
                prev_envelope.dynamic_observations, curr_envelope.dynamic_observations
            )

        # Check if summaries changed
        if prev_envelope.summary_hash != curr_envelope.summary_hash:
            delta["summaries_delta"] = self._diff_dicts(
                prev_envelope.summaries, curr_envelope.summaries
            )

        # Stable inputs shouldn't change, but check anyway
        if prev_envelope.stable_hash != curr_envelope.stable_hash:
            logger.warning("Stable inputs changed (unexpected)")
            delta["stable_inputs_changed"] = True

        return delta

    def _diff_dicts(self, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        """Compute diff between two dicts.

        Args:
            old: Old dict
            new: New dict

        Returns:
            Dict with added, modified, removed keys
        """
        diff = {"added": {}, "modified": {}, "removed": []}

        # Find added and modified
        for key, value in new.items():
            if key not in old:
                diff["added"][key] = value
            elif old[key] != value:
                diff["modified"][key] = value

        # Find removed
        for key in old:
            if key not in new:
                diff["removed"].append(key)

        return diff

    async def summarize(
        self,
        content: dict[str, Any],
        llm_provider: "LLMProvider",
        model: str = "claude-haiku-4",
        session_id: str | None = None,
        turn_id: int | None = None,
        summarize_threshold: float = 60.0,
        rotate_threshold: float = 70.0,
    ) -> str:
        """Structured summarization with schema and optional caching.

        If summary_cache is configured and session_id/turn_id are provided,
        this method will check the cache first before calling the LLM.

        Args:
            content: Content to summarize
            llm_provider: LLM provider for summarization
            model: Model to use (default: cheapest)
            session_id: Optional session ID for caching
            turn_id: Optional turn ID for caching
            summarize_threshold: Summarize threshold (for cache key)
            rotate_threshold: Rotate threshold (for cache key)

        Returns:
            Summary as JSON string
        """
        from sibyl.core.contracts.providers import CompletionOptions

        # Check cache if enabled
        if self.summary_cache and session_id and turn_id is not None:
            cache_key = self.summary_cache.compute_key(
                context=content,
                session_id=session_id,
                turn_id=turn_id,
                summarize_threshold=summarize_threshold,
                rotate_threshold=rotate_threshold,
            )

            # Try cache first
            cached_summary = await self.summary_cache.get(cache_key)
            if cached_summary:
                logger.info(
                    "Cache hit for summarization (session=%s, turn=%s)", session_id, turn_id
                )
                return json.dumps(cached_summary)

            logger.debug("Cache miss for summarization (session=%s, turn=%s)", session_id, turn_id)

        # Cache miss or caching disabled: call LLM
        logger.debug("Calling LLM for summarization (model=%s)", model)
        prompt = self._build_summary_prompt(content)

        # Call LLM with structured output
        result = await llm_provider.structured_complete(
            prompt, self.SUMMARY_SCHEMA, CompletionOptions(model=model, temperature=0.0)
        )

        summary_text = result["text"]
        summary_dict = json.loads(summary_text)

        # Store in cache if enabled
        if self.summary_cache and session_id and turn_id is not None:
            await self.summary_cache.set(
                key=cache_key,
                summary=summary_dict,
                session_id=session_id,
                turn_id=turn_id,
            )
            logger.debug("Cached summary (session=%s, turn=%s)", session_id, turn_id)

        return summary_text

    def _build_summary_prompt(self, content: dict[str, Any]) -> str:
        """Build summarization prompt.

        Args:
            content: Content to summarize

        Returns:
            Prompt string
        """
        # Load configuration
        config = _get_context_config()
        summ_config = config.get("summarization", {})

        # Get parameters from config
        template = summ_config.get("prompt_template", "")
        compression_target = summ_config.get("compression_target", "50%")
        truncation_limit = summ_config.get("content_truncation_limit", 2000)
        focus_areas_list = summ_config.get("focus_areas", [])

        # Format content
        content_str = json.dumps(content, indent=2)
        truncated_content = content_str[:truncation_limit]

        # Format focus areas
        focus_areas = "\n".join(f"{i + 1}. {area}" for i, area in enumerate(focus_areas_list))

        # Format schema
        schema_str = json.dumps(self.SUMMARY_SCHEMA, indent=2)

        # Use template if provided, otherwise fallback to hardcoded
        if template:
            return template.format(
                compression_target=compression_target,
                content=truncated_content,
                focus_areas=focus_areas,
                schema=schema_str,
            )
        # Fallback to original hardcoded prompt
        return f"""Summarize this context to ~{compression_target} of original length while preserving critical information:

{truncated_content}

Focus on:
{focus_areas}

Output JSON matching this schema:
{schema_str}
"""

    async def summarize_when_over_budget(
        self,
        context: ContextEnvelope,
        llm_provider: "LLMProvider",
        target_token_reduction: int,
        session_id: str | None = None,
        turn_id: int | None = None,
        summarize_threshold: float = 60.0,
        rotate_threshold: float = 70.0,
    ) -> ContextEnvelope:
        """Summarize context to fit budget with optional caching.

        Args:
            context: Current context envelope
            llm_provider: LLM provider for summarization
            target_token_reduction: Target token reduction
            session_id: Optional session ID for caching
            turn_id: Optional turn ID for caching
            summarize_threshold: Summarize threshold (for cache key)
            rotate_threshold: Rotate threshold (for cache key)

        Returns:
            New context envelope with compressed content
        """
        from sibyl.core.server.config import get_config
        from sibyl.techniques.infrastructure.token_management.subtechniques.counting.default.token_counter import (
            TokenCounter,
        )

        logger.info("Summarizing context to reduce %s tokens", target_token_reduction)

        # Get provider and model from configuration
        config = get_config()
        default_provider = "anthropic"  # Fallback if config not available
        default_model = "claude-sonnet-4-5"  # Fallback if config not available

        if config.providers:
            llm_config = config.providers.get_llm_provider()
            if llm_config:
                default_provider = llm_config.name
                # Get cheapest model for summarization
                cheapest_model = llm_config.get_cheapest_model()
                if cheapest_model:
                    default_model = cheapest_model.name

        # Identify compressible sections
        compressible = {
            "dynamic_observations": context.dynamic_observations,
            "summaries": context.summaries,
        }

        # Summarize each section
        compressed = {}
        for key, content in compressible.items():
            if not content:
                continue

            # Count tokens in original
            original_tokens = TokenCounter.count(
                json.dumps(content), model=default_model, provider=default_provider
            )

            logger.debug("Summarizing %s (%s tokens)", key, original_tokens)

            # Summarize (with caching if enabled)
            summary_json = await self.summarize(
                content=content,
                llm_provider=llm_provider,
                session_id=session_id,
                turn_id=turn_id,
                summarize_threshold=summarize_threshold,
                rotate_threshold=rotate_threshold,
            )
            compressed[key] = json.loads(summary_json)

            # Count tokens in summary
            summary_tokens = TokenCounter.count(
                summary_json, model=default_model, provider=default_provider
            )

            reduction = original_tokens - summary_tokens
            logger.info(
                "Compressed %s: %s → %s tokens (%s saved)",
                key,
                original_tokens,
                summary_tokens,
                reduction,
            )

        # Build new envelope
        return ContextEnvelope(
            stable_inputs=context.stable_inputs,  # Never compress stable
            stable_hash=context.stable_hash,
            dynamic_observations=compressed.get("dynamic_observations", {}),
            summaries=compressed.get("summaries", {}),
            summary_version="2.0",  # Indicate re-summarized
        )


class ContextHasher:
    """Utility for computing content hashes."""

    @staticmethod
    def hash_content(content: str) -> str:
        """Hash string content.

        Args:
            content: Content to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def hash_dict(data: dict[str, Any]) -> str:
        """Hash dict with canonical JSON.

        Args:
            data: Dict to hash

        Returns:
            SHA256 hex digest
        """
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    @staticmethod
    def verify_hash(content: str, expected_hash: str) -> bool:
        """Verify content matches hash.

        Args:
            content: Content to verify
            expected_hash: Expected SHA256 hex digest

        Returns:
            True if match, False otherwise
        """
        actual_hash = ContextHasher.hash_content(content)
        return actual_hash == expected_hash


def get_context_optimizer(with_cache: bool = True) -> ContextOptimizer:
    """Factory function to create ContextOptimizer with optional caching.

    Args:
        with_cache: Whether to enable SummaryCache (default True)

    Returns:
        ContextOptimizer instance

    Usage:
        # With caching (recommended for production)
        optimizer = get_context_optimizer(with_cache=True)

        # Without caching (for testing or simple use cases)
        optimizer = get_context_optimizer(with_cache=False)

        # Cache-aware summarization
        summary = await optimizer.summarize(
            content=my_content,
            llm_provider=provider,
            session_id="sess_123",
            turn_id=42,
            summarize_threshold=60.0,
            rotate_threshold=70.0,
        )
    """
    if with_cache:
        try:
            from sibyl.core.infrastructure.session.summary_cache import get_summary_cache

            cache = get_summary_cache()
            logger.info("Created ContextOptimizer with SummaryCache")
            return ContextOptimizer(summary_cache=cache)
        except ImportError:
            logger.warning("SummaryCache not available, creating ContextOptimizer without cache")
            return ContextOptimizer(summary_cache=None)
    else:
        logger.info("Created ContextOptimizer without cache")
        return ContextOptimizer(summary_cache=None)
