"""Minimal infrastructure layer for core functionality.

This module contains only the essential infrastructure components:
- LLM client and routing
- Provider registry
- Hook system
- Lifecycle management
"""

# LLM infrastructure
from .llm.base_client import BaseLLMClient
from .llm.errors import (
    BudgetExceededError,
    CapabilityError,
    CircuitOpenError,
    ProviderError,
    RateLimitError,
    TransientProviderError,
)

__all__ = [
    # LLM Components
    "BaseLLMClient",
    "BudgetExceededError",
    "CapabilityError",
    "CircuitOpenError",
    # LLM Errors
    "ProviderError",
    "RateLimitError",
    "TransientProviderError",
]
