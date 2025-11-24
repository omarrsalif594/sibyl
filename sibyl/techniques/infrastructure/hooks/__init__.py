"""
Hook infrastructure implementations.

Concrete implementations of hooks system including built-in hooks, registry, and decorators.
"""

from .builtin import CacheHook, MetricsHook, OperationMetrics
from .decorator import with_hooks, with_hooks_and_session
from .registry import HookRegistry, get_hook_registry, reset_hook_registry

__all__ = [
    "CacheHook",
    "HookRegistry",
    "MetricsHook",
    "OperationMetrics",
    "get_hook_registry",
    "reset_hook_registry",
    "with_hooks",
    "with_hooks_and_session",
]
