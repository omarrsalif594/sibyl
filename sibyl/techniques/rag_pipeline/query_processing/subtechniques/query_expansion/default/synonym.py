"""Synonym expansion implementation for query expansion.

This implementation expands queries by adding synonyms from a configurable dictionary.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.query_processing.protocols import (
    ProcessedQuery,
    QueryProcessingResult,
)


class SynonymExpansion:
    """Synonym-based query expansion implementation."""

    def __init__(self) -> None:
        self._name = "synonym"
        self._description = "Expand queries using synonym dictionaries"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        # Simple synonym dictionary for common terms
        self._default_synonyms = {
            "search": ["find", "lookup", "locate"],
            "retrieve": ["get", "fetch", "obtain"],
            "data": ["information", "records", "content"],
            "document": ["file", "record", "item"],
            "system": ["platform", "application", "service"],
            "user": ["person", "individual", "account"],
            "create": ["make", "generate", "produce"],
            "delete": ["remove", "eliminate", "erase"],
            "update": ["modify", "change", "edit"],
            "error": ["issue", "problem", "bug"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> QueryProcessingResult:
        """Expand query using synonyms.

        Args:
            input_data: Dict with 'query' key
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            QueryProcessingResult with expanded queries
        """
        query: str = input_data.get("query", "")
        max_expansions: int = config.get("max_expansions", 3)
        custom_synonyms: dict = config.get("custom_synonyms", {})

        if not query:
            return QueryProcessingResult(
                processed_queries=[],
                original_query=query,
                processing_method="query_expansion:synonym",
                metadata={"error": "Empty query"},
            )

        # Merge custom synonyms with defaults
        synonyms = {**self._default_synonyms, **custom_synonyms}

        # Find synonyms in query
        words = query.lower().split()
        expanded_queries = [ProcessedQuery(query=query, method="original", original_query=query)]

        for word in words:
            if word in synonyms and len(expanded_queries) < max_expansions:
                # Create variations with synonyms
                for synonym in synonyms[word][: max_expansions - len(expanded_queries)]:
                    expanded_query = query.replace(word, synonym, 1)
                    expanded_queries.append(
                        ProcessedQuery(
                            query=expanded_query,
                            method="synonym_expansion",
                            original_query=query,
                            metadata={"replaced_word": word, "synonym": synonym},
                        )
                    )

        return QueryProcessingResult(
            processed_queries=expanded_queries,
            original_query=query,
            processing_method="query_expansion:synonym",
            metadata={
                "max_expansions": max_expansions,
                "total_expansions": len(expanded_queries) - 1,
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {"max_expansions": 3, "custom_synonyms": {}}

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "max_expansions" in config and config["max_expansions"] < 1:
            return False
        return not ("custom_synonyms" in config and not isinstance(config["custom_synonyms"], dict))
