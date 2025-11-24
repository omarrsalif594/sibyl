"""Persistence layer for state and session management.

This module provides persistence abstractions for storing and retrieving:
- External resource handles
- Session handles with checkpoints
- Pipeline execution state

Supports pluggable backends with DuckDB as the default implementation.
"""

from sibyl.core.persistence.store import (
    DuckDBStateStore,
    StateStore,
)

__all__ = [
    "DuckDBStateStore",
    "StateStore",
]
