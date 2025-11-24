"""Runtime compression adapters.

Provides concrete implementations of compressors that adapt existing
Sibyl techniques and external services for use in compression chains.
"""

from .algorithmic_compressor import AlgorithmicCompressor
from .llm_summarizer import LLMSummarizer

__all__ = [
    "AlgorithmicCompressor",
    "LLMSummarizer",
]
