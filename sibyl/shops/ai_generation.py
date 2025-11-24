"""
AI Generation shop: high-level access to AI generation and validation techniques.

This module provides access to techniques for generating, validating, and
reaching consensus on AI-generated content.
"""

from sibyl.techniques.ai_generation.consensus.technique import ConsensusTechnique
from sibyl.techniques.ai_generation.formatting.technique import FormattingTechnique
from sibyl.techniques.ai_generation.generation.technique import GenerationTechnique
from sibyl.techniques.ai_generation.validation.technique import ValidationTechnique
from sibyl.techniques.ai_generation.voting.technique import VotingTechnique

__all__ = [
    "ConsensusTechnique",
    "FormattingTechnique",
    "GenerationTechnique",
    "ValidationTechnique",
    "VotingTechnique",
]
