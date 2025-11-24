"""Core orchestration strategy implementations."""

__all__ = []


def get_builtin_implementations() -> Any:
    """Get dictionary of built-in orchestration strategy implementations."""
    return {
        "context_merge": {},
        "consensus_aggregation": {},
        "error_reporting": {},
    }
