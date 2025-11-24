"""Base orchestration classes for the framework."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

from sibyl.core.infrastructure.state import StateFacade
from sibyl.techniques.infrastructure.llm.router import LLMRouter

from .budget import BudgetManager, BudgetPolicy
from .context import ContextEnvelope, ContextOptimizer

logger = logging.getLogger(__name__)


# Module-level config cache
_EXPERT_CONFIG: dict[str, Any] | None = None


def _get_expert_config() -> dict[str, Any]:
    """Get cached expert configuration."""
    global _EXPERT_CONFIG
    if _EXPERT_CONFIG is None:
        config_path = Path(__file__).parent / "expert_config.yaml"
        try:
            if config_path.exists():
                with open(config_path) as f:
                    _EXPERT_CONFIG = yaml.safe_load(f) or {}
            else:
                _EXPERT_CONFIG = {}
        except Exception as e:
            logger.warning("Failed to load expert config: %s", e)
            _EXPERT_CONFIG = {}

        # Set defaults if not in config
        if "default_model" not in _EXPERT_CONFIG:
            _EXPERT_CONFIG["default_model"] = "claude-sonnet-4-5-20250929"
        if "default_temperature" not in _EXPERT_CONFIG:
            _EXPERT_CONFIG["default_temperature"] = 0.0

    return _EXPERT_CONFIG


class MainOrchestrator(ABC):
    """Phase-level controller (sequential with checkpoints).

    Base class for workflow implementations. Enforces:
    - Sequential phase execution
    - Checkpointing at phase boundaries
    - Budget management per phase
    - Context hashing and versioning
    - Config snapshot immutability
    """

    def __init__(
        self,
        workflow_type: str,
        state_store: StateFacade,
        llm_router: LLMRouter,
        budget_policy: BudgetPolicy,
        config: dict[str, Any],
    ) -> None:
        """Initialize main orchestrator.

        Args:
            workflow_type: Workflow identifier
            state_store: State store for persistence
            llm_router: LLM router with backpressure
            budget_policy: Budget allocation policy
            config: Configuration dict (will be snapshot)
        """
        self.workflow_type = workflow_type
        self.state = state_store
        self.router = llm_router
        self.budget_policy = budget_policy

        # Snapshot config (immutable for this orchestrator instance)
        import copy

        self.config_snapshot = copy.deepcopy(config)
        self.config_version = config.get("version", "1.0.0")

        # Cancellation token
        self.cancel_token = asyncio.Event()

        # Context optimizer
        self.context_optimizer = ContextOptimizer()

        logger.info(
            "Main orchestrator initialized: workflow=%s, config_version=%s",
            workflow_type,
            self.config_version,
        )

    async def execute(
        self,
        conversation_id: str,
        initial_context: ContextEnvelope,
        phases: list[str],
    ) -> dict[str, Any]:
        """Execute workflow with phase checkpoints.

        Args:
            conversation_id: Unique conversation identifier
            initial_context: Initial context envelope
            phases: List of phase names to execute

        Returns:
            Dict with phase results

        Raises:
            Exception: If any phase fails
        """
        logger.info(
            "Starting workflow %s: conversation_id=%s, phases=%s",
            self.workflow_type,
            conversation_id,
            phases,
        )

        # Initialize conversation in state store
        await self.state.create_conversation(
            id=conversation_id,
            workflow_type=self.workflow_type,
            token_budget=self.budget_policy.total_budget,
            context_hash=initial_context.global_hash,
            config_version=self.config_version,
        )

        current_context = initial_context
        results = {}

        try:
            for phase_num, phase in enumerate(phases):
                if self.cancel_token.is_set():
                    logger.warning("Workflow cancelled at phase %s: %s", phase_num, phase)
                    await self.state.update_conversation(conversation_id, status="cancelled")
                    break

                logger.info(
                    f"Starting phase {phase_num + 1}/{len(phases)}: {phase}",
                    extra={"correlation_id": conversation_id, "phase": phase},
                )

                # Create checkpoint
                checkpoint_id = f"{conversation_id}:{phase}"
                await self.state.create_checkpoint(
                    id=checkpoint_id,
                    conversation_id=conversation_id,
                    phase=phase,
                    phase_number=phase_num,
                    context_hash=current_context.global_hash,
                )

                # Allocate phase budget
                phase_budget = self.budget_policy.create_phase_manager(
                    phase, degradation_strategy="downgrade"
                )

                start_time = time.monotonic()

                try:
                    # Execute phase (implemented by subclass)
                    phase_result = await self.execute_phase(
                        phase=phase,
                        context=current_context,
                        budget=phase_budget,
                        conversation_id=conversation_id,
                    )

                    results[phase] = phase_result

                    # Update context with phase output
                    if "context_delta" in phase_result:
                        current_context = self._merge_context(
                            current_context, phase_result["context_delta"]
                        )

                    # Checkpoint success
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    await self.state.update_checkpoint(
                        checkpoint_id, status="completed", duration_ms=duration_ms
                    )

                    logger.info(
                        f"Phase {phase} completed in {duration_ms}ms",
                        extra={"correlation_id": conversation_id, "phase": phase},
                    )

                except Exception as e:
                    logger.exception(
                        f"Phase {phase} failed: {e}",
                        extra={"correlation_id": conversation_id, "phase": phase},
                    )

                    # Checkpoint failure
                    await self.state.update_checkpoint(checkpoint_id, status="failed", error=str(e))

                    # Update conversation status
                    await self.state.update_conversation(conversation_id, status="failed")

                    raise

            # All phases completed
            await self.state.update_conversation(conversation_id, status="completed")

            logger.info(
                f"Workflow {self.workflow_type} completed: {len(phases)} phases",
                extra={"correlation_id": conversation_id},
            )

            return results

        except Exception as e:
            logger.exception(
                f"Workflow {self.workflow_type} failed: {e}",
                extra={"correlation_id": conversation_id},
            )
            raise

    @abstractmethod
    async def execute_phase(
        self,
        phase: str,
        context: ContextEnvelope,
        budget: BudgetManager,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Execute single phase with parallel sub-orchestrators.

        Must be implemented by subclass.

        Args:
            phase: Phase name
            context: Current context envelope
            budget: Budget manager for this phase
            conversation_id: Conversation ID for correlation

        Returns:
            Phase result dict with:
            - context_delta: Changes to context
            - results: Phase-specific results
            - duration_ms: Execution time
            - tokens_used: Tokens consumed
            - cost_usd: Cost incurred
        """

    def _merge_context(self, current: ContextEnvelope, delta: dict[str, Any]) -> ContextEnvelope:
        """Merge context delta into current context.

        Args:
            current: Current context envelope
            delta: Delta from phase execution

        Returns:
            New context envelope with merged changes
        """
        # Update observations if present
        if "observations" in delta:
            for phase, observations in delta["observations"].items():
                current.update_observations(phase, observations)

        # Update summaries if present
        if "summaries" in delta:
            for phase, summary in delta["summaries"].items():
                current.update_summary(phase, summary)

        return current

    async def cancel(self) -> None:
        """Cancel workflow execution."""
        logger.warning("Cancellation requested")
        self.cancel_token.set()


class SubOrchestrator:
    """Parallel worker for a single task (e.g., one model).

    Coordinates domain experts for a specific task within a phase.
    """

    def __init__(
        self,
        task_id: str,
        phase: str,
        expert_registry: "ExpertRegistry",
        llm_router: LLMRouter,
        state_store: StateFacade,
    ) -> None:
        """Initialize sub-orchestrator.

        Args:
            task_id: Task identifier
            phase: Phase name
            expert_registry: Registry of domain experts
            llm_router: LLM router
            state_store: State store
        """
        self.task_id = task_id
        self.phase = phase
        self.experts = expert_registry
        self.router = llm_router
        self.state = state_store

        logger.debug("Sub-orchestrator created: task=%s, phase=%s", task_id, phase)

    async def execute(
        self,
        context_slice: dict[str, Any],
        budget: BudgetManager,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Execute task by coordinating domain experts.

        Args:
            context_slice: Relevant context slice for this task
            budget: Budget manager
            correlation_id: Correlation ID for tracing

        Returns:
            Task result dict with:
            - task_id: Task identifier
            - expert_responses: Dict of expert responses
            - tokens_used: Total tokens consumed
            - duration_ms: Execution time
        """
        span_id = f"{correlation_id}:{self.task_id}"
        start_time = time.monotonic()

        logger.info(
            f"Sub-orchestrator executing: task={self.task_id}",
            extra={"correlation_id": correlation_id, "span_id": span_id},
        )

        # Query experts (phase-specific logic)
        expert_responses = await self._coordinate_experts(
            context_slice, budget, correlation_id, span_id
        )

        duration_ms = int((time.monotonic() - start_time) * 1000)
        tokens_used = sum(r.get("tokens_used", 0) for r in expert_responses.values())

        logger.info(
            f"Sub-orchestrator completed: task={self.task_id}, tokens={tokens_used}, duration={duration_ms}ms",
            extra={"correlation_id": correlation_id, "span_id": span_id},
        )

        return {
            "task_id": self.task_id,
            "expert_responses": expert_responses,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
        }

    async def _coordinate_experts(
        self,
        context_slice: dict[str, Any],
        budget: BudgetManager,
        correlation_id: str,
        span_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Coordinate domain experts (phase-specific).

        Args:
            context_slice: Context slice
            budget: Budget manager
            correlation_id: Correlation ID
            span_id: Span ID

        Returns:
            Dict of expert_type → response
        """
        responses = {}

        # Load expert coordination workflow from config
        config = _get_expert_config()
        coordination_config = config.get("expert_coordination", {})
        workflow = coordination_config.get(self.phase, coordination_config.get("default", []))

        # Execute workflow steps
        for step in workflow:
            expert_type = step.get("expert_type")
            condition = step.get("condition")
            query_field = step.get("query_field")
            response_key = step.get("response_key", expert_type)

            # Check if condition is met
            if condition and condition not in context_slice:
                continue

            # Get query from specified field
            query = context_slice.get(query_field, "")
            if not query:
                continue

            # Query the expert
            expert_response = await self._query_expert(
                expert_type=expert_type,
                query=query,
                context=context_slice,
                budget=budget,
                correlation_id=correlation_id,
                span_id=f"{span_id}:{expert_type}",
            )
            responses[response_key] = expert_response

        return responses

    async def _query_expert(
        self,
        expert_type: str,
        query: str,
        context: dict[str, Any],
        budget: BudgetManager,
        correlation_id: str,
        span_id: str,
    ) -> dict[str, Any]:
        """Query a domain expert.

        Args:
            expert_type: Expert identifier
            query: Query for expert
            context: Context dict
            budget: Budget manager
            correlation_id: Correlation ID
            span_id: Span ID

        Returns:
            Expert response dict
        """
        expert = self.experts.get(expert_type)

        # Call expert
        return await expert.answer(
            query=query,
            context=context,
            router=self.router,
            budget=budget,
            correlation_id=correlation_id,
            span_id=span_id,
        )


class ExpertRegistry:
    """Registry for domain experts."""

    def __init__(self) -> None:
        """Initialize expert registry."""
        self._experts: dict[str, ExpertAgent] = {}

    def register(self, expert_type: str, expert: "ExpertAgent") -> None:
        """Register an expert.

        Args:
            expert_type: Expert identifier
            expert: Expert instance
        """
        self._experts[expert_type] = expert
        logger.info("Registered expert: %s", expert_type)

    def get(self, expert_type: str) -> "ExpertAgent":
        """Get expert by type.

        Args:
            expert_type: Expert identifier

        Returns:
            ExpertAgent instance

        Raises:
            KeyError: If expert not found
        """
        if expert_type not in self._experts:
            msg = f"Expert not found: {expert_type}"
            raise KeyError(msg)
        return self._experts[expert_type]

    def list_experts(self) -> list[str]:
        """List all registered experts.

        Returns:
            List of expert type names
        """
        return list(self._experts.keys())


class ExpertAgent(ABC):
    """Base class for domain experts.

    Domain experts are specialized agents that answer specific queries
    using LLMs with structured prompts.
    """

    def __init__(
        self,
        expert_type: str,
        default_model: str | None = None,
        default_temperature: float | None = None,
    ) -> None:
        """Initialize expert agent.

        Args:
            expert_type: Expert identifier
            default_model: Default model to use (loads from config if None)
            default_temperature: Default temperature (loads from config if None)
        """
        # Load from config if not provided
        config = _get_expert_config()
        if default_model is None:
            default_model = config.get("default_model", "claude-sonnet-4-5-20250929")
        if default_temperature is None:
            default_temperature = config.get("default_temperature", 0.0)
        self.expert_type = expert_type
        self.default_model = default_model
        self.default_temperature = default_temperature

        logger.debug("Expert agent created: %s", expert_type)

    @abstractmethod
    def build_prompt(self, query: str, context: dict[str, Any]) -> str:
        """Build expert-specific prompt.

        Args:
            query: Query for expert
            context: Context dict

        Returns:
            Prompt string
        """

    @abstractmethod
    def parse_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured output.

        Args:
            response: LLM response text

        Returns:
            Parsed response dict
        """

    async def answer(
        self,
        query: str,
        context: dict[str, Any],
        router: LLMRouter,
        budget: BudgetManager,
        correlation_id: str,
        span_id: str,
    ) -> dict[str, Any]:
        """Query the expert.

        Args:
            query: Query for expert
            context: Context dict
            router: LLM router
            budget: Budget manager
            correlation_id: Correlation ID
            span_id: Span ID

        Returns:
            Expert response dict with:
            - answer: Parsed answer
            - confidence: Confidence score (0-1)
            - tokens_used: Tokens consumed
            - latency_ms: Response latency
            - finish_reason: LLM finish reason
        """
        from sibyl.core.contracts.providers import CompletionOptions
        from sibyl.techniques.infrastructure.token_management.subtechniques.counting.default.token_counter import (
            TokenCounter,
        )

        # Build prompt
        prompt = self.build_prompt(query, context)

        # Get current model from budget
        current_model = budget.get_current_model()

        # Preflight token estimation
        estimated_tokens = TokenCounter.count(prompt, current_model.model, current_model.provider)
        estimated_cost = current_model.estimate_cost(estimated_tokens, estimated_tokens)

        # Check budget
        budget_action = await budget.check_and_reserve(estimated_tokens, estimated_cost)

        if budget_action["action"] == "downgrade":
            # Use downgraded model
            current_model = budget_action["model"]
            logger.warning(
                "Expert %s using downgraded model: %s", self.expert_type, current_model.model
            )

        elif budget_action["action"] == "summarize":
            logger.warning("Expert %s needs context summarization", self.expert_type)
            # TODO: Trigger summarization
            msg = "Context summarization not yet implemented"
            raise NotImplementedError(msg)

        # Call LLM
        start_time = time.monotonic()

        result = await router.route(
            provider=current_model.provider,
            model=current_model.model,
            prompt=prompt,
            options=CompletionOptions(
                model=current_model.model,
                temperature=self.default_temperature,
                correlation_id=correlation_id,
                seed=42 if self.default_temperature == 0.0 else None,
            ),
        )

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Commit actual budget
        actual_tokens = result["tokens_in"] + result["tokens_out"]
        actual_cost = current_model.estimate_cost(result["tokens_in"], result["tokens_out"])
        await budget.commit(actual_tokens, actual_cost, estimated_tokens)

        # Parse response
        parsed = self.parse_response(result["text"])

        return {
            "answer": parsed,
            "confidence": self._compute_confidence(parsed),
            "tokens_used": actual_tokens,
            "latency_ms": latency_ms,
            "finish_reason": result["finish_reason"],
        }

    def _compute_confidence(self, parsed: dict[str, Any]) -> float:
        """Compute confidence score (0-1).

        Override in subclass if needed.

        Args:
            parsed: Parsed response

        Returns:
            Confidence score
        """
        # Load from config
        config = _get_expert_config()
        conf_config = config.get("confidence_calculation", {})

        # Check for expert-specific confidence
        per_expert = conf_config.get("per_expert", {})
        if self.expert_type in per_expert:
            return per_expert[self.expert_type]

        # Return default confidence
        return conf_config.get("default_confidence", 0.9)
