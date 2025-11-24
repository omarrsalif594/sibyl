"""Template-based query rewriting implementation.

This implementation rewrites queries using predefined templates to improve retrieval.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class TemplateRewriting:
    """Template-based query rewriting implementation."""

    def __init__(self) -> None:
        self._name = "template"
        self._description = "Rewrite queries using template-based patterns"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

        # Common query templates for rewriting
        self._templates = {
            "how_to": {
                "patterns": [r"^how (do|can|to) (.+)", r"^how (.+)"],
                "template": "How to {action}?",
            },
            "what_is": {
                "patterns": [r"^what is (.+)", r"^what are (.+)"],
                "template": "What is {concept}?",
            },
            "why": {"patterns": [r"^why (.+)", r"^why does (.+)"], "template": "Why {question}?"},
            "when": {"patterns": [r"^when (.+)", r"^when to (.+)"], "template": "When {question}?"},
            "where": {
                "patterns": [r"^where (.+)", r"^where is (.+)"],
                "template": "Where {question}?",
            },
            "best_practices": {
                "patterns": [r"(.+) best practices", r"best (.+)", r"(.+) recommendations"],
                "template": "What are the best practices for {topic}?",
            },
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Rewrite query using templates.

        Args:
            input_data: Dict with 'query' and optional 'context' keys
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            QueryProcessingResult with rewritten query
        """
        query: str = input_data.get("query", "")
        input_data.get("context")
        enable_templates: bool = config.get("enable_templates", True)
        custom_templates: dict = config.get("custom_templates", {})

        if not query:
            return QueryProcessingResult(
                processed_queries=[],
                original_query=query,
                processing_method="query_rewriting:template",
                metadata={"error": "Empty query"},
            )

        # If templates disabled, return original
        if not enable_templates:
            return QueryProcessingResult(
                processed_queries=[
                    ProcessedQuery(query=query, method="no_rewrite", original_query=query)
                ],
                original_query=query,
                processing_method="query_rewriting:template",
                metadata={"templates_enabled": False},
            )

        # Merge custom templates with defaults
        templates = {**self._templates, **custom_templates}

        # Try to match and rewrite query
        query_lower = query.lower().strip()
        rewritten_query = query
        matched_template = None

        for template_name, template_info in templates.items():
            patterns = template_info.get("patterns", [])
            template_str = template_info.get("template", "")

            for pattern in patterns:
                match = re.match(pattern, query_lower)
                if match:
                    # Extract captured groups
                    groups = match.groups()
                    if groups:
                        # Use first group as the main content
                        content = groups[0] if len(groups) == 1 else " ".join(groups)

                        # Format template
                        if "{action}" in template_str:
                            rewritten_query = template_str.format(action=content)
                        elif "{concept}" in template_str:
                            rewritten_query = template_str.format(concept=content)
                        elif "{question}" in template_str:
                            rewritten_query = template_str.format(question=content)
                        elif "{topic}" in template_str:
                            rewritten_query = template_str.format(topic=content)

                        matched_template = template_name
                        break

            if matched_template:
                break

        return QueryProcessingResult(
            processed_queries=[
                ProcessedQuery(
                    query=rewritten_query,
                    method="template_rewriting",
                    original_query=query,
                    metadata={
                        "matched_template": matched_template,
                        "was_rewritten": rewritten_query != query,
                    },
                )
            ],
            original_query=query,
            processing_method="query_rewriting:template",
            metadata={
                "matched_template": matched_template,
                "was_rewritten": rewritten_query != query,
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {"enable_templates": True, "custom_templates": {}}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "enable_templates" in config and not isinstance(config["enable_templates"], bool):
            return False
        return not (
            "custom_templates" in config and not isinstance(config["custom_templates"], dict)
        )
