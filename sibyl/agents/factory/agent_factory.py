"""
Agent Factory - Creates and configures agents.

This module:
- Builds agents with proper dependencies
- Handles profile-based configuration
- Manages agent lifecycle
"""

import logging
from typing import Any

from sibyl.agents.base.agent import BaseAgent
from sibyl.agents.implementations.executor import ExecutorAgent
from sibyl.agents.implementations.planner import PlannerAgent
from sibyl.agents.implementations.search import SearchAgent

# Import ReviewAgent lazily to avoid circular dependency
# Will be imported when needed
from sibyl.agents.tools import get_tool_catalog

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating configured agents.

    Handles dependency injection and profile-based configuration.
    """

    def __init__(
        self,
        llm_client: Any = None,
        session_context: Any = None,
        qc_orchestrator: Any = None,
        search_service: Any = None,
        hybrid_search_service: Any = None,
        budget_tracker: Any = None,
        tool_executor: Any = None,
        plugin_registry: Any = None,
        profile: str | None = None,
    ) -> None:
        """
        Initialize agent factory.

        Args:
            llm_client: LLM client for reasoning
            session_context: Session management
            qc_orchestrator: Quality control service
            search_service: Knowledge base search
            hybrid_search_service: Hybrid search backend
            budget_tracker: Budget tracking
            tool_executor: Tool execution service
            plugin_registry: Plugin registry
            profile: Optional profile name
        """
        self.llm_client = llm_client
        self.session_context = session_context
        self.qc_orchestrator = qc_orchestrator
        self.search_service = search_service
        self.hybrid_search_service = hybrid_search_service
        self.budget_tracker = budget_tracker
        self.tool_executor = tool_executor
        self.plugin_registry = plugin_registry
        self.profile = profile

        # Load tool catalog for this profile
        self.tool_catalog = get_tool_catalog(profile)

        logger.info(
            "AgentFactory initialized (profile=%s, tools=%s)", profile, len(self.tool_catalog)
        )

    def create_planner(self) -> PlannerAgent:
        """
        Create planner agent.

        Returns:
            Configured PlannerAgent
        """
        return PlannerAgent(
            tool_catalog=self.tool_catalog,
            llm_client=self.llm_client,
            session_context=self.session_context,
            qc_orchestrator=self.qc_orchestrator,
            search_service=self.search_service,
            budget_tracker=self.budget_tracker,
        )

    def create_executor(self) -> ExecutorAgent:
        """
        Create executor agent.

        Returns:
            Configured ExecutorAgent
        """
        if not self.tool_executor:
            logger.warning("No tool executor provided, executor agent may not function properly")

        return ExecutorAgent(
            tool_executor=self.tool_executor,
            plugin_registry=self.plugin_registry,
            llm_client=self.llm_client,
            session_context=self.session_context,
            qc_orchestrator=self.qc_orchestrator,
            search_service=self.search_service,
            budget_tracker=self.budget_tracker,
        )

    def create_reviewer(self) -> Any:
        """
        Create review agent.

        Returns:
            Configured ReviewAgent
        """
        # Lazy import to avoid circular dependency
        from sibyl.agents.implementations.reviewer import ReviewAgent

        return ReviewAgent(
            llm_client=self.llm_client,
            session_context=self.session_context,
            qc_orchestrator=self.qc_orchestrator,
            search_service=self.search_service,
            budget_tracker=self.budget_tracker,
        )

    def create_search(self) -> SearchAgent:
        """
        Create search agent.

        Returns:
            Configured SearchAgent
        """
        return SearchAgent(
            hybrid_search_service=self.hybrid_search_service,
            llm_client=self.llm_client,
            session_context=self.session_context,
            qc_orchestrator=self.qc_orchestrator,
            search_service=self.search_service,
            budget_tracker=self.budget_tracker,
        )

    def create_all_agents(self) -> dict[str, BaseAgent]:
        """
        Create all standard agents.

        Returns:
            Dictionary of agent_name -> agent instance
        """
        agents = {
            "planner": self.create_planner(),
            "executor": self.create_executor(),
            "reviewer": self.create_reviewer(),
            "search": self.create_search(),
        }

        logger.info("Created %s agents", len(agents))
        return agents


def build_agents(profile: str | None = None, **services: Any) -> dict[str, BaseAgent]:
    """
    Convenience function to build all agents.

    Args:
        profile: Optional profile name
        **services: Service dependencies (llm_client, search_service, etc.)

    Returns:
        Dictionary of agent_name -> agent instance
    """
    factory = AgentFactory(profile=profile, **services)
    return factory.create_all_agents()


def extend_tool_catalog(additional_tools: dict[str, Any], factory: AgentFactory) -> AgentFactory:
    """
    Extend tool catalog with additional tools.

    This is used by example packages to inject their tools.

    Args:
        additional_tools: Additional tool definitions
        factory: Existing factory

    Returns:
        Factory with extended catalog
    """
    factory.tool_catalog.update(additional_tools)
    logger.info("Extended tool catalog: %s tools total", len(factory.tool_catalog))
    return factory
