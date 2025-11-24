"""
AI generation techniques.

This module provides convenient access to the main technique classes
for AI generation operations:
- ConsensusTechnique: Consensus building across multiple AI outputs
- FormattingTechnique: Output formatting and structure
- GenerationTechnique: Content generation
- ValidationTechnique: Output validation and verification
- VotingTechnique: Voting-based decision making

Example:
    from sibyl.techniques.ai_generation import ConsensusTechnique
    from sibyl.techniques.ai_generation import ValidationTechnique
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
