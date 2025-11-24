"""
State migrator for schema management and integrity checks.

Handles schema versioning, migrations, and database integrity validation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from .duckdb_client import DuckDBClient
from .migrations import MigrationRunner, create_initial_schema

logger = logging.getLogger(__name__)


@dataclass
class IntegrityResult:
    """Result of integrity check."""

    passed: bool
    message: str
    details: dict | None = None


@dataclass
class SchemaStatus:
    """Schema version status."""

    current_version: int
    expected_version: int
    needs_migration: bool
    migration_required: bool  # True if MUST migrate, False if optional


class StateMigrator:
    """
    Schema management and integrity validation.

    Single Responsibility: Database schema lifecycle

    Features:
    - Integrity checks (PRAGMA integrity_check)
    - Schema version management
    - Migration execution
    - Validation and diagnostics

    Usage:
        client = DuckDBClient(db_path)
        migrator = StateMigrator(client, expected_version=2)

        # Check integrity
        result = migrator.check_integrity()
        if not result.passed:
            raise RuntimeError(f"Integrity check failed: {result.message}")

        # Check schema version
        status = migrator.get_schema_status()
        if status.needs_migration:
            migrator.run_migration(status.expected_version)
    """

    def __init__(
        self, client: DuckDBClient, expected_version: int = 2, db_path: Path | None = None
    ) -> None:
        """
        Initialize state migrator.

        Args:
            client: DuckDB client
            expected_version: Expected schema version (default: 2)
            db_path: Optional database path (for creating new databases)
        """
        self.client = client
        self.expected_version = expected_version
        self.db_path = db_path or client.db_path

        logger.debug("StateMigrator initialized (expected_version=%s)", expected_version)

    def check_integrity(self) -> IntegrityResult:
        """
        Check database integrity using PRAGMA integrity_check.

        Returns:
            IntegrityResult with pass/fail status

        Raises:
            ConnectionError: If integrity check fails to execute
        """
        logger.info("Running database integrity check...")

        try:
            result = self.client.execute_read("PRAGMA integrity_check")

            if result and result[0][0] == "ok":
                logger.info("✓ Integrity check passed")
                return IntegrityResult(passed=True, message="Database integrity check passed")
            error_msg = result[0][0] if result else "Unknown error"
            logger.error("✗ Integrity check failed: %s", error_msg)
            return IntegrityResult(
                passed=False,
                message=f"Database integrity check failed: {error_msg}",
                details={"result": result},
            )

        except Exception as e:
            logger.exception("✗ Integrity check error: %s", e)
            return IntegrityResult(
                passed=False, message=f"Integrity check failed with exception: {e}"
            )

    def get_current_version(self) -> int:
        """
        Get current schema version from database.

        Returns:
            Current schema version (0 if not found)

        Raises:
            RuntimeError: If schema_version table doesn't exist
        """
        try:
            result = self.client.execute_read("SELECT MAX(version) FROM schema_version")
            version = result[0][0] if result and result[0][0] is not None else 0
            logger.debug("Current schema version: %s", version)
            return version

        except Exception as e:
            logger.warning("Could not get schema version: %s", e)
            # Table might not exist yet
            return 0

    def get_schema_status(self) -> SchemaStatus:
        """
        Get schema version status.

        Returns:
            SchemaStatus with version comparison
        """
        current = self.get_current_version()

        needs_migration = current < self.expected_version
        migration_required = current < self.expected_version

        status = SchemaStatus(
            current_version=current,
            expected_version=self.expected_version,
            needs_migration=needs_migration,
            migration_required=migration_required,
        )

        if current < self.expected_version:
            logger.warning(
                "Schema version %s < expected %s (migration required)",
                current,
                self.expected_version,
            )
        elif current > self.expected_version:
            logger.warning(
                f"Schema version {current} > expected {self.expected_version} "
                "(application may be outdated)"
            )
        else:
            logger.info("Schema version %s matches expected", current)

        return status

    def validate_schema(self) -> IntegrityResult:
        """
        Validate schema version matches expected version.

        Returns:
            IntegrityResult indicating if schema is valid

        Raises:
            RuntimeError: If schema version mismatch requires action
        """
        status = self.get_schema_status()

        if status.current_version < status.expected_version:
            msg = (
                f"Schema version {status.current_version} < expected {status.expected_version}. "
                f"Migration required. Run: migrator.run_migration({status.expected_version})"
            )
            logger.error(msg)
            return IntegrityResult(passed=False, message=msg, details={"status": status})

        if status.current_version > status.expected_version:
            msg = (
                f"Schema version {status.current_version} > expected {status.expected_version}. "
                "Application may be outdated. Please upgrade."
            )
            logger.error(msg)
            return IntegrityResult(passed=False, message=msg, details={"status": status})

        logger.info("✓ Schema version %s is valid", status.current_version)
        return IntegrityResult(
            passed=True,
            message=f"Schema version {status.current_version} matches expected",
            details={"status": status},
        )

    def create_schema(self) -> None:
        """
        Create initial schema (for new databases).

        Raises:
            RuntimeError: If database already exists
        """
        if self.db_path.exists():
            msg = f"Database already exists: {self.db_path}"
            raise RuntimeError(msg)

        logger.info("Creating initial schema at %s...", self.db_path)

        # Create parent directory
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create schema
        create_initial_schema(self.db_path)

        logger.info("✓ Initial schema created")

    def run_migration(self, target_version: int) -> None:
        """
        Run migrations to target version.

        Args:
            target_version: Target schema version

        Raises:
            RuntimeError: If migration fails
        """
        current = self.get_current_version()

        if current == target_version:
            logger.info("Already at version %s, no migration needed", target_version)
            return

        if current > target_version:
            msg = (
                f"Cannot downgrade from version {current} to {target_version}. "
                "Downgrades are not supported."
            )
            raise RuntimeError(msg)

        logger.info("Migrating from version %s to %s...", current, target_version)

        try:
            runner = MigrationRunner(self.db_path)
            runner.run_migrations(target_version)

            logger.info("✓ Migration to version %s completed", target_version)

        except Exception as e:
            logger.exception("✗ Migration failed: %s", e)
            msg = f"Migration failed: {e}"
            raise RuntimeError(msg) from e

    def get_migration_history(self) -> list[dict]:
        """
        Get migration history from schema_version table.

        Returns:
            List of migration records
        """
        try:
            results = self.client.execute_read(
                "SELECT version, applied_at, description FROM schema_version ORDER BY version"
            )
            return [
                {"version": row[0], "applied_at": row[1], "description": row[2]} for row in results
            ]
        except Exception as e:
            logger.warning("Could not get migration history: %s", e)
            return []

    def verify_tables_exist(self) -> IntegrityResult:
        """
        Verify that all expected tables exist.

        Returns:
            IntegrityResult indicating if all tables exist
        """
        expected_tables = ["schema_version", "conversations", "phase_checkpoints", "subagent_calls"]

        missing_tables = []

        for table in expected_tables:
            try:
                # Table names are from expected_tables constant list (safe)
                self.client.execute_read(f"SELECT 1 FROM {table} LIMIT 1")
            except Exception:
                missing_tables.append(table)

        if missing_tables:
            msg = f"Missing tables: {', '.join(missing_tables)}"
            logger.error(msg)
            return IntegrityResult(
                passed=False, message=msg, details={"missing_tables": missing_tables}
            )

        logger.info("✓ All expected tables exist")
        return IntegrityResult(passed=True, message="All expected tables exist")

    def full_validation(self) -> IntegrityResult:
        """
        Run full validation suite (integrity + schema + tables).

        Returns:
            IntegrityResult with overall status

        This is the recommended method for boot-time validation.
        """
        logger.info("Running full validation suite...")

        # 1. Check integrity
        integrity = self.check_integrity()
        if not integrity.passed:
            return integrity

        # 2. Validate schema version
        schema = self.validate_schema()
        if not schema.passed:
            return schema

        # 3. Verify tables exist
        tables = self.verify_tables_exist()
        if not tables.passed:
            return tables

        logger.info("✓ Full validation passed")
        return IntegrityResult(
            passed=True, message="Full validation passed (integrity + schema + tables)"
        )
