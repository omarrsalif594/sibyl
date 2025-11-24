"""
Review Agent - Reviews execution results and provides feedback.

This agent:
- Analyzes execution results
- Identifies issues and improvements
- Provides actionable feedback
- Uses QC signals
- No domain assumptions
"""

import logging
from typing import Any

from sibyl.agents.base.agent import BaseAgent
from sibyl.agents.types import AgentRequestPayload, AgentResponsePayload

logger = logging.getLogger(__name__)

__all__ = ["ReviewAgent"]


class ReviewAgent(BaseAgent):
    """
    Generic review agent that critiques execution results.

    Uses QC signals and heuristics to provide feedback.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize review agent."""
        super().__init__(agent_id="reviewer", **kwargs)
        logger.info("Review agent initialized")

    async def execute(self, request: AgentRequestPayload) -> AgentResponsePayload:
        """
        Review execution results.

        Args:
            request: {
                "results": execution results to review,
                "plan": original plan,
                "goal": original goal
            }

        Returns:
            {
                "summary": overall summary,
                "issues": list of identified issues,
                "suggestions": list of improvements,
                "quality_score": 0-100 score
            }
        """
        results = request.get("results", [])
        plan = request.get("plan", [])
        goal = request.get("goal", "")

        logger.info("Reviewing %s results", len(results))

        # Analyze results
        issues = self._identify_issues(results)
        suggestions = self._generate_suggestions(results, plan, goal)
        quality_score = self._calculate_quality_score(results, issues)

        # Generate summary
        summary = await self._generate_summary(results, issues, suggestions, goal)

        return {
            "summary": summary,
            "issues": issues,
            "suggestions": suggestions,
            "quality_score": quality_score,
            "reviewed_count": len(results),
        }

    def _identify_issues(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Identify issues in results.

        Args:
            results: Execution results

        Returns:
            List of issues
        """
        issues = []

        for result in results:
            # Check for failures
            if result.get("status") == "failed":
                issues.append(
                    {
                        "type": "execution_failure",
                        "step": result.get("step"),
                        "severity": "high",
                        "message": f"Step {result.get('step')} failed: {result.get('error')}",
                    }
                )

            # Check QC results
            qc = result.get("result", {}).get("qc", {})
            if qc.get("status") == "completed" and not qc.get("passed"):
                issues.append(
                    {
                        "type": "quality_check_failed",
                        "step": result.get("step"),
                        "severity": "medium",
                        "message": f"Quality checks failed for step {result.get('step')}",
                    }
                )

            # Check for warnings
            warnings = result.get("result", {}).get("warnings", [])
            for warning in warnings:
                issues.append(
                    {
                        "type": "warning",
                        "step": result.get("step"),
                        "severity": "low",
                        "message": warning,
                    }
                )

        logger.debug("Identified %s issues", len(issues))
        return issues

    def _generate_suggestions(
        self, results: list[dict[str, Any]], plan: list[dict[str, Any]], goal: str
    ) -> list[dict[str, Any]]:
        """
        Generate improvement suggestions.

        Args:
            results: Execution results
            plan: Original plan
            goal: Original goal

        Returns:
            List of suggestions
        """
        suggestions = []

        # Check if all steps completed
        completed = len([r for r in results if r.get("status") == "success"])
        if completed < len(plan):
            suggestions.append(
                {
                    "type": "retry",
                    "message": f"Only {completed}/{len(plan)} steps completed. Consider retrying failed steps.",
                }
            )

        # Check for performance issues
        slow_steps = [r for r in results if r.get("result", {}).get("duration_seconds", 0) > 30]
        if slow_steps:
            suggestions.append(
                {
                    "type": "performance",
                    "message": f"{len(slow_steps)} steps took >30s. Consider optimization.",
                }
            )

        # Check for missing QC
        no_qc = [r for r in results if "qc" not in r.get("result", {})]
        if no_qc:
            suggestions.append(
                {
                    "type": "quality",
                    "message": f"{len(no_qc)} steps have no quality checks. Consider adding validation.",
                }
            )

        return suggestions

    def _calculate_quality_score(
        self, results: list[dict[str, Any]], issues: list[dict[str, Any]]
    ) -> int:
        """
        Calculate overall quality score.

        Args:
            results: Execution results
            issues: Identified issues

        Returns:
            Score 0-100
        """
        if not results:
            return 0

        # Start with 100
        score = 100

        # Deduct for failures
        failures = len([r for r in results if r.get("status") == "failed"])
        score -= failures * 20

        # Deduct for issues by severity
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 10
            else:
                score -= 5

        # Ensure 0-100 range
        return max(0, min(100, score))

    async def _generate_summary(
        self,
        results: list[dict[str, Any]],
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        goal: str,
    ) -> str:
        """
        Generate human-readable summary.

        Args:
            results: Execution results
            issues: Identified issues
            suggestions: Suggestions
            goal: Original goal

        Returns:
            Summary text
        """
        success_count = len([r for r in results if r.get("status") == "success"])
        total_count = len(results)

        summary_parts = [
            f"Execution Review for: {goal}",
            "",
            f"Results: {success_count}/{total_count} steps completed successfully",
        ]

        if issues:
            summary_parts.append(f"Issues: {len(issues)} identified")
            for issue in issues[:3]:  # Show top 3
                summary_parts.append(f"  - {issue['message']}")
        else:
            summary_parts.append("Issues: None")

        if suggestions:
            summary_parts.append(f"Suggestions: {len(suggestions)}")
            for suggestion in suggestions[:3]:  # Show top 3
                summary_parts.append(f"  - {suggestion['message']}")

        # Use LLM for richer summary if available
        if self.llm_client and goal:
            llm_summary = await self._generate_llm_summary(results, issues, suggestions, goal)
            if llm_summary:
                summary_parts.append("")
                summary_parts.append("Analysis:")
                summary_parts.append(llm_summary)

        return "\n".join(summary_parts)

    async def _generate_llm_summary(
        self,
        results: list[dict[str, Any]],
        issues: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        goal: str,
    ) -> str:
        """
        Generate LLM-powered summary.

        Args:
            results: Execution results
            issues: Issues
            suggestions: Suggestions
            goal: Original goal

        Returns:
            LLM summary
        """
        prompt = f"""
Review the following execution:

Goal: {goal}
Results: {len(results)} steps executed
Issues: {len(issues)}
Suggestions: {len(suggestions)}

Provide a brief analysis of what went well and what could be improved.
Focus on actionable insights.
"""

        return await self.call_llm(
            prompt=prompt,
            system_prompt="You are a code review expert. Provide constructive feedback.",
            max_tokens=500,
        )
