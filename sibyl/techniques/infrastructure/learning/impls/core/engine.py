"""Learning engine for pattern discovery and recommendations.

This module analyzes learning records to:
- Discover new error patterns from unknown errors
- Recommend new keywords for existing categories
- Suggest new error categories
- Auto-update error_patterns.yml with high-confidence patterns

Example:
    from sibyl.mcp_server.infrastructure.learning import (
        LearningEngine,
        get_learning_store,
    )

    engine = LearningEngine(store=get_learning_store())

    # Discover patterns from unknown errors
    recommendations = engine.discover_patterns(
        min_frequency=3,
        min_success_rate=0.7,
    )

    # Apply high-confidence recommendations
    for rec in recommendations:
        if rec.confidence > 0.8:
            engine.apply_recommendation(rec)
"""

import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available, auto-update disabled")

from sibyl.mcp_server.infrastructure.learning.protocol import (
    FixOutcome,
    LearningStore,
    PatternRecommendation,
)

logger = logging.getLogger(__name__)

# Load learning technique configuration for default thresholds
try:
    from sibyl.techniques.infrastructure.learning import LearningTechnique

    _learning_technique = LearningTechnique()

    # Load config file
    config_path = (
        Path(__file__).parent.parent.parent.parent / "techniques" / "learning" / "config.yaml"
    )
    if config_path.exists():
        with open(config_path) as f:
            _learning_config = yaml.safe_load(f) if YAML_AVAILABLE else {}
    else:
        _learning_config = {}
except Exception as e:
    logger.warning("Failed to load learning technique config: %s", e)
    _learning_config = {}


class LearningEngine:
    """Engine for discovering patterns and making recommendations."""

    def __init__(
        self,
        store: LearningStore,
        error_patterns_file: Path | None = None,
    ) -> None:
        """Initialize learning engine.

        Args:
            store: Learning store implementation
            error_patterns_file: Path to error_patterns.yml (for auto-update)
        """
        self.store = store
        self.error_patterns_file = error_patterns_file or self._get_default_patterns_file()

    def _get_default_patterns_file(self) -> Path:
        """Get default path to error_patterns.yml."""
        return Path(__file__).parent.parent / "quality_control" / "error_patterns.yml"

    def discover_patterns(
        self,
        min_frequency: int | None = None,
        min_success_rate: float | None = None,
    ) -> list[PatternRecommendation]:
        """Discover new error patterns from unknown errors.

        Analyzes unknown error records to find common patterns.

        Args:
            min_frequency: Minimum times pattern must appear (defaults from technique: 3)
            min_success_rate: Minimum success rate for fixes (defaults from technique: 0.6)

        Returns:
            List of pattern recommendations
        """
        # Use technique configuration as defaults
        # Configuration source: sibyl/techniques/learning/config.yaml
        if min_frequency is None:
            pattern_config = _learning_config.get("pattern_discovery", {})
            min_frequency = pattern_config.get("min_frequency", 3)

        if min_success_rate is None:
            pattern_config = _learning_config.get("pattern_discovery", {})
            min_success_rate = pattern_config.get("min_success_rate", 0.6)
        # Get unknown error records
        unknown_records = self.store.list_records(category="unknown", limit=1000)

        if not unknown_records:
            logger.info("No unknown errors to analyze")
            return []

        logger.info("Analyzing %s unknown error records", len(unknown_records))

        # Extract common keywords from error messages
        keyword_counter = Counter()
        error_groups = defaultdict(list)

        for record in unknown_records:
            keywords = self._extract_keywords(record.error_message)
            for keyword in keywords:
                keyword_counter[keyword] += 1

            # Group by similar keywords
            key = tuple(sorted(keywords[:3]))  # Use top 3 keywords as key
            error_groups[key].append(record)

        # Generate recommendations for frequent patterns
        recommendations = []

        for keyword_tuple, records in error_groups.items():
            if len(records) < min_frequency:
                continue

            # Calculate success rate for fixes
            success_count = sum(1 for r in records if r.outcome == FixOutcome.SUCCESS)
            total_count = len(records)
            success_rate = success_count / total_count if total_count > 0 else 0.0

            if success_rate < min_success_rate:
                continue

            # Extract suggested fixes from successful records
            successful_fixes = [
                r.fix_applied for r in records if r.outcome == FixOutcome.SUCCESS and r.fix_applied
            ]

            # Deduplicate and get most common
            fix_counter = Counter(successful_fixes)
            top_fixes = [fix for fix, count in fix_counter.most_common(5)]

            # Generate category name from keywords
            category_name = self._generate_category_name(list(keyword_tuple))

            # Calculate confidence
            confidence = min(1.0, (success_rate + (total_count / 20)) / 2)

            recommendation = PatternRecommendation(
                category=category_name,
                keywords=list(keyword_tuple),
                suggested_fixes=top_fixes,
                confidence=confidence,
                supporting_records=[r.record_id for r in records],
                frequency=total_count,
                success_rate=success_rate,
            )

            recommendations.append(recommendation)

        # Sort by confidence
        recommendations.sort(key=lambda r: r.confidence, reverse=True)

        logger.info("Discovered %s pattern recommendations", len(recommendations))

        return recommendations

    def recommend_keyword_additions(
        self,
        category: str,
        min_frequency: int | None = None,
    ) -> list[str]:
        """Recommend new keywords to add to existing category.

        Analyzes successful fixes for a category to find keywords
        that should be added to improve classification.

        Args:
            category: Error category to analyze
            min_frequency: Minimum frequency for keyword (defaults from technique: 5)

        Returns:
            List of recommended keywords
        """
        # Use technique configuration as default
        # Configuration source: sibyl/techniques/learning/config.yaml
        if min_frequency is None:
            keyword_config = _learning_config.get("keyword_recommendation", {})
            min_frequency = keyword_config.get("min_frequency", 5)
        # Get successful records for category
        records = self.store.list_records(
            category=category,
            outcome=FixOutcome.SUCCESS,
            limit=500,
        )

        if not records:
            return []

        # Extract keywords that weren't matched but should have been
        keyword_counter = Counter()

        for record in records:
            # Get all keywords from error message
            all_keywords = self._extract_keywords(record.error_message)

            # Find keywords that weren't matched
            unmatched = [
                kw
                for kw in all_keywords
                if kw.lower() not in [mk.lower() for mk in record.matched_keywords]
            ]

            keyword_counter.update(unmatched)

        # Get frequent unmatched keywords
        # Use technique config for max recommendations (default 20)
        keyword_config = _learning_config.get("keyword_recommendation", {})
        max_recommendations = keyword_config.get("max_recommendations", 20)

        recommended = [
            keyword
            for keyword, count in keyword_counter.most_common(max_recommendations)
            if count >= min_frequency
        ]

        logger.info("Recommended %s new keywords for category %s", len(recommended), category)

        return recommended

    def apply_recommendation(
        self,
        recommendation: PatternRecommendation,
        dry_run: bool = False,
    ) -> bool:
        """Apply a pattern recommendation to error_patterns.yml.

        Args:
            recommendation: Pattern recommendation to apply
            dry_run: If True, don't actually update file

        Returns:
            True if applied successfully
        """
        if not YAML_AVAILABLE:
            logger.error("PyYAML not available, cannot update patterns")
            return False

        if not self.error_patterns_file.exists():
            logger.error("Error patterns file not found: %s", self.error_patterns_file)
            return False

        try:
            # Load current patterns
            with open(self.error_patterns_file) as f:
                config = yaml.safe_load(f)

            if not config or "error_patterns" not in config:
                logger.error("Invalid error_patterns.yml format")
                return False

            # Check if category already exists
            if recommendation.category in config["error_patterns"]:
                logger.info("Category %s already exists, merging", recommendation.category)

                # Merge keywords and fixes
                existing = config["error_patterns"][recommendation.category]
                existing_keywords = existing.get("keywords", [])
                existing_fixes = existing.get("suggested_fixes", [])

                # Add new unique keywords
                new_keywords = [kw for kw in recommendation.keywords if kw not in existing_keywords]
                existing_keywords.extend(new_keywords)

                # Add new unique fixes
                new_fixes = [
                    fix for fix in recommendation.suggested_fixes if fix not in existing_fixes
                ]
                existing_fixes.extend(new_fixes)

                config["error_patterns"][recommendation.category]["keywords"] = existing_keywords
                config["error_patterns"][recommendation.category]["suggested_fixes"] = (
                    existing_fixes
                )

            else:
                # Add new category
                logger.info("Adding new category: %s", recommendation.category)

                config["error_patterns"][recommendation.category] = {
                    "priority": 50,  # Default priority for learned patterns
                    "keywords": recommendation.keywords,
                    "suggested_fixes": recommendation.suggested_fixes,
                }

            if dry_run:
                logger.info("Dry run - would update error_patterns.yml")
                return True

            # Write updated patterns
            with open(self.error_patterns_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info("Updated error_patterns.yml with %s", recommendation.category)

            return True

        except Exception as e:
            logger.exception("Failed to apply recommendation: %s", e)
            return False

    def update_historical_success(self) -> dict[str, list[dict]]:
        """Update historical_success_patterns in error_patterns.yml.

        Returns:
            Dictionary of historical patterns by category
        """
        historical_patterns = {}

        # Get all categories
        stats = self.store.get_statistics()
        categories = stats.get("category_counts", {}).keys()

        for category in categories:
            if category == "unknown":
                continue

            # Get successful fix patterns
            # Use technique config for min success rate (default 0.7)
            historical_config = _learning_config.get("historical_patterns", {})
            min_success_rate = historical_config.get("min_success_rate", 0.7)

            patterns = self.store.get_success_patterns(
                category=category,
                min_success_rate=min_success_rate,
            )

            if patterns:
                historical_patterns[category] = patterns

        # Update error_patterns.yml if YAML available
        if YAML_AVAILABLE and self.error_patterns_file.exists():
            try:
                with open(self.error_patterns_file) as f:
                    config = yaml.safe_load(f)

                config["historical_success_patterns"] = historical_patterns

                with open(self.error_patterns_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                logger.info("Updated historical_success_patterns in error_patterns.yml")

            except Exception as e:
                logger.exception("Failed to update historical patterns: %s", e)

        return historical_patterns

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract potential keywords from text.

        Args:
            text: Error message or text

        Returns:
            List of keywords
        """
        # Convert to lowercase
        text_lower = text.lower()

        # Common error-related keywords
        common_keywords = [
            "error",
            "failed",
            "failure",
            "exception",
            "invalid",
            "not found",
            "missing",
            "undefined",
            "cannot",
            "unable",
            "unexpected",
            "syntax",
            "compilation",
            "runtime",
            "timeout",
            "permission",
            "denied",
            "forbidden",
            "quota",
            "exceeded",
            "type",
            "mismatch",
            "cast",
            "signature",
            "column",
            "table",
            "schema",
            "dataset",
            "relation",
            "macro",
            "jinja",
            "template",
            "ref",
            "source",
            "incremental",
            "merge",
            "timestamp",
            "datetime",
            "date",
            "string",
            "integer",
            "float",
        ]

        # Find matching keywords
        found_keywords = [kw for kw in common_keywords if kw in text_lower]

        # Also extract quoted strings (often contain important identifiers)
        quoted_matches = re.findall(r"['\"]([^'\"]+)['\"]", text)
        # Limit to short strings (likely to be identifiers, not full error messages)
        quoted_keywords = [m for m in quoted_matches if len(m) < 30]

        # Combine and deduplicate
        all_keywords = list(set(found_keywords + quoted_keywords))

        return all_keywords[:10]  # Return top 10

    def _generate_category_name(self, keywords: list[str]) -> str:
        """Generate a category name from keywords.

        Args:
            keywords: List of keywords

        Returns:
            Category name in snake_case
        """
        # Take first 2-3 keywords
        primary_keywords = keywords[:3]

        # Clean and join
        cleaned = [kw.lower().replace(" ", "_") for kw in primary_keywords]

        # Create name
        category_name = "_".join(cleaned)

        # Limit length
        if len(category_name) > 40:
            category_name = category_name[:40]

        return category_name

    def get_learning_summary(self) -> dict[str, Any]:
        """Get summary of learning activity.

        Returns:
            Dictionary with learning statistics and insights
        """
        stats = self.store.get_statistics()

        # Get top categories by frequency
        category_counts = stats.get("category_counts", {})
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Get unknown error rate
        total = stats.get("total_records", 0)
        unknown_count = category_counts.get("unknown", 0)
        unknown_rate = unknown_count / total if total > 0 else 0.0

        return {
            "total_records": total,
            "success_rate": stats.get("success_rate", 0.0),
            "unknown_rate": unknown_rate,
            "top_categories": [{"category": cat, "count": count} for cat, count in top_categories],
            "recommendations_available": len(self.discover_patterns()),
        }
