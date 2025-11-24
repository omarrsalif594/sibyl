"""Generic expert agent framework - domain-agnostic AI analysis.

This module provides a generic expert agent abstraction with NO domain assumptions.
Experts can analyze any type of input and provide recommendations.


Example usage:
    class AlertExpert(ExpertAgent):
        async def analyze(self, input: dict, context: dict) -> ExpertReport:
            current = input.get("current_value", 0)
            threshold = input.get("threshold", 0)

            if current < threshold:
                return ExpertReport(
                    analysis="Value is below threshold",
                    recommendations=["Open incident ticket", "Notify responder"],
                    confidence=0.95
                )
            return ExpertReport(
                analysis="Value is within threshold",
                recommendations=[],
                confidence=0.90
            )

    expert = AlertExpert()
    report = await expert.analyze({"current_value": 10, "threshold": 50}, {})
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ExpertReport:
    """Report from an expert agent analysis.

    This is a generic report structure that can represent analysis results
    for any domain (operations, code quality, data validation, etc.).

    Attributes:
        analysis: Human-readable analysis summary
        recommendations: List of actionable recommendations
        confidence: Confidence score (0.0 to 1.0)
        metadata: Additional context
        report_id: Unique identifier
        timestamp: When analysis was performed
        expert_name: Name of the expert who generated this report
    """

    analysis: str
    recommendations: list[str]
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    report_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expert_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analysis": self.analysis,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "expert_name": self.expert_name,
        }


class ExpertAgent(ABC):
    """Generic expert agent - analyzes any domain.

    Expert agents provide AI-powered analysis and recommendations.
    They are completely domain-agnostic and can be applied to any problem.

    Subclasses implement the analyze() method to provide domain-specific logic.
    """

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize expert agent.

        Args:
            name: Expert name
            description: Human-readable description
        """
        self.name = name
        self.description = description
        logger.info("Initialized expert: %s", name)

    @abstractmethod
    async def analyze(self, input: Any, context: dict[str, Any]) -> ExpertReport:
        """Analyze input and provide recommendations.

        This is the core method that subclasses must implement.
        It takes arbitrary input and context, performs analysis,
        and returns an ExpertReport.

        Args:
            input: Input to analyze (can be dict, object, etc.)
            context: Additional context for analysis

        Returns:
            ExpertReport with analysis and recommendations
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class ExpertOrchestrator:
    """Orchestrates multiple expert agents.

    This class manages a collection of experts and can run them
    in sequence or parallel to get comprehensive analysis.
    """

    def __init__(self, experts: list[ExpertAgent]) -> None:
        """Initialize with list of experts.

        Args:
            experts: List of ExpertAgent instances
        """
        self.experts = experts
        logger.info("Initialized ExpertOrchestrator with %s experts", len(experts))

    async def analyze(
        self, input: Any, context: dict[str, Any] | None = None
    ) -> list[ExpertReport]:
        """Run all experts on the input.

        Args:
            input: Input to analyze
            context: Optional analysis context

        Returns:
            List of ExpertReport objects from all experts
        """
        context = context or {}
        reports = []

        for expert in self.experts:
            try:
                report = await expert.analyze(input, context)
                report.expert_name = expert.name
                reports.append(report)
                logger.debug("Expert %s completed analysis", expert.name)
            except Exception as e:
                logger.exception("Expert %s failed: %s", expert.name, e)
                # Add error report
                reports.append(
                    ExpertReport(
                        analysis=f"Expert analysis failed: {e}",
                        recommendations=["Review expert configuration", "Check input data"],
                        confidence=0.0,
                        metadata={"error": str(e), "expert": expert.name},
                        expert_name=expert.name,
                    )
                )

        logger.info("Completed analysis with %s expert reports", len(reports))
        return reports

    def get_consensus(self, reports: list[ExpertReport]) -> ExpertReport:
        """Get consensus from multiple expert reports.

        Combines recommendations and averages confidence scores.

        Args:
            reports: List of ExpertReport objects

        Returns:
            Consolidated ExpertReport
        """
        if not reports:
            return ExpertReport(
                analysis="No expert reports available",
                recommendations=[],
                confidence=0.0,
                expert_name="consensus",
            )

        # Combine all recommendations (deduplicate)
        all_recommendations = []
        seen = set()
        for report in reports:
            for rec in report.recommendations:
                if rec not in seen:
                    all_recommendations.append(rec)
                    seen.add(rec)

        # Average confidence
        avg_confidence = sum(r.confidence for r in reports) / len(reports)

        # Combine analyses
        analyses = [f"{r.expert_name}: {r.analysis}" for r in reports]
        combined_analysis = "\n".join(analyses)

        return ExpertReport(
            analysis=combined_analysis,
            recommendations=all_recommendations,
            confidence=avg_confidence,
            metadata={"expert_count": len(reports), "experts": [r.expert_name for r in reports]},
            expert_name="consensus",
        )

    def add_expert(self, expert: ExpertAgent) -> None:
        """Add an expert to the orchestrator.

        Args:
            expert: ExpertAgent instance
        """
        self.experts.append(expert)
        logger.info("Added expert: %s", expert.name)

    def remove_expert(self, expert_name: str) -> None:
        """Remove an expert by name.

        Args:
            expert_name: Name of expert to remove
        """
        self.experts = [e for e in self.experts if e.name != expert_name]
        logger.info("Removed expert: %s", expert_name)


# Export public API
__all__ = [
    "ExpertAgent",
    "ExpertOrchestrator",
    "ExpertReport",
]
