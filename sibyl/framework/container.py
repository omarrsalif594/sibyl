from __future__ import annotations

"""
Generic dependency container for the core framework.

This container is intentionally slim: it only wires generic services such as
an in-memory graph provider and a lightweight entity vector index. Domain-
specific providers belong in example packages, not in core.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sibyl.techniques.rag_pipeline.search.impls.core.vector_index import (
    EmbeddingProvider,
    EntityVectorIndex,
)
from sibyl.techniques.workflow_orchestration.graph.impls.core.service import GenericGraphService

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Minimal application configuration."""

    workspace_root: Path
    enable_vector_search: bool = True

    @classmethod
    def from_env(cls) -> AppConfig:
        workspace_root = Path(os.getenv("SIBYL_WORKSPACE_ROOT", ".")).resolve()
        enable_vector_search = os.getenv("SIBYL_ENABLE_VECTOR", "true").lower() == "true"
        return cls(workspace_root=workspace_root, enable_vector_search=enable_vector_search)


@dataclass
class ProviderHealth:
    """Simple health snapshot for a provider."""

    name: str
    healthy: bool
    message: str
    details: dict | None = None


class _DeterministicEmbeddingProvider(EmbeddingProvider):
    """Lightweight embedding provider that avoids external dependencies."""

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def _vector_for_text(self, text: str) -> np.ndarray:
        # Deterministic pseudo-random vector based on text hash
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        return rng.standard_normal(self.dimension)

    def embed(self, text: str) -> np.ndarray:  # type: ignore[override]
        return self._vector_for_text(text)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:  # type: ignore[override]
        return [self._vector_for_text(text) for text in texts]


class CoreContainer:
    """Thin container that exposes only generic, domain-neutral providers."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig.from_env()
        self._graph_provider: GenericGraphService | None = None
        self._entity_index: EntityVectorIndex | None = None
        self._tool_registry = None
        self._started = False

    def startup(self) -> None:
        """Eagerly initialize core providers."""
        if self._started:
            return
        _ = self.get_graph_provider()
        _ = self.get_entity_index()
        _ = self.get_tool_registry()
        self._started = True
        logger.info("CoreContainer started")

    def get_graph_provider(self) -> GenericGraphService:
        """Return the generic graph provider (lazy-initialized)."""
        if self._graph_provider is None:
            self._graph_provider = GenericGraphService()
            self._seed_graph(self._graph_provider)
        return self._graph_provider

    def get_entity_index(self) -> EntityVectorIndex | None:
        """Return the generic entity index (lazy-initialized)."""
        if not self.config.enable_vector_search:
            return None

        if self._entity_index is None:
            embedding_provider = _DeterministicEmbeddingProvider()
            self._entity_index = EntityVectorIndex(embedding_provider=embedding_provider)
            self._seed_entities(self._entity_index)
        return self._entity_index

    def health_check(self) -> list[ProviderHealth]:
        """Report health for initialized providers."""
        results: list[ProviderHealth] = []

        if self._graph_provider is not None:
            stats = {
                "node_count": len(list(self._graph_provider.nodes())),
                "edge_count": len(list(self._graph_provider.edges())),
            }
            results.append(ProviderHealth("graph", True, "graph ready", stats))
        else:
            results.append(ProviderHealth("graph", False, "not initialized"))

        if self.config.enable_vector_search:
            if self._entity_index is not None:
                results.append(
                    ProviderHealth(
                        "entity_index",
                        True,
                        "entity index ready",
                        self._entity_index.get_stats(),
                    )
                )
            else:
                results.append(ProviderHealth("entity_index", False, "not initialized"))

        return results

    def get_tool_registry(self) -> Any:
        """Return the tool registry."""
        if self._tool_registry is None:
            from sibyl.framework.tools.tool_registry import ToolRegistry

            self._tool_registry = ToolRegistry()
        return self._tool_registry

    @staticmethod
    def _seed_graph(graph: GenericGraphService) -> None:
        """Add a tiny default graph so traversal endpoints have data."""
        if list(graph.nodes()):
            return
        graph.add_node("entity:root", "root", {"title": "Root entity"})
        graph.add_node("entity:child", "example", {"title": "Child entity"})
        graph.add_edge("entity:root", "entity:child", "related_to", {"weight": 1.0})

    @staticmethod
    def _seed_entities(index: EntityVectorIndex) -> None:
        """Seed the entity index with a few demo entries if empty."""
        if getattr(index, "_embeddings", {}):
            return
        index.add(
            entity_id="entity:root",
            text="Root entity for Sibyl core demo",
            metadata={"type": "demo"},
        )
        index.add(
            entity_id="entity:child",
            text="Child entity connected to the root",
            metadata={"type": "demo"},
        )


def create_core_container(config: AppConfig | None = None) -> CoreContainer:
    """Factory for a pre-started core container."""
    container = CoreContainer(config)
    container.startup()
    return container
