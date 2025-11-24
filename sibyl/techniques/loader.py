"""
Dynamic subtechnique loader for the Sibyl framework.

This module provides infrastructure for dynamically loading subtechnique implementations
based on a specification. It enables the hyper-modular architecture by allowing
techniques to discover and load subtechniques without hardcoded imports.

Key Components:
    - SubtechniqueSpec: Dataclass specifying what to load
    - load_subtechnique: Dynamic loader function
    - TechniqueLoader: Class-based loader with caching support

Design Principles:
    - Fail fast with clear error messages
    - Follow the canonical directory structure
    - Enable runtime discovery and loading
    - Support multiple variant types (default, provider, custom)

Example Usage:
    >>> from sibyl.techniques.loader import load_subtechnique, SubtechniqueSpec
    >>>
    >>> # Define what to load
    >>> spec = SubtechniqueSpec(
    ...     shop="rag_pipeline",
    ...     technique="augmentation",
    ...     subtechnique="metadata_injection",
    ...     variant="default"
    ... )
    >>>
    >>> # Load the factory function
    >>> factory = load_subtechnique(spec)
    >>>
    >>> # Build an instance
    >>> impl = factory(implementation_name="schema_metadata")
    >>> result = impl.execute(input_data, config)
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubtechniqueSpec:
    """
    Specification for loading a subtechnique implementation.

    This dataclass defines the four components needed to uniquely identify
    a subtechnique variant within the Sibyl framework's directory structure.

    Attributes:
        shop: The shop category (e.g., 'rag_pipeline', 'ai_generation', 'infrastructure')
        technique: The technique name (e.g., 'augmentation', 'search', 'chunking')
        subtechnique: The subtechnique name (e.g., 'metadata_injection', 'hybrid_search')
        variant: The variant type (e.g., 'default', 'provider', 'custom')

    Example:
        >>> spec = SubtechniqueSpec(
        ...     shop="rag_pipeline",
        ...     technique="augmentation",
        ...     subtechnique="metadata_injection",
        ...     variant="default"
        ... )
        >>> print(spec.import_path)
        sibyl.techniques.rag_pipeline.augmentation.subtechniques.metadata_injection.default

    Note:
        This class is frozen (immutable) to ensure specs can be used as dictionary keys
        and maintain referential integrity throughout the loading process.
    """

    shop: str
    technique: str
    subtechnique: str
    variant: str

    @property
    def import_path(self) -> str:
        """
        Construct the fully qualified import path for this subtechnique variant.

        Returns:
            str: Import path in format 'sibyl.techniques.{shop}.{technique}.subtechniques.{subtechnique}.{variant}'

        Example:
            >>> spec = SubtechniqueSpec("rag_pipeline", "search", "vector_search", "default")
            >>> spec.import_path
            'sibyl.techniques.rag_pipeline.search.subtechniques.vector_search.default'
        """
        return f"sibyl.techniques.{self.shop}.{self.technique}.subtechniques.{self.subtechnique}.{self.variant}"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"{self.shop}/{self.technique}/{self.subtechnique}:{self.variant}"

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        return (
            f"SubtechniqueSpec(shop='{self.shop}', technique='{self.technique}', "
            f"subtechnique='{self.subtechnique}', variant='{self.variant}')"
        )


def load_subtechnique(spec: SubtechniqueSpec, **kwargs: Any) -> Callable:
    """
    Dynamically load a subtechnique factory function from a specification.

    This function constructs the import path from the spec, imports the module,
    and returns the `build_subtechnique()` factory function. It fails fast with
    clear error messages if the module or factory function is missing.

    Args:
        spec: SubtechniqueSpec defining what to load
        **kwargs: Optional keyword arguments to pass to the factory (not used in loading,
                 reserved for future extensions)

    Returns:
        Callable: The build_subtechnique factory function from the variant module

    Raises:
        ModuleNotFoundError: If the module path does not exist
        AttributeError: If the module does not have a build_subtechnique function
        ImportError: If there are import errors in the module

    Example:
        >>> # Load metadata injection default variant
        >>> spec = SubtechniqueSpec(
        ...     shop="rag_pipeline",
        ...     technique="augmentation",
        ...     subtechnique="metadata_injection",
        ...     variant="default"
        ... )
        >>> factory = load_subtechnique(spec)
        >>> impl = factory(implementation_name="schema_metadata")
        >>>
        >>> # Load with error handling
        >>> try:
        ...     factory = load_subtechnique(spec)
        ... except ModuleNotFoundError as e:
        ...     print(f"Subtechnique variant not found: {e}")
        ... except AttributeError as e:
        ...     print(f"Missing build_subtechnique factory: {e}")

    Implementation Notes:
        - The function expects each variant directory to have __init__.py with build_subtechnique()
        - The factory function signature should accept **kwargs for flexibility
        - Common factory patterns:
            1. Simple: build_subtechnique() -> returns single implementation instance
            2. Named: build_subtechnique(implementation_name: str, **kwargs) -> returns named impl
            3. Configured: build_subtechnique(config: dict, **kwargs) -> returns configured impl

    See Also:
        - docs/techniques/TECHNIQUE_TEMPLATE.md - Full structure documentation
        - SubtechniqueSpec - Specification format
        - TechniqueLoader - Class-based loader with caching
    """
    import_path = spec.import_path
    logger.debug("Loading subtechnique from: %s", import_path)

    try:
        # Dynamically import the variant module
        module = import_module(import_path)
        logger.debug("Successfully imported module: %s", import_path)
    except ModuleNotFoundError as e:
        error_msg = (
            f"Failed to load subtechnique variant '{spec}'. "
            f"Module not found: {import_path}\n"
            f"Expected directory structure:\n"
            f"  sibyl/techniques/{spec.shop}/{spec.technique}/subtechniques/{spec.subtechnique}/{spec.variant}/\n"
            f"Ensure the variant directory exists and has __init__.py"
        )
        logger.exception(error_msg)
        raise ModuleNotFoundError(error_msg) from e
    except ImportError as e:
        error_msg = (
            f"Failed to import subtechnique variant '{spec}'. "
            f"Import error in module: {import_path}\n"
            f"Original error: {e!s}"
        )
        logger.exception(error_msg)
        raise ImportError(error_msg) from e

    # Extract the build_subtechnique factory function
    if not hasattr(module, "build_subtechnique"):
        error_msg = (
            f"Module {import_path} does not export 'build_subtechnique' factory function.\n"
            f"Each variant's __init__.py MUST export a build_subtechnique() function.\n"
            f"Expected signature: def build_subtechnique(**kwargs) -> BaseSubtechnique\n"
            f"See docs/techniques/TECHNIQUE_TEMPLATE.md for details."
        )
        logger.error(error_msg)
        raise AttributeError(error_msg)

    factory = module.build_subtechnique
    logger.info("Successfully loaded subtechnique factory: %s", spec)
    return factory


class TechniqueLoader:
    """
    Class-based loader with caching support for subtechnique factories.

    This class provides a higher-level interface for loading subtechniques with
    optional caching to improve performance when loading the same subtechnique
    multiple times.

    Attributes:
        cache: Dictionary mapping SubtechniqueSpec to factory functions
        enable_cache: Whether to cache loaded factories

    Example:
        >>> loader = TechniqueLoader(enable_cache=True)
        >>>
        >>> # Load and cache
        >>> spec = SubtechniqueSpec(
        ...     shop="rag_pipeline",
        ...     technique="search",
        ...     subtechnique="vector_search",
        ...     variant="default"
        ... )
        >>> factory = loader.load(spec)
        >>>
        >>> # Second load uses cache
        >>> factory2 = loader.load(spec)  # Instant return from cache
        >>>
        >>> # Build instances
        >>> impl1 = factory()
        >>> impl2 = factory()  # Fresh instance
        >>>
        >>> # Clear cache
        >>> loader.clear_cache()

    Usage Patterns:
        1. Single-use loader (no caching):
           >>> loader = TechniqueLoader(enable_cache=False)
           >>> factory = loader.load(spec)

        2. Long-lived loader with caching:
           >>> loader = TechniqueLoader(enable_cache=True)
           >>> # Use throughout application lifecycle

        3. Pre-warm cache:
           >>> loader = TechniqueLoader()
           >>> specs = [spec1, spec2, spec3]
           >>> for spec in specs:
           ...     loader.load(spec)

    Note:
        - Caching stores factory functions, not instances
        - Each call to factory() creates a new instance
        - Cache key is the immutable SubtechniqueSpec
        - Thread-safety considerations: This class is not thread-safe by default
    """

    def __init__(self, enable_cache: bool = True) -> None:
        """
        Initialize the loader.

        Args:
            enable_cache: If True, cache loaded factories; if False, always reload
        """
        self.cache: dict[SubtechniqueSpec, Callable] = {}
        self.enable_cache = enable_cache
        logger.debug(
            "Initialized TechniqueLoader with caching=%s", "enabled" if enable_cache else "disabled"
        )

    def load(self, spec: SubtechniqueSpec, force_reload: bool = False, **kwargs: Any) -> Callable:
        """
        Load a subtechnique factory with optional caching.

        Args:
            spec: SubtechniqueSpec defining what to load
            force_reload: If True, bypass cache and reload from disk
            **kwargs: Additional keyword arguments (reserved for future use)

        Returns:
            Callable: The build_subtechnique factory function

        Raises:
            ModuleNotFoundError: If the module path does not exist
            AttributeError: If the module does not have a build_subtechnique function
            ImportError: If there are import errors in the module

        Example:
            >>> loader = TechniqueLoader()
            >>> spec = SubtechniqueSpec("rag_pipeline", "chunking", "fixed_size", "default")
            >>>
            >>> # First load (from disk)
            >>> factory = loader.load(spec)
            >>>
            >>> # Second load (from cache if enabled)
            >>> factory = loader.load(spec)
            >>>
            >>> # Force reload (bypass cache)
            >>> factory = loader.load(spec, force_reload=True)
        """
        # Check cache first
        if self.enable_cache and not force_reload and spec in self.cache:
            logger.debug("Returning cached factory for: %s", spec)
            return self.cache[spec]

        # Load from disk
        logger.debug("Loading factory from disk for: %s", spec)
        factory = load_subtechnique(spec, **kwargs)

        # Cache if enabled
        if self.enable_cache:
            self.cache[spec] = factory
            logger.debug("Cached factory for: %s", spec)

        return factory

    def preload(self, specs: list[SubtechniqueSpec]) -> None:
        """
        Pre-load multiple subtechniques into cache.

        This is useful for warming up the cache at application startup to
        avoid lazy-loading delays during runtime.

        Args:
            specs: List of SubtechniqueSpec to pre-load

        Example:
            >>> loader = TechniqueLoader()
            >>> specs = [
            ...     SubtechniqueSpec("rag_pipeline", "search", "vector_search", "default"),
            ...     SubtechniqueSpec("rag_pipeline", "search", "keyword_search", "default"),
            ...     SubtechniqueSpec("rag_pipeline", "search", "hybrid_search", "default"),
            ... ]
            >>> loader.preload(specs)
            >>> # All factories now cached and ready
        """
        logger.info("Pre-loading %s subtechnique factories", len(specs))
        failed = []
        for spec in specs:
            try:
                self.load(spec)
            except (ModuleNotFoundError, AttributeError, ImportError) as e:
                logger.warning("Failed to preload %s: %s", spec, e)
                failed.append(spec)

        if failed:
            logger.warning("Failed to preload %s subtechniques: %s", len(failed), failed)
        else:
            logger.info("Successfully preloaded all %s subtechniques", len(specs))

    def clear_cache(self, spec: SubtechniqueSpec | None = None) -> None:
        """
        Clear the factory cache.

        Args:
            spec: Optional specific spec to clear; if None, clears entire cache

        Example:
            >>> loader = TechniqueLoader()
            >>> # ... load some factories ...
            >>>
            >>> # Clear specific entry
            >>> loader.clear_cache(spec)
            >>>
            >>> # Clear entire cache
            >>> loader.clear_cache()
        """
        if spec is None:
            count = len(self.cache)
            self.cache.clear()
            logger.info("Cleared entire factory cache (%s entries)", count)
        elif spec in self.cache:
            del self.cache[spec]
            logger.info("Cleared cache entry for: %s", spec)
        else:
            logger.debug("No cache entry to clear for: %s", spec)

    def is_cached(self, spec: SubtechniqueSpec) -> bool:
        """
        Check if a factory is cached.

        Args:
            spec: SubtechniqueSpec to check

        Returns:
            bool: True if cached, False otherwise

        Example:
            >>> loader = TechniqueLoader()
            >>> spec = SubtechniqueSpec("rag_pipeline", "search", "vector_search", "default")
            >>> loader.is_cached(spec)  # False
            >>> loader.load(spec)
            >>> loader.is_cached(spec)  # True
        """
        return spec in self.cache

    def cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Statistics including size, enabled status, and cached specs

        Example:
            >>> loader = TechniqueLoader()
            >>> # ... load some factories ...
            >>> stats = loader.cache_stats()
            >>> print(f"Cache size: {stats['size']}")
            >>> print(f"Cached specs: {stats['specs']}")
        """
        return {
            "enabled": self.enable_cache,
            "size": len(self.cache),
            "specs": [str(spec) for spec in self.cache],
        }


# Convenience function for creating loaders
def create_loader(enable_cache: bool = True) -> TechniqueLoader:
    """
    Create a new TechniqueLoader instance.

    This is a convenience factory function for creating loaders with consistent
    configuration.

    Args:
        enable_cache: Whether to enable caching

    Returns:
        TechniqueLoader: New loader instance

    Example:
        >>> loader = create_loader(enable_cache=True)
        >>> factory = loader.load(spec)
    """
    return TechniqueLoader(enable_cache=enable_cache)


__all__ = [
    "SubtechniqueSpec",
    "TechniqueLoader",
    "create_loader",
    "load_subtechnique",
]
