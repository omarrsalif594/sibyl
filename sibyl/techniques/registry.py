"""Central registry for all techniques."""

import logging
from collections.abc import Iterable
from importlib import import_module

from sibyl.techniques.protocols import BaseTechnique

logger = logging.getLogger(__name__)

# Map technique name to import path of its class
TECHNIQUE_REGISTRY: dict[str, str] = {
    # Core techniques
    "chunking": "sibyl.techniques.rag_pipeline.chunking.technique.ChunkingTechnique",
    "embedding": "sibyl.techniques.rag_pipeline.embedding.technique.EmbeddingTechnique",
    "retrieval": "sibyl.techniques.rag_pipeline.retrieval.technique.RetrievalTechnique",
    "consensus": "sibyl.techniques.ai_generation.consensus.technique.ConsensusTechnique",
    "storage": "sibyl.techniques.infrastructure.storage.technique.StorageTechnique",
    "session_management": "sibyl.techniques.workflow_orchestration.session_management.technique.SessionManagementTechnique",
    "orchestration": "sibyl.techniques.workflow_orchestration.orchestration.technique.OrchestrationTechnique",
    "validation": "sibyl.techniques.ai_generation.validation.technique.ValidationTechnique",
    "search": "sibyl.techniques.rag_pipeline.search.technique.SearchTechnique",
    "graph": "sibyl.techniques.workflow_orchestration.graph.technique.GraphTechnique",
    "checkpointing": "sibyl.techniques.infrastructure.checkpointing.technique.CheckpointingTechnique",
    "learning": "sibyl.techniques.infrastructure.learning.technique.LearningTechnique",
    "query_processing": "sibyl.techniques.rag_pipeline.query_processing.technique.QueryProcessingTechnique",
    "reranking": "sibyl.techniques.rag_pipeline.reranking.technique.RerankingTechnique",
    "context_management": "sibyl.techniques.workflow_orchestration.context_management.technique.ContextManagementTechnique",
    "augmentation": "sibyl.techniques.rag_pipeline.augmentation.technique.AugmentationTechnique",
    "generation": "sibyl.techniques.ai_generation.generation.technique.GenerationTechnique",
    "evaluation": "sibyl.techniques.infrastructure.evaluation.technique.EvaluationTechnique",
    "caching": "sibyl.techniques.infrastructure.caching.technique.CachingTechnique",
    "security": "sibyl.techniques.infrastructure.security.technique.SecurityTechnique",
    "workflow_optimization": (
        "sibyl.techniques.infrastructure.workflow_optimization.technique.WorkflowOptimizationTechnique"
    ),
    # NEW: Core refactoring techniques (extracted from hardcoded logic)
    "scoring": "sibyl.techniques.infrastructure.scoring.technique.ScoringTechnique",
    "resilience": "sibyl.techniques.infrastructure.resilience.technique.ResilienceTechnique",
    "orchestration_strategies": "sibyl.techniques.workflow_orchestration.orchestration_strategies.technique.OrchestrationStrategiesTechnique",
    "formatting": "sibyl.techniques.ai_generation.formatting.technique.FormattingTechnique",
    # Phase 2: Critical techniques (eliminate hardcoded values)
    "voting": "sibyl.techniques.ai_generation.voting.technique.VotingTechnique",
    "rate_limiting": "sibyl.techniques.infrastructure.rate_limiting.technique.RateLimitingTechnique",
    "budget_allocation": "sibyl.techniques.infrastructure.budget_allocation.technique.BudgetAllocationTechnique",
    "security_validation": "sibyl.techniques.infrastructure.security_validation.technique.SecurityValidationTechnique",
}


# Instance cache for lazy loading
_TECHNIQUE_INSTANCES: dict[str, BaseTechnique] = {}


def _load_class(import_path: str) -> type[BaseTechnique]:
    """Load a technique class from an import path.

    Args:
        import_path: Fully qualified import path (e.g., 'sibyl.techniques.infrastructure.scoring.technique.ScoringTechnique')

    Returns:
        Technique class

    Raises:
        ImportError: If module cannot be imported
        AttributeError: If class not found in module
    """
    try:
        module_path, class_name = import_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        logger.exception("Failed to load technique from %s: %s", import_path, e)
        raise


def get_technique(name: str, cached: bool = True) -> BaseTechnique:
    """Instantiate a technique by name with optional caching.

    Args:
        name: Technique name (e.g., 'scoring', 'resilience')
        cached: If True, return cached instance; if False, create new instance

    Returns:
        Technique instance

    Raises:
        ValueError: If technique name not found
        ImportError: If technique class cannot be loaded

    Examples:
        >>> scoring = get_technique('scoring')
        >>> confidence = scoring.calculate_confidence(tools=['tool1', 'tool2'])

        >>> # Get fresh instance
        >>> scoring = get_technique('scoring', cached=False)
    """
    if name not in TECHNIQUE_REGISTRY:
        available = ", ".join(sorted(TECHNIQUE_REGISTRY.keys()))
        msg = f"Unknown technique: '{name}'. Available techniques: {available}"
        raise ValueError(msg)

    # Return cached instance if requested
    if cached and name in _TECHNIQUE_INSTANCES:
        logger.debug("Returning cached instance of technique '%s'", name)
        return _TECHNIQUE_INSTANCES[name]

    # Load and instantiate
    try:
        cls = _load_class(TECHNIQUE_REGISTRY[name])
        instance = cls()  # type: ignore[call-arg]

        # Cache for future use
        if cached:
            _TECHNIQUE_INSTANCES[name] = instance
            logger.debug("Cached new instance of technique '%s'", name)

        return instance
    except Exception as e:
        logger.exception("Failed to instantiate technique '%s': %s", name, e)
        raise


def clear_cache(name: str | None = None) -> None:
    """Clear technique instance cache.

    Args:
        name: Optional technique name to clear; if None, clears all

    Examples:
        >>> clear_cache('scoring')  # Clear specific technique
        >>> clear_cache()  # Clear all cached techniques
    """
    global _TECHNIQUE_INSTANCES

    if name is None:
        count = len(_TECHNIQUE_INSTANCES)
        _TECHNIQUE_INSTANCES.clear()
        logger.info("Cleared all %s cached technique instances", count)
    elif name in _TECHNIQUE_INSTANCES:
        del _TECHNIQUE_INSTANCES[name]
        logger.info("Cleared cached instance of technique '%s'", name)
    else:
        logger.warning("No cached instance found for technique '%s'", name)


def is_cached(name: str) -> bool:
    """Check if a technique instance is cached.

    Args:
        name: Technique name

    Returns:
        True if cached, False otherwise
    """
    return name in _TECHNIQUE_INSTANCES


def iter_technique_classes() -> Iterable[tuple[str, type[BaseTechnique]]]:
    """Iterate through technique classes (lazy-loaded).

    Yields:
        Tuple of (technique_name, technique_class)

    Examples:
        >>> for name, cls in iter_technique_classes():
        ...     print(f"{name}: {cls.__name__}")
    """
    for name, import_path in TECHNIQUE_REGISTRY.items():
        try:
            yield name, _load_class(import_path)
        except Exception as e:
            logger.exception("Failed to load technique class '%s': %s", name, e)
            continue


def list_techniques() -> list[str]:
    """List all available technique names.

    Returns:
        Sorted list of technique names

    Examples:
        >>> techniques = list_techniques()
        >>> print(techniques)
        ['augmentation', 'caching', 'checkpointing', ...]
    """
    return sorted(TECHNIQUE_REGISTRY.keys())


def technique_exists(name: str) -> bool:
    """Check if a technique exists in the registry.

    Args:
        name: Technique name

    Returns:
        True if technique exists, False otherwise

    Examples:
        >>> technique_exists('scoring')
        True
        >>> technique_exists('nonexistent')
        False
    """
    return name in TECHNIQUE_REGISTRY


def register_technique(name: str, import_path: str, override: bool = False) -> None:
    """Register a new technique at runtime.

    Args:
        name: Technique name
        import_path: Fully qualified import path to technique class
        override: If True, allow overriding existing techniques

    Raises:
        ValueError: If technique already exists and override=False

    Examples:
        >>> register_technique(
        ...     'custom_scoring',
        ...     'my_package.techniques.custom_scoring.CustomScoringTechnique'
        ... )
    """
    if name in TECHNIQUE_REGISTRY and not override:
        msg = f"Technique '{name}' already registered. Use override=True to replace."
        raise ValueError(msg)

    TECHNIQUE_REGISTRY[name] = import_path
    logger.info("Registered technique '%s' -> %s", name, import_path)

    # Clear cache if updating existing technique
    if name in _TECHNIQUE_INSTANCES:
        del _TECHNIQUE_INSTANCES[name]
        logger.debug("Cleared cached instance of updated technique '%s'", name)


__all__ = [
    "TECHNIQUE_REGISTRY",
    "clear_cache",
    "get_technique",
    "is_cached",
    "iter_technique_classes",
    "list_techniques",
    "register_technique",
    "technique_exists",
]
