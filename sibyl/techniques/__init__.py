"""
Sibyl Techniques Module

This module provides the hyper-modular technique and subtechnique architecture.
Each technique (chunking, embedding, retrieval) has its own directory with
configuration and implementation.
"""

from .config_cascade import ConfigCascade
from .protocols import BaseSubtechnique, BaseTechnique, SubtechniqueResult, TechniqueConfig
from .registry import TECHNIQUE_REGISTRY, get_technique, iter_technique_classes, list_techniques

# Version is managed centrally in sibyl.__init__.py
# Do not hardcode version here

__all__ = [
    "TECHNIQUE_REGISTRY",
    "BaseSubtechnique",
    "BaseTechnique",
    "ConfigCascade",
    "SubtechniqueResult",
    "TechniqueConfig",
    "get_technique",
    "iter_technique_classes",
    "list_techniques",
]
