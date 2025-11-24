"""
Planner Agent - Plans task execution using available tools.

This agent:
- Analyzes user requests
- Identifies required tools from the tool catalog
- Creates execution plans
- No domain-specific assumptions
"""

import logging
from typing import Any

from sibyl.agents.base.agent import BaseAgent
from sibyl.agents.types import AgentRequestPayload, AgentResponsePayload

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Generic planning agent that creates execution plans from tool metadata.

    Uses tool catalog to understand capabilities and plan accordingly.
    """

    def __init__(self, tool_catalog: dict[str, Any], **kwargs) -> None:
        """
        Initialize planner agent.

        Args:
            tool_catalog: Available tools and their metadata
            **kwargs: Base agent parameters
        """
        super().__init__(agent_id="planner", **kwargs)
        self.tool_catalog = tool_catalog
        logger.info("Planner initialized with %s tools", len(tool_catalog))

    async def execute(self, request: AgentRequestPayload) -> AgentResponsePayload:
        """
        Create an execution plan for the request.

        Args:
            request: {
                "goal": "what user wants to achieve",
                "context": optional context,
                "constraints": optional constraints
            }

        Returns:
            {
                "plan": [list of steps],
                "tools_required": [list of tool names],
                "estimated_cost": budget estimate,
                "confidence": confidence score
            }
        """
        goal = request.get("goal", "")
        context = request.get("context", {})
        constraints = request.get("constraints", {})

        logger.info("Planning for goal: %s", goal)

        # Analyze goal and identify relevant tools
        relevant_tools = self._identify_tools(goal, context)

        # Create execution plan
        plan = await self._create_plan(goal, relevant_tools, constraints)

        # Estimate cost
        estimated_cost = self._estimate_cost(plan)

        return {
            "plan": plan,
            "tools_required": [step["tool"] for step in plan],
            "estimated_cost": estimated_cost,
            "confidence": self._calculate_confidence(plan, relevant_tools),
        }

    def _identify_tools(self, goal: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Identify relevant tools for the goal.

        Args:
            goal: User's goal
            context: Additional context

        Returns:
            List of relevant tool metadata
        """
        relevant = []

        goal_lower = goal.lower()

        for tool_name, tool_meta in self.tool_catalog.items():
            # Simple keyword matching (can be enhanced with semantic search)
            description = tool_meta.get("description", "").lower()
            keywords = tool_meta.get("keywords", [])

            # Check if tool is relevant
            if any(kw.lower() in goal_lower for kw in keywords) or any(
                word in description for word in goal_lower.split()
            ):
                relevant.append({"name": tool_name, "metadata": tool_meta})

        logger.debug("Identified %s relevant tools", len(relevant))
        return relevant

    async def _create_plan(
        self, goal: str, tools: list[dict[str, Any]], constraints: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Create execution plan from goal and tools.

        Args:
            goal: User's goal
            tools: Available tools
            constraints: Execution constraints

        Returns:
            List of execution steps
        """
        if not tools:
            return [
                {
                    "step": 1,
                    "action": "search",
                    "tool": "knowledge_base_search",
                    "params": {"query": goal},
                }
            ]

        # If we have LLM, use it for sophisticated planning
        if self.llm_client:
            return await self._llm_based_planning(goal, tools, constraints)

        # Otherwise, use simple heuristic planning
        return self._heuristic_planning(goal, tools, constraints)

    async def _llm_based_planning(
        self, goal: str, tools: list[dict[str, Any]], constraints: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Use LLM to create sophisticated plan.

        Args:
            goal: User's goal
            tools: Available tools
            constraints: Execution constraints

        Returns:
            List of execution steps
        """
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['metadata'].get('description', '')}" for t in tools]
        )

        prompt = f"""
Given the goal: {goal}

Available tools:
{tool_descriptions}

Constraints: {constraints}

Create a step-by-step execution plan. Return as JSON array of steps.
Each step should have: step_number, tool_name, action_description, parameters.
"""

        response = await self.call_llm(
            prompt=prompt,
            system_prompt="You are a task planning expert. Create efficient execution plans.",
        )

        # Parse LLM response into plan (simplified)
        # In production, would use structured output
        return self._parse_plan_response(response, tools)

    def _heuristic_planning(
        self, goal: str, tools: list[dict[str, Any]], constraints: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Create plan using simple heuristics.

        Args:
            goal: User's goal
            tools: Available tools
            constraints: Execution constraints

        Returns:
            List of execution steps
        """
        plan = []

        # Simple sequential plan
        for idx, tool in enumerate(tools[:5], 1):  # Limit to 5 tools
            plan.append(
                {
                    "step": idx,
                    "tool": tool["name"],
                    "action": f"Execute {tool['name']}",
                    "params": {"goal": goal},
                }
            )

        return plan

    def _estimate_cost(self, plan: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Estimate execution cost.

        Args:
            plan: Execution plan

        Returns:
            Cost estimate
        """
        return {
            "steps": len(plan),
            "estimated_tokens": len(plan) * 1000,  # Rough estimate
            "estimated_time_seconds": len(plan) * 5,
        }

    def _calculate_confidence(
        self, plan: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> float:
        """
        Calculate confidence in the plan.

        Args:
            plan: Execution plan
            tools: Available tools

        Returns:
            Confidence score (0-1)
        """
        if not plan:
            return 0.0

        if not tools:
            return 0.3  # Low confidence with no tools

        # Higher confidence with more relevant tools
        return min(0.9, 0.5 + (len(tools) * 0.1))

    def _parse_plan_response(
        self, response: str, tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Parse LLM response into structured plan.

        Args:
            response: LLM response
            tools: Available tools

        Returns:
            Structured plan
        """
        # Simplified parsing - in production would use JSON schema
        import json  # can be moved to top

        try:
            return json.loads(response)
        except:
            # Fallback to heuristic
            return self._heuristic_planning("", tools, {})
