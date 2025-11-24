"""Perspective variation implementation for multi-query generation.

This implementation generates multiple perspectives of the same query to improve retrieval coverage.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class PerspectiveVariation:
    """Perspective variation multi-query generation implementation."""

    def __init__(self) -> None:
        self._name = "perspective_variation"
        self._description = "Generate multiple perspectives of the same query"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

        # Common perspective variations
        self._perspective_mappings = {
            "best practices": ["recommended approaches", "optimal methods", "industry standards"],
            "how to": ["steps to", "guide for", "tutorial on"],
            "what is": ["definition of", "explanation of", "overview of"],
            "advantages": ["benefits", "pros", "strengths"],
            "disadvantages": ["drawbacks", "cons", "limitations"],
            "differences": ["comparison", "distinction between", "contrast between"],
            "examples": ["sample", "demonstration", "illustration"],
            "tutorial": ["guide", "walkthrough", "how-to"],
            "problem": ["issue", "challenge", "difficulty"],
            "solution": ["fix", "resolution", "answer"],
            "configure": ["setup", "set up", "configure"],
            "install": ["installation", "setup", "deploy"],
            "error": ["bug", "issue", "problem"],
            "optimize": ["improve", "enhance", "performance tuning"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Generate multiple perspective variations of the query.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            QueryProcessingResult with multiple query perspectives
        """
        query: str = input_data.get("query", "")
        num_variations: int = config.get("num_variations", 3)
        custom_mappings: dict = config.get("custom_perspective_mappings", {})

        if not query:
            return QueryProcessingResult(
                processed_queries=[],
                original_query=query,
                processing_method="multi_query:perspective_variation",
                metadata={"error": "Empty query"},
            )

        # Merge custom mappings with defaults
        mappings = {**self._perspective_mappings, **custom_mappings}

        # Start with original query
        variations = [
            ProcessedQuery(query=query, method="original", original_query=query, score=1.0)
        ]

        query_lower = query.lower()

        # Generate variations by replacing perspective phrases
        for phrase, alternatives in mappings.items():
            if phrase in query_lower and len(variations) < num_variations + 1:
                for alt in alternatives:
                    if len(variations) >= num_variations + 1:
                        break

                    # Create variation by replacing phrase
                    varied_query = query_lower.replace(phrase, alt)

                    # Preserve original capitalization pattern
                    if query[0].isupper():
                        varied_query = varied_query.capitalize()

                    variations.append(
                        ProcessedQuery(
                            query=varied_query,
                            method="perspective_variation",
                            original_query=query,
                            metadata={"replaced_phrase": phrase, "alternative": alt},
                            score=0.8,
                        )
                    )

        # If no variations were generated, create some generic rephrasing
        if len(variations) == 1:
            variations.extend(self._generate_generic_variations(query, num_variations))

        # Limit to requested number + original
        variations = variations[: num_variations + 1]

        return QueryProcessingResult(
            processed_queries=variations,
            original_query=query,
            processing_method="multi_query:perspective_variation",
            metadata={
                "num_variations": len(variations) - 1,
                "requested_variations": num_variations,
            },
        )

    def _generate_generic_variations(self, query: str, num_variations: int) -> list[ProcessedQuery]:
        """Generate generic variations when no specific mappings match.

        Args:
            query: Original query
            num_variations: Number of variations to generate

        Returns:
            List of ProcessedQuery variations
        """
        variations = []
        templates = [
            "Tell me about {query}",
            "I need information on {query}",
            "Can you explain {query}",
            "What can you tell me about {query}",
            "Help me understand {query}",
        ]

        for _i, template in enumerate(templates[:num_variations]):
            variations.append(
                ProcessedQuery(
                    query=template.format(query=query),
                    method="generic_variation",
                    original_query=query,
                    metadata={"template": template},
                    score=0.6,
                )
            )

        return variations

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {"num_variations": 3, "custom_perspective_mappings": {}}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "num_variations" in config:
            if not isinstance(config["num_variations"], int) or config["num_variations"] < 1:
                return False
        if "custom_perspective_mappings" in config:
            if not isinstance(config["custom_perspective_mappings"], dict):
                return False
        return True
