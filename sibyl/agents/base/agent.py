"""
Base Agent - Generic foundation for all Sibyl agents.

This is a domain-neutral base class that provides:
- LLM integration
- Session management
- Quality control integration
- Search capabilities
- Budget tracking

No domain-specific logic or assumptions.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sibyl.agents.types import AgentRequestPayload, AgentResponsePayload

if TYPE_CHECKING:
    from sibyl.core.infrastructure.llm.base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base agent providing core capabilities without domain assumptions.

    All agents in Sibyl inherit from this base and implement their
    specific orchestration logic.
    """

    def __init__(
        self,
        agent_id: str,
        llm_client: "BaseLLMClient | None" = None,
        session_context: Any = None,
        qc_orchestrator: Any = None,
        search_service: Any = None,
        budget_tracker: Any = None,
    ) -> None:
        """
        Initialize base agent with framework services.

        Args:
            agent_id: Unique identifier for this agent
            llm_client: Optional LLM client for reasoning
            session_context: Session management
            qc_orchestrator: Quality control service
            search_service: Knowledge base search
            budget_tracker: Resource budget tracking
        """
        self.agent_id = agent_id
        self.llm_client = llm_client
        self.session_context = session_context
        self.qc_orchestrator = qc_orchestrator
        self.search_service = search_service
        self.budget_tracker = budget_tracker

        logger.info("Initialized agent: %s", agent_id)

    @abstractmethod
    async def execute(self, request: AgentRequestPayload) -> AgentResponsePayload:
        """
        Execute agent logic.

        Args:
            request: Generic request parameters

        Returns:
            Generic response dictionary
        """

    async def search_knowledge_base(
        self, query: str, filters: dict[str, Any] | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search the knowledge base.

        Args:
            query: Search query string
            filters: Optional filters (resource_type, tags, etc.)
            limit: Maximum results

        Returns:
            List of search results
        """
        if not self.search_service:
            logger.warning("%s: No search service available", self.agent_id)
            return []

        try:
            return await self.search_service.search(query=query, filters=filters or {}, limit=limit)
        except Exception as e:
            logger.exception("%s: Search failed: %s", self.agent_id, e)
            return []

    async def run_quality_checks(
        self, resource_id: str, check_types: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run quality control checks on a resource.

        Args:
            resource_id: Resource identifier
            check_types: Optional list of specific check types

        Returns:
            Quality check results
        """
        if not self.qc_orchestrator:
            logger.warning("%s: No QC service available", self.agent_id)
            return {"status": "skipped", "reason": "no_qc_service"}

        try:
            return await self.qc_orchestrator.run_checks(
                resource_id=resource_id, check_types=check_types
            )
        except Exception as e:
            logger.exception("%s: QC failed: %s", self.agent_id, e)
            return {"status": "error", "error": str(e)}

    async def call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call LLM for reasoning.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            LLM response text
        """
        if not self.llm_client:
            logger.warning("%s: No LLM client available", self.agent_id)
            return ""

        try:
            return await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.exception("%s: LLM call failed: %s", self.agent_id, e)
            return ""

    def check_budget(self) -> dict[str, Any]:
        """
        Check current budget status.

        Returns:
            Budget status dictionary
        """
        if not self.budget_tracker:
            return {"status": "unlimited"}

        return self.budget_tracker.get_status()

    def record_metric(self, metric_name: str, value: str | int | float | bool) -> None:
        """
        Record a metric for observability.

        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if self.session_context:
            self.session_context.record_metric(
                agent_id=self.agent_id, metric_name=metric_name, value=value
            )
