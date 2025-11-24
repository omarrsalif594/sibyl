"""
Basic complexity scorer for core plugin system.

This scorer uses simple metrics to assess code complexity:
- Line count
- Character count
- Basic structural metrics
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.core.protocols.rag_pipeline.code_processing import CodeType

logger = logging.getLogger(__name__)


# Module-level config cache
_SCORER_CONFIG: dict[str, Any] | None = None


def _get_scorer_config() -> dict[str, Any]:
    """Get cached scorer configuration."""
    global _SCORER_CONFIG
    if _SCORER_CONFIG is None:
        config_path = Path(__file__).parent / "scorer_config.yaml"
        try:
            if config_path.exists():
                with open(config_path) as f:
                    _SCORER_CONFIG = yaml.safe_load(f) or {}
            else:
                _SCORER_CONFIG = {}
        except Exception as e:
            logger.warning("Failed to load scorer config: %s", e)
            _SCORER_CONFIG = {}

    return _SCORER_CONFIG


class BasicComplexityScorer:
    """
    Generic complexity scorer using simple metrics.

    Assigns complexity levels (low/medium/high) based on:
    - Content length
    - Line count
    - Basic structural indicators
    """

    def __init__(
        self,
        low_threshold_lines: int | None = None,
        medium_threshold_lines: int | None = None,
        low_threshold_chars: int | None = None,
        medium_threshold_chars: int | None = None,
    ) -> None:
        """
        Initialize the basic complexity scorer.

        Args:
            low_threshold_lines: Lines below this = low complexity (loads from config if None)
            medium_threshold_lines: Lines below this = medium complexity (loads from config if None)
            low_threshold_chars: Characters below this = low complexity (loads from config if None)
            medium_threshold_chars: Characters below this = medium complexity (loads from config if None)
        """
        # Load from config if not provided
        config = _get_scorer_config()
        thresholds = config.get("complexity_thresholds", {})

        self.low_threshold_lines = (
            low_threshold_lines
            if low_threshold_lines is not None
            else thresholds.get("low_threshold_lines", 20)
        )
        self.medium_threshold_lines = (
            medium_threshold_lines
            if medium_threshold_lines is not None
            else thresholds.get("medium_threshold_lines", 100)
        )
        self.low_threshold_chars = (
            low_threshold_chars
            if low_threshold_chars is not None
            else thresholds.get("low_threshold_chars", 500)
        )
        self.medium_threshold_chars = (
            medium_threshold_chars
            if medium_threshold_chars is not None
            else thresholds.get("medium_threshold_chars", 3000)
        )

    def supports(self, code_type: CodeType) -> bool:
        """Support TEXT, MARKDOWN, and SQL types."""
        return code_type in (CodeType.TEXT, CodeType.MARKDOWN, CodeType.SQL)

    def score(self, code: str, code_type: CodeType, **opts) -> dict[str, Any]:
        """
        Score code complexity using basic metrics.

        Args:
            code: The code to score
            code_type: Type of code being scored
            **opts: Optional overrides for thresholds

        Returns:
            Dictionary with:
            - level: "low" | "medium" | "high"
            - metrics: Dict of measurements
        """
        if not self.supports(code_type):
            return {
                "level": "unknown",
                "metrics": {},
                "error": f"BasicComplexityScorer does not support {code_type}",
            }

        # Calculate basic metrics
        lines = code.split("\n")
        num_lines = len(lines)
        num_chars = len(code)
        num_words = len(code.split())
        non_empty_lines = len([line for line in lines if line.strip()])

        metrics = {
            "num_lines": num_lines,
            "num_chars": num_chars,
            "num_words": num_words,
            "non_empty_lines": non_empty_lines,
            "avg_line_length": num_chars / num_lines if num_lines > 0 else 0,
        }

        # Add code-type specific metrics
        if code_type == CodeType.SQL:
            metrics.update(self._sql_metrics(code))
        elif code_type == CodeType.MARKDOWN:
            metrics.update(self._markdown_metrics(code))

        # Determine complexity level
        level = self._calculate_level(num_lines, num_chars, metrics, opts)

        return {"level": level, "metrics": metrics}

    def _calculate_level(
        self, num_lines: int, num_chars: int, metrics: dict[str, Any], opts: dict[str, Any]
    ) -> str:
        """
        Calculate complexity level from metrics.

        Args:
            num_lines: Number of lines
            num_chars: Number of characters
            metrics: Additional metrics
            opts: Optional threshold overrides

        Returns:
            "low", "medium", or "high"
        """
        low_lines = opts.get("low_threshold_lines", self.low_threshold_lines)
        med_lines = opts.get("medium_threshold_lines", self.medium_threshold_lines)
        low_chars = opts.get("low_threshold_chars", self.low_threshold_chars)
        med_chars = opts.get("medium_threshold_chars", self.medium_threshold_chars)

        # Use both line and character counts
        line_score = 0
        if num_lines < low_lines:
            line_score = 1
        elif num_lines < med_lines:
            line_score = 2
        else:
            line_score = 3

        char_score = 0
        if num_chars < low_chars:
            char_score = 1
        elif num_chars < med_chars:
            char_score = 2
        else:
            char_score = 3

        # Take the higher score (more conservative)
        final_score = max(line_score, char_score)

        # Adjust based on code-specific metrics from config
        config = _get_scorer_config()
        sql_indicators = config.get("sql_complexity_indicators", {})
        max_joins = sql_indicators.get("max_joins_before_high", 5)
        max_subqueries = sql_indicators.get("max_subqueries_before_high", 3)

        if "join_count" in metrics and metrics["join_count"] > max_joins:
            final_score = max(final_score, 3)
        if "subquery_count" in metrics and metrics["subquery_count"] > max_subqueries:
            final_score = max(final_score, 3)

        if final_score == 1:
            return "low"
        if final_score == 2:
            return "medium"
        return "high"

    def _sql_metrics(self, sql: str) -> dict[str, Any]:
        """
        Calculate SQL-specific metrics.

        Args:
            sql: SQL code

        Returns:
            Dictionary of SQL metrics
        """
        sql_upper = sql.upper()

        return {
            "join_count": sql_upper.count(" JOIN "),
            "subquery_count": sql_upper.count("SELECT") - 1,  # Rough estimate
            "where_clauses": sql_upper.count(" WHERE "),
            "group_by_count": sql_upper.count(" GROUP BY "),
            "has_cte": "WITH" in sql_upper,
        }

    def _markdown_metrics(self, markdown: str) -> dict[str, Any]:
        """
        Calculate markdown-specific metrics.

        Args:
            markdown: Markdown content

        Returns:
            Dictionary of markdown metrics
        """
        lines = markdown.split("\n")

        heading_count = sum(1 for line in lines if line.strip().startswith("#"))
        code_block_count = markdown.count("```") // 2
        link_count = markdown.count("[") + markdown.count("](")

        return {
            "heading_count": heading_count,
            "code_block_count": code_block_count,
            "link_count": link_count,
        }
