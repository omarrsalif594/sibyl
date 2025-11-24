"""Compression shop implementations.

High-level compression strategies that compose runtime compressors
into sophisticated compression workflows.
"""

from .global_intent_extractor import GlobalIntentExtractor
from .multi_pass_summary import MultiPassSummary

__all__ = [
    "GlobalIntentExtractor",
    "MultiPassSummary",
]
