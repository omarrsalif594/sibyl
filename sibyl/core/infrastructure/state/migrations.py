from __future__ import annotations

"""Database migration runner with checksum validation."""

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Run schema migrations with checksum validation.

    Features:
    - Ordered migration execution
    - Checksum validation (prevents tampering)
    - Transactional application
    - Manifest tracking
    """

    def __init__(self, db_path: Path, migrations_dir: Path) -> None:
        """Initialize migration runner.

        Args:
            db_path: Path to DuckDB database
            migrations_dir: Directory containing migration files
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self.manifest_path = migrations_dir / "migrations_manifest.json"

        logger.info("Migration runner initialized: %s", migrations_dir)

    def run(self, target_version: int) -> None:
        """Run migrations up to target version.

        Args:
            target_version: Target schema version

        Raises:
            RuntimeError: If migration fails or checksum mismatch
        """
        import duckdb

        conn = duckdb.connect(str(self.db_path))

        try:
            # Get current version
            current_version = self._get_current_version(conn)
            logger.info("Current schema version: %s", current_version)

            if current_version >= target_version:
                logger.info("Already at target version %s", target_version)
                return

            # Load manifest
            manifest = self._load_manifest()

            # Apply migrations
            for version in range(current_version + 1, target_version + 1):
                logger.info("Applying migration to version %s", version)

                # Find migration in manifest
                migration = self._find_migration(manifest, version)
                if not migration:
                    msg = f"Migration not found in manifest for version {version}"
                    raise RuntimeError(msg)

                # Get migration file
                migration_file = self.migrations_dir / migration["filename"]
                if not migration_file.exists():
                    msg = f"Migration file not found: {migration['filename']}"
                    raise RuntimeError(msg)

                # Validate checksum
                actual_checksum = self._compute_checksum(migration_file)
                expected_checksum = migration.get("checksum")

                if expected_checksum and expected_checksum != "SHA256 will be computed at runtime":
                    if actual_checksum != expected_checksum:
                        msg = (
                            f"Checksum mismatch for {migration['filename']}: "
                            f"expected {expected_checksum}, got {actual_checksum}"
                        )
                        raise RuntimeError(msg)
                    logger.debug("Checksum validated: %s...", actual_checksum[:8])
                else:
                    # Update manifest with computed checksum
                    migration["checksum"] = actual_checksum
                    logger.debug("Computed checksum: %s...", actual_checksum[:8])

                # Apply migration
                self._apply_migration(conn, migration_file, version, migration["description"])

                logger.info("Migration to version %s completed", version)

            # Save updated manifest
            if expected_checksum == "SHA256 will be computed at runtime":
                self._save_manifest(manifest)

        finally:
            conn.close()

    def _get_current_version(self, conn: Any) -> int:
        """Get current schema version.

        Args:
            conn: DuckDB connection

        Returns:
            Current schema version (0 if schema_version table doesn't exist)
        """
        try:
            result = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return result[0] if result and result[0] else 0
        except Exception:
            # schema_version table doesn't exist
            return 0

    def _load_manifest(self) -> dict[str, Any]:
        """Load migrations manifest.

        Returns:
            Manifest dict

        Raises:
            FileNotFoundError: If manifest not found
        """
        if not self.manifest_path.exists():
            msg = f"Migrations manifest not found: {self.manifest_path}"
            raise FileNotFoundError(msg)

        with open(self.manifest_path) as f:
            return json.load(f)

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        """Save updated manifest.

        Args:
            manifest: Manifest dict
        """
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.debug("Manifest updated")

    def _find_migration(self, manifest: dict[str, Any], version: int) -> dict[str, Any] | None:
        """Find migration by version in manifest.

        Args:
            manifest: Manifest dict
            version: Target version

        Returns:
            Migration dict or None if not found
        """
        for migration in manifest.get("migrations", []):
            if migration["version"] == version:
                return migration
        return None

    def _compute_checksum(self, migration_file: Path) -> str:
        """Compute SHA256 checksum of migration file.

        Args:
            migration_file: Path to migration SQL file

        Returns:
            SHA256 hex digest
        """
        content = migration_file.read_text()
        return hashlib.sha256(content.encode()).hexdigest()

    def _apply_migration(
        self, conn: Any, migration_file: Path, version: int, description: str
    ) -> None:
        """Apply a migration file.

        Args:
            conn: DuckDB connection
            migration_file: Path to migration SQL file
            version: Migration version
            description: Migration description

        Raises:
            RuntimeError: If migration fails
        """
        sql = migration_file.read_text()

        # Begin transaction
        conn.begin()

        try:
            # Execute migration SQL
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(statement)

            # Update schema_version table
            conn.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )

            # Commit
            conn.commit()

            logger.info("Migration %s applied: %s", version, description)

        except Exception as e:
            # Rollback on error
            conn.rollback()
            msg = f"Migration {version} failed: {e}"
            raise RuntimeError(msg) from e


def create_initial_schema(db_path: Path) -> None:
    """Create initial schema (bootstrap).

    Args:
        db_path: Path to DuckDB database

    Raises:
        RuntimeError: If schema creation fails
    """
    import duckdb

    logger.info("Creating initial schema (bootstrap)")

    conn = duckdb.connect(str(db_path))

    try:
        # Create schema_version table first
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL
            )
        """)

        # Insert version 0 (before any migrations)
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, description) VALUES (0, 'Bootstrap')"
        )

        conn.commit()
        logger.info("Initial schema created")

    except Exception as e:
        conn.rollback()
        msg = f"Failed to create initial schema: {e}"
        raise RuntimeError(msg) from e

    finally:
        conn.close()
