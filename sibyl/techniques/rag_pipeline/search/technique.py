"""Search technique for search and retrieval operations.

This technique orchestrates vector search, keyword search, and hybrid search
to provide comprehensive search capabilities.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique
from sibyl.techniques.rag_pipeline.search.protocols import SearchResponse

logger = logging.getLogger(__name__)


class SearchTechnique(BaseTechnique):
    """Search technique for search and retrieval operations."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "search"
        self._description = "Search and retrieval mechanisms"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}
        self._technique_config = self.load_config(self._config_path)
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def subtechniques(self) -> dict[str, dict[str, BaseSubtechnique]]:
        return self._subtechniques

    def register_subtechnique(
        self,
        subtechnique: BaseSubtechnique,
        subtechnique_name: str,
        implementation: str = "default",
    ) -> None:
        """Register a subtechnique implementation.

        Args:
            subtechnique: Subtechnique instance to register
            subtechnique_name: Name of the subtechnique category
            implementation: Implementation variant name
        """
        if subtechnique_name not in self._subtechniques:
            self._subtechniques[subtechnique_name] = {}

        self._subtechniques[subtechnique_name][implementation] = subtechnique
        logger.debug("Registered %s:%s", subtechnique_name, implementation)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict | None = None,
        **kwargs,
    ) -> SearchResponse:
        """Execute search technique.

        Args:
            input_data: Input data for search
            subtechnique: Subtechnique name (vector_search, keyword_search, hybrid_search)
            implementation: Implementation name
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            SearchResponse from subtechnique execution
        """
        # Validate subtechnique exists
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique: {subtechnique}. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        if implementation not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown implementation '{implementation}' for subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        # Get subtechnique instance
        subtechnique_instance = self._subtechniques[subtechnique][implementation]

        # Build configuration cascade
        subtechnique_config = subtechnique_instance.get_config()
        cascade = ConfigCascade(
            global_config=config or {},
            technique_config=self._technique_config,
            subtechnique_config=subtechnique_config,
        )
        merged_config = cascade.merge()

        # Validate configuration
        if not subtechnique_instance.validate_config(merged_config):
            msg = f"Invalid configuration for {subtechnique}:{implementation}"
            raise ValueError(msg)

        # Execute subtechnique
        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=implementation,
            input_data=input_data,
            config=merged_config,
            executor=lambda: subtechnique_instance.execute(input_data, merged_config),
        )

    def load_config(self, config_path: Path) -> dict[str, Any]:
        """Load technique configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_config(self) -> dict[str, Any]:
        """Get technique configuration.

        Returns:
            Technique configuration dictionary
        """
        return self._technique_config.copy()

    def list_subtechniques(self) -> list[str]:
        """List available subtechniques.

        Returns:
            List of subtechnique names
        """
        return list(self._subtechniques.keys())

    def _discover_subtechniques(self) -> None:
        """Auto-discover and register subtechniques."""
        base_path = Path(__file__).parent / "subtechniques"

        if not base_path.exists():
            logger.warning("Subtechniques directory not found: %s", base_path)
            return

        # Discover vector_search subtechniques
        self._discover_subtechnique_category("vector_search", base_path)

        # Discover keyword_search subtechniques
        self._discover_subtechnique_category("keyword_search", base_path)

        # Discover hybrid_search subtechniques
        self._discover_subtechnique_category("hybrid_search", base_path)

    def _discover_subtechnique_category(self, category: str, base_path: Path) -> None:
        """Discover implementations for a specific subtechnique category.

        Args:
            category: Subtechnique category name
            base_path: Base path for subtechniques
        """
        category_path = base_path / category / "default"

        if not category_path.exists():
            logger.debug("No default implementations found for %s", category)
            return

        # Import and register default implementations
        if category == "vector_search":
            self._register_vector_search(category_path)
        elif category == "keyword_search":
            self._register_keyword_search(category_path)
        elif category == "hybrid_search":
            self._register_hybrid_search(category_path)

    def _register_vector_search(self, path: Path) -> None:
        """Register vector search implementations."""
        try:
            from sibyl.techniques.rag_pipeline.search.subtechniques.vector_search.default.duckdb import (  # plugin registration
                DuckDBVectorSearch,
            )

            self.register_subtechnique(DuckDBVectorSearch(), "vector_search", "duckdb")
            logger.info("Registered vector_search subtechniques")
        except Exception as e:
            logger.exception("Failed to register vector_search: %s", e)

    def _register_keyword_search(self, path: Path) -> None:
        """Register keyword search implementations."""
        try:
            from sibyl.techniques.rag_pipeline.search.subtechniques.keyword_search.default.bm25 import (  # plugin registration
                BM25Search,
            )

            self.register_subtechnique(BM25Search(), "keyword_search", "bm25")
            logger.info("Registered keyword_search subtechniques")
        except Exception as e:
            logger.exception("Failed to register keyword_search: %s", e)

    def _register_hybrid_search(self, path: Path) -> None:
        """Register hybrid search implementations."""
        try:
            from sibyl.techniques.rag_pipeline.search.subtechniques.hybrid_search.default.rrf import (  # plugin registration
                RRFHybridSearch,
            )

            self.register_subtechnique(RRFHybridSearch(), "hybrid_search", "rrf")
            logger.info("Registered hybrid_search subtechniques")
        except Exception as e:
            logger.exception("Failed to register hybrid_search: %s", e)
