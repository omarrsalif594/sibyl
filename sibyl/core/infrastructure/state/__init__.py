"""
State management infrastructure.

This module provides the core state management infrastructure including:
- DuckDB-based state storage
- State reader for queries
- State writer with batching
- Blob manager for content-addressed storage
- State migration system

Usage:
    from sibyl.core.infrastructure.state import StateFacade, StateReader

    facade = StateFacade(db_path="state.db")
    reader = StateReader(facade.client)
"""

# Core state components
from .blob_manager import BlobManager
from .duckdb_client import DuckDBClient
from .migrations import MigrationRunner, create_initial_schema
from .state_facade import StateFacade
from .state_migrator import StateMigrator
from .state_reader import StateReader
from .writer_queue import StateWriter

__all__ = [
    "BlobManager",
    "DuckDBClient",
    "MigrationRunner",
    "StateFacade",
    "StateMigrator",
    "StateReader",
    "StateWriter",
    "create_initial_schema",
]
