"""Runtime router components.

Provides integration between compression and LLM routing.
"""

from .compression_integration import CompressionRouter, create_compression_chain

__all__ = [
    "CompressionRouter",
    "create_compression_chain",
]
