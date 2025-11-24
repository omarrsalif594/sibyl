"""Reranking technique for result reordering and fusion.

This technique orchestrates cross-encoder reranking, LLM reranking, diversity reranking,
BM25 reranking, and result fusion to improve retrieval effectiveness.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique
from sibyl.techniques.rag_pipeline.reranking.protocols import RerankingResult

logger = logging.getLogger(__name__)


class RerankingTechnique(BaseTechnique):
    """Reranking technique for result reordering and fusion."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "reranking"
        self._description = "Result reordering and fusion"
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
    ) -> RerankingResult:
        """Execute reranking technique.

        Args:
            input_data: Input data for reranking
            subtechnique: Subtechnique name (cross_encoder, llm_rerank, etc.)
            implementation: Implementation name
            config: Optional configuration override
            **kwargs: Additional arguments

        Returns:
            RerankingResult from subtechnique execution
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
        self._discover_subtechnique_category("cross_encoder", base_path)
        self._discover_subtechnique_category("llm_rerank", base_path)
        self._discover_subtechnique_category("diversity_rerank", base_path)
        self._discover_subtechnique_category("bm25_rerank", base_path)
        self._discover_subtechnique_category("fusion", base_path)

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
        if category == "cross_encoder":
            self._register_cross_encoder(category_path)
        elif category == "llm_rerank":
            self._register_llm_rerank(category_path)
        elif category == "diversity_rerank":
            self._register_diversity_rerank(category_path)
        elif category == "bm25_rerank":
            self._register_bm25_rerank(category_path)
        elif category == "fusion":
            self._register_fusion(category_path)

    def _register_cross_encoder(self, path: Path) -> None:
        """Register cross-encoder reranking implementations."""
        try:
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.cross_encoder.default.no_rerank import (  # plugin registration
                NoRerank,
            )
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.cross_encoder.default.sentence_transformer import (  # plugin registration
                CrossEncoderReranking,
            )

            self.register_subtechnique(
                CrossEncoderReranking(), "cross_encoder", "sentence_transformer"
            )
            self.register_subtechnique(NoRerank(), "cross_encoder", "no_rerank")
            logger.info("Registered cross_encoder subtechniques")
        except Exception as e:
            logger.exception("Failed to register cross_encoder: %s", e)

    def _register_llm_rerank(self, path: Path) -> None:
        """Register LLM reranking implementations."""
        try:
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.llm_rerank.default.prompt_based import (  # plugin registration
                PromptBasedReranking,
            )

            self.register_subtechnique(PromptBasedReranking(), "llm_rerank", "prompt_based")
            logger.info("Registered llm_rerank subtechniques")
        except Exception as e:
            logger.exception("Failed to register llm_rerank: %s", e)

    def _register_diversity_rerank(self, path: Path) -> None:
        """Register diversity reranking implementations."""
        try:
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.diversity_rerank.default.cluster_based import (  # plugin registration
                ClusterBasedReranking,
            )
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.diversity_rerank.default.mmr import (  # plugin registration
                MMRReranking,
            )

            self.register_subtechnique(MMRReranking(), "diversity_rerank", "mmr")
            self.register_subtechnique(ClusterBasedReranking(), "diversity_rerank", "cluster_based")
            logger.info("Registered diversity_rerank subtechniques")
        except Exception as e:
            logger.exception("Failed to register diversity_rerank: %s", e)

    def _register_bm25_rerank(self, path: Path) -> None:
        """Register BM25 reranking implementations."""
        try:
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.bm25_rerank.default.bm25_scorer import (  # plugin registration
                BM25Reranking,
            )

            self.register_subtechnique(BM25Reranking(), "bm25_rerank", "bm25_scorer")
            logger.info("Registered bm25_rerank subtechniques")
        except Exception as e:
            logger.exception("Failed to register bm25_rerank: %s", e)

    def _register_fusion(self, path: Path) -> None:
        """Register fusion reranking implementations."""
        try:
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.fusion.default.rrf import (  # plugin registration
                RRFFusion,
            )
            from sibyl.techniques.rag_pipeline.reranking.subtechniques.fusion.default.weighted_fusion import (  # plugin registration
                WeightedFusion,
            )

            self.register_subtechnique(RRFFusion(), "fusion", "rrf")
            self.register_subtechnique(WeightedFusion(), "fusion", "weighted_fusion")
            logger.info("Registered fusion subtechniques")
        except Exception as e:
            logger.exception("Failed to register fusion: %s", e)
