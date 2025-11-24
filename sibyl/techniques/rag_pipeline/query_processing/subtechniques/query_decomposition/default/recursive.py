"""Recursive query decomposition implementation.

This implementation breaks complex queries into sub-queries using simple heuristics.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class RecursiveDecomposition:
    """Recursive query decomposition implementation."""

    def __init__(self) -> None:
        self._name = "recursive"
        self._description = "Break complex queries into sub-queries"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

        # Conjunctions that indicate query can be split
        self._split_patterns = [
            r"\s+and\s+",
            r"\s+or\s+",
            r",\s+",
            r";\s*",
            r"\s+then\s+",
            r"\s+also\s+",
            r"\s+plus\s+",
        ]

        # Question patterns for creating sub-queries
        self._question_starters = [
            "how do i",
            "how to",
            "what is",
            "what are",
            "when should",
            "where can",
            "why does",
            "which",
            "can i",
            "should i",
        ]

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Decompose complex query into sub-queries.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            QueryProcessingResult with decomposed sub-queries
        """
        query: str = input_data.get("query", "")
        max_subqueries: int = config.get("max_subqueries", 5)
        min_subquery_length: int = config.get("min_subquery_length", 10)

        if not query:
            return QueryProcessingResult(
                processed_queries=[],
                original_query=query,
                processing_method="query_decomposition:recursive",
                metadata={"error": "Empty query"},
            )

        # Try to decompose the query
        subqueries = self._decompose_query(query, max_subqueries, min_subquery_length)

        # If decomposition didn't produce multiple queries, return original
        if len(subqueries) <= 1:
            return QueryProcessingResult(
                processed_queries=[
                    ProcessedQuery(
                        query=query, method="no_decomposition", original_query=query, score=1.0
                    )
                ],
                original_query=query,
                processing_method="query_decomposition:recursive",
                metadata={"decomposed": False, "reason": "No decomposition patterns found"},
            )

        # Convert sub-queries to ProcessedQuery objects
        processed = []
        for i, subq in enumerate(subqueries):
            processed.append(
                ProcessedQuery(
                    query=subq,
                    method="recursive_decomposition",
                    original_query=query,
                    metadata={"subquery_index": i},
                    score=1.0 / (i + 1),  # Higher score for earlier sub-queries
                )
            )

        return QueryProcessingResult(
            processed_queries=processed,
            original_query=query,
            processing_method="query_decomposition:recursive",
            metadata={"decomposed": True, "num_subqueries": len(subqueries)},
        )

    def _decompose_query(self, query: str, max_subqueries: int, min_length: int) -> list[str]:
        """Decompose query into sub-queries.

        Args:
            query: Original query
            max_subqueries: Maximum number of sub-queries to generate
            min_length: Minimum length for a sub-query

        Returns:
            List of sub-queries
        """
        subqueries = []

        # First, try splitting by conjunctions
        query_lower = query.lower()

        # Try each split pattern
        for pattern in self._split_patterns:
            parts = re.split(pattern, query, flags=re.IGNORECASE)
            if len(parts) > 1:
                # Found a valid split
                subqueries = self._process_split_parts(parts, query_lower, min_length)
                if len(subqueries) > 1:
                    break

        # If no split worked, try detecting multiple questions
        if len(subqueries) <= 1:
            subqueries = self._detect_multiple_questions(query)

        # Limit to max_subqueries
        return subqueries[:max_subqueries]

    def _process_split_parts(
        self, parts: list[str], original_lower: str, min_length: int
    ) -> list[str]:
        """Process split parts into valid sub-queries.

        Args:
            parts: Split parts from regex
            original_lower: Original query in lowercase
            min_length: Minimum length for sub-query

        Returns:
            List of processed sub-queries
        """
        subqueries = []

        # Detect if original query has a question starter
        question_prefix = ""
        for starter in self._question_starters:
            if original_lower.startswith(starter):
                question_prefix = starter
                break

        for part in parts:
            part = part.strip()
            if len(part) < min_length:
                continue

            # If part doesn't start with a question word, try to add context
            part_lower = part.lower()
            has_question_word = any(
                part_lower.startswith(starter) for starter in self._question_starters
            )

            if not has_question_word and question_prefix:
                # Inherit question prefix from original query
                if not part_lower.startswith(question_prefix):
                    # Check if the part already makes sense standalone
                    if "?" not in part:
                        part = f"{question_prefix.title()} {part}"

            # Ensure it ends with question mark if it looks like a question
            if (has_question_word or question_prefix) and not part.endswith("?"):
                part = part + "?"

            subqueries.append(part)

        return subqueries

    def _detect_multiple_questions(self, query: str) -> list[str]:
        """Detect multiple questions in a single query string.

        Args:
            query: Original query

        Returns:
            List of detected questions
        """
        # Split by question marks
        potential_questions = re.split(r"\?+", query)
        questions = []

        for q in potential_questions:
            q = q.strip()
            if len(q) > 10:  # Minimum length check
                if not q.endswith("?"):
                    q = q + "?"
                questions.append(q)

        # If we found multiple questions, return them
        if len(questions) > 1:
            return questions

        # Otherwise return original
        return [query]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {"max_subqueries": 5, "min_subquery_length": 10}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "max_subqueries" in config:
            if not isinstance(config["max_subqueries"], int) or config["max_subqueries"] < 1:
                return False
        if "min_subquery_length" in config:
            if (
                not isinstance(config["min_subquery_length"], int)
                or config["min_subquery_length"] < 1
            ):
                return False
        return True
