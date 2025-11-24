"""SQL database providers for Sibyl.

This package contains implementations of SQLDataProvider protocol
for various SQL databases (SQLite, PostgreSQL, MySQL, etc.).
"""

from sibyl.providers.sql.sqlite import SQLiteDataProvider

__all__ = ["SQLiteDataProvider"]
