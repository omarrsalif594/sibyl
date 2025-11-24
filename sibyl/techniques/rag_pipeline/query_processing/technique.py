"""Query processing technique for query transformation and enhancement.

This technique orchestrates query expansion, rewriting, multi-query generation,
HyDE, and query decomposition to enhance retrieval effectiveness.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique
from sibyl.techniques.rag_pipeline.query_processing.protocols import QueryProcessingResult

logger = logging.getLogger(__name__)


class QueryProcessingTechnique(BaseTechnique):
    """Query processing technique for query transformation and enhancement."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "query_processing"
        self._description = "Query transformation and enhancement"
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
    ) -> QueryProcessingResult:
        """Execute query processing technique.

        Args:
            input_data: Input data for query processing
            subtechnique: Subtechnique name (query_expansion, query_rewriting, etc.)
            implementation: Implementation name
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            QueryProcessingResult from subtechnique execution
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

        # Discover all subtechnique categories
        self._discover_subtechnique_category("query_expansion", base_path)
        self._discover_subtechnique_category("query_rewriting", base_path)
        self._discover_subtechnique_category("multi_query", base_path)
        self._discover_subtechnique_category("hyde", base_path)
        self._discover_subtechnique_category("query_decomposition", base_path)

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
        if category == "query_expansion":
            self._register_query_expansion(category_path)
        elif category == "query_rewriting":
            self._register_query_rewriting(category_path)
        elif category == "multi_query":
            self._register_multi_query(category_path)
        elif category == "hyde":
            self._register_hyde(category_path)
        elif category == "query_decomposition":
            self._register_query_decomposition(category_path)

    def _register_query_expansion(self, path: Path) -> None:
        """Register query expansion implementations."""
        try:
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_expansion.default.no_expansion import (  # plugin registration
                NoExpansion,
            )
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_expansion.default.synonym import (  # plugin registration
                SynonymExpansion,
            )

            self.register_subtechnique(SynonymExpansion(), "query_expansion", "synonym")
            self.register_subtechnique(NoExpansion(), "query_expansion", "no_expansion")
            logger.info("Registered query_expansion subtechniques")
        except Exception as e:
            logger.exception("Failed to register query_expansion: %s", e)

    def _register_query_rewriting(self, path: Path) -> None:
        """Register query rewriting implementations."""
        try:
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_rewriting.default.no_rewrite import (  # plugin registration
                NoRewrite,
            )
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_rewriting.default.template import (  # plugin registration
                TemplateRewriting,
            )

            self.register_subtechnique(TemplateRewriting(), "query_rewriting", "template")
            self.register_subtechnique(NoRewrite(), "query_rewriting", "no_rewrite")
            logger.info("Registered query_rewriting subtechniques")
        except Exception as e:
            logger.exception("Failed to register query_rewriting: %s", e)

    def _register_multi_query(self, path: Path) -> None:
        """Register multi-query generation implementations."""
        try:
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.multi_query.default.perspective_variation import (  # plugin registration
                PerspectiveVariation,
            )
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.multi_query.default.single import (  # plugin registration
                SingleQuery,
            )

            self.register_subtechnique(
                PerspectiveVariation(), "multi_query", "perspective_variation"
            )
            self.register_subtechnique(SingleQuery(), "multi_query", "single")
            logger.info("Registered multi_query subtechniques")
        except Exception as e:
            logger.exception("Failed to register multi_query: %s", e)

    def _register_hyde(self, path: Path) -> None:
        """Register HyDE implementations."""
        try:
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.hyde.default.disabled import (  # plugin registration
                DisabledHyDE,
            )
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.hyde.default.simple_hyde import (  # plugin registration
                SimpleHyDE,
            )

            self.register_subtechnique(SimpleHyDE(), "hyde", "simple_hyde")
            self.register_subtechnique(DisabledHyDE(), "hyde", "disabled")
            logger.info("Registered hyde subtechniques")
        except Exception as e:
            logger.exception("Failed to register hyde: %s", e)

    def _register_query_decomposition(self, path: Path) -> None:
        """Register query decomposition implementations."""
        try:
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_decomposition.default.no_decomp import (  # plugin registration
                NoDecomposition,
            )
            from sibyl.techniques.rag_pipeline.query_processing.subtechniques.query_decomposition.default.recursive import (  # plugin registration
                RecursiveDecomposition,
            )

            self.register_subtechnique(RecursiveDecomposition(), "query_decomposition", "recursive")
            self.register_subtechnique(NoDecomposition(), "query_decomposition", "no_decomp")
            logger.info("Registered query_decomposition subtechniques")
        except Exception as e:
            logger.exception("Failed to register query_decomposition: %s", e)
