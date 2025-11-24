"""JSON file-based checkpoint store.

Simple file-based implementation of CheckpointStore using JSON files.
Suitable for single-machine deployments and development.

For production multi-machine deployments, consider:
- SQLiteCheckpointStore (concurrent access with locking)
- RedisCheckpointStore (distributed systems)
- PostgreSQLCheckpointStore (persistent + concurrent)

Example:
    from sibyl.mcp_server.infrastructure.checkpointing import (
        JSONCheckpointStore,
        OperationCheckpoint,
    )

    store = JSONCheckpointStore(checkpoint_dir="/tmp/checkpoints")

    # Save checkpoint
    checkpoint = OperationCheckpoint(
        operation_id="batch-123",
        operation_name="compile",
        checkpoint_id="wave_1",
        state={"completed": ["model_a", "model_b"]},
    )
    store.save_checkpoint(checkpoint)

    # Resume
    last = store.load_latest_checkpoint("batch-123")
    if last:
        completed = last.state["completed"]
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sibyl.mcp_server.infrastructure.checkpointing.protocol import (
    OperationCheckpoint,
)

logger = logging.getLogger(__name__)


class JSONCheckpointStore:
    """JSON file-based checkpoint store.

    Stores checkpoints as JSON files in a directory structure:
    checkpoint_dir/
        {operation_id}/
            checkpoint_{sequence}.json
            latest.json  # Symlink or copy to latest checkpoint

    Thread-safety: Not thread-safe. Use file locking for concurrent access.
    """

    def __init__(self, checkpoint_dir: Path | str | None = None) -> None:
        """Initialize JSON checkpoint store.

        Args:
            checkpoint_dir: Directory to store checkpoint files (uses system temp dir if None)
        """
        # Use system temp dir for portability (Windows/Linux/Mac)
        if checkpoint_dir is None:
            import tempfile

            checkpoint_dir = Path(tempfile.gettempdir()) / "sibyl_checkpoints"
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initialized JSON checkpoint store at %s", self.checkpoint_dir)

    def save_checkpoint(self, checkpoint: OperationCheckpoint) -> None:
        """Save checkpoint to JSON file.

        Args:
            checkpoint: Checkpoint to save
        """
        # Create operation directory
        operation_dir = self.checkpoint_dir / checkpoint.operation_id
        operation_dir.mkdir(parents=True, exist_ok=True)

        # Save checkpoint file
        checkpoint_file = operation_dir / f"checkpoint_{checkpoint.sequence_number:04d}.json"

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        # Update latest.json
        latest_file = operation_dir / "latest.json"
        with open(latest_file, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        logger.debug(
            "Saved checkpoint %s for operation %s",
            checkpoint.checkpoint_id,
            checkpoint.operation_id,
        )

    def load_checkpoint(
        self, operation_id: str, checkpoint_id: str
    ) -> Optional[OperationCheckpoint]:
        """Load a specific checkpoint.

        Args:
            operation_id: Operation ID
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint or None if not found
        """
        operation_dir = self.checkpoint_dir / operation_id

        if not operation_dir.exists():
            logger.debug("No checkpoints found for operation %s", operation_id)
            return None

        # Search for checkpoint with matching ID
        for checkpoint_file in operation_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                    if data.get("checkpoint_id") == checkpoint_id:
                        return OperationCheckpoint.from_dict(data)
            except Exception as e:
                logger.warning("Failed to load checkpoint %s: %s", checkpoint_file, e)

        logger.debug("Checkpoint %s not found for operation %s", checkpoint_id, operation_id)
        return None

    def load_latest_checkpoint(self, operation_id: str) -> Optional[OperationCheckpoint]:
        """Load the most recent checkpoint.

        Args:
            operation_id: Operation ID

        Returns:
            Latest checkpoint or None if not found
        """
        latest_file = self.checkpoint_dir / operation_id / "latest.json"

        if not latest_file.exists():
            logger.debug("No checkpoints found for operation %s", operation_id)
            return None

        try:
            with open(latest_file) as f:
                data = json.load(f)
                checkpoint = OperationCheckpoint.from_dict(data)
                logger.info(
                    "Loaded latest checkpoint %s for operation %s",
                    checkpoint.checkpoint_id,
                    operation_id,
                )
                return checkpoint
        except Exception as e:
            logger.exception(
                f"Failed to load latest checkpoint for operation {operation_id}: {e}",
            )
            return None

    def list_checkpoints(self, operation_id: str) -> list[OperationCheckpoint]:
        """List all checkpoints for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            List of checkpoints ordered by sequence_number
        """
        operation_dir = self.checkpoint_dir / operation_id

        if not operation_dir.exists():
            return []

        checkpoints = []
        for checkpoint_file in operation_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                    checkpoints.append(OperationCheckpoint.from_dict(data))
            except Exception as e:
                logger.warning("Failed to load checkpoint %s: %s", checkpoint_file, e)

        # Sort by sequence number
        checkpoints.sort(key=lambda c: c.sequence_number)

        logger.debug("Found %s checkpoints for operation %s", len(checkpoints), operation_id)
        return checkpoints

    def delete_checkpoint(self, operation_id: str, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint.

        Args:
            operation_id: Operation ID
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        operation_dir = self.checkpoint_dir / operation_id

        if not operation_dir.exists():
            return False

        # Find and delete checkpoint file
        for checkpoint_file in operation_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file) as f:
                    data = json.load(f)
                    if data.get("checkpoint_id") == checkpoint_id:
                        checkpoint_file.unlink()
                        logger.info(
                            "Deleted checkpoint %s for operation %s", checkpoint_id, operation_id
                        )
                        return True
            except Exception as e:
                logger.warning("Failed to process checkpoint %s: %s", checkpoint_file, e)

        return False

    def delete_all_checkpoints(self, operation_id: str) -> int:
        """Delete all checkpoints for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Number of checkpoints deleted
        """
        operation_dir = self.checkpoint_dir / operation_id

        if not operation_dir.exists():
            return 0

        count = 0
        for checkpoint_file in operation_dir.glob("checkpoint_*.json"):
            try:
                checkpoint_file.unlink()
                count += 1
            except Exception as e:
                logger.warning("Failed to delete checkpoint %s: %s", checkpoint_file, e)

        # Delete latest.json
        latest_file = operation_dir / "latest.json"
        if latest_file.exists():
            latest_file.unlink()

        # Remove operation directory if empty
        try:
            operation_dir.rmdir()
        except OSError:
            pass  # Directory not empty

        logger.info("Deleted %s checkpoints for operation %s", count, operation_id)
        return count

    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """Clean up checkpoints older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of checkpoints deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        count = 0

        for operation_dir in self.checkpoint_dir.iterdir():
            if not operation_dir.is_dir():
                continue

            for checkpoint_file in operation_dir.glob("checkpoint_*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        checkpoint_file.unlink()
                        count += 1
                except Exception as e:
                    logger.warning("Failed to process checkpoint %s: %s", checkpoint_file, e)

            # Clean up empty operation directories
            try:
                if not list(operation_dir.iterdir()):
                    operation_dir.rmdir()
            except OSError:
                pass

        logger.info("Cleaned up %s checkpoints older than %s days", count, max_age_days)
        return count

    def get_statistics(self) -> dict[str, int]:
        """Get checkpoint store statistics.

        Returns:
            Dictionary with statistics
        """
        total_operations = 0
        total_checkpoints = 0

        for operation_dir in self.checkpoint_dir.iterdir():
            if not operation_dir.is_dir():
                continue

            total_operations += 1
            checkpoint_files = list(operation_dir.glob("checkpoint_*.json"))
            total_checkpoints += len(checkpoint_files)

        return {
            "total_operations": total_operations,
            "total_checkpoints": total_checkpoints,
            "avg_checkpoints_per_operation": total_checkpoints / total_operations
            if total_operations > 0
            else 0,
        }
