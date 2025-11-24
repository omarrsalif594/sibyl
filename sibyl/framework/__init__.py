"""Application layer utilities for tooling and plugins."""

from typing import Never

from . import errors, plugins, tools
from .plugins import register_builtin_plugins

REMOVED_SHIMS = {"providers", "runtime", "workflow", "registry"}


def __getattr__(name) -> Never:
    """Provide clearer errors for removed shims."""
    if name in REMOVED_SHIMS:
        msg = (
            f"sibyl.framework.{name} was removed; "
            "use 'sibyl.runtime' for runtime/providers or 'sibyl.techniques.registry' for technique registry."
        )
        raise ImportError(msg)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["errors", "plugins", "register_builtin_plugins", "tools"]
