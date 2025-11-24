"""JSON file-based learning store implementation."""

import contextlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from sibyl.mcp_server.infrastructure.learning.protocol import (
    FixOutcome,
    LearningRecord,
)

logger = logging.getLogger(__name__)


class JSONLearningStore:
    """JSON file-based learning store.

    from typing import Dict, List
        Stores learning records as JSON files in a directory structure:
        learning_dir/
            records/
                {year}/
                    {month}/
                        record_{record_id}.json
            index.json  # Index for fast lookups

        Thread-safety: Not thread-safe. Use file locking for concurrent access.
    """

    def __init__(self, learning_dir: Path | str | None = None) -> None:
        """Initialize JSON learning store.

        Args:
            learning_dir: Directory to store learning records (uses system temp dir if None)
        """
        # Use system temp dir for portability (Windows/Linux/Mac)
        if learning_dir is None:
            import tempfile

            learning_dir = Path(tempfile.gettempdir()) / "sibyl_learning"
        self.learning_dir = Path(learning_dir)
        self.records_dir = self.learning_dir / "records"
        self.records_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.learning_dir / "index.json"
        self._index = self._load_index()

        logger.info("Initialized JSON learning store at %s", self.learning_dir)

    def _load_index(self) -> dict:
        """Load index file.

        Returns:
            Index dictionary
        """
        if not self.index_file.exists():
            return {"records": [], "categories": defaultdict(list)}

        try:
            with open(self.index_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load index, starting fresh: %s", e)
            return {"records": [], "categories": defaultdict(list)}

    def _save_index(self) -> None:
        """Save index file."""
        try:
            with open(self.index_file, "w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.exception("Failed to save index: %s", e)

    def save_record(self, record: LearningRecord) -> None:
        """Save a learning record.

        Args:
            record: Learning record to save
        """
        # Create year/month directory structure
        year_month = record.created_at.strftime("%Y/%m")
        record_dir = self.records_dir / year_month
        record_dir.mkdir(parents=True, exist_ok=True)

        # Save record file
        record_file = record_dir / f"record_{record.record_id}.json"
        with open(record_file, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

        # Update index
        self._index["records"].append(
            {
                "record_id": record.record_id,
                "category": record.error_category,
                "outcome": record.outcome.value,
                "created_at": record.created_at.isoformat(),
                "path": str(record_file.relative_to(self.learning_dir)),
            }
        )

        # Update category index
        if "categories" not in self._index:
            self._index["categories"] = defaultdict(list)

        if record.error_category not in self._index["categories"]:
            self._index["categories"][record.error_category] = []

        self._index["categories"][record.error_category].append(record.record_id)

        self._save_index()

        logger.debug(
            "Saved learning record %s for category %s", record.record_id, record.error_category
        )

    def load_record(self, record_id: str) -> Optional[LearningRecord]:
        """Load a specific record.

        Args:
            record_id: Record ID

        Returns:
            Record or None if not found
        """
        # Find record in index
        record_info = next(
            (r for r in self._index.get("records", []) if r["record_id"] == record_id), None
        )

        if not record_info:
            logger.debug("Record %s not found in index", record_id)
            return None

        # Load from file
        record_path = self.learning_dir / record_info["path"]

        try:
            with open(record_path) as f:
                data = json.load(f)
                return LearningRecord.from_dict(data)
        except Exception as e:
            logger.exception("Failed to load record %s: %s", record_id, e)
            return None

    def list_records(
        self,
        category: Optional[str] = None,
        outcome: Optional[FixOutcome] = None,
        limit: int = 100,
    ) -> List[LearningRecord]:
        """List learning records with optional filters.

        Args:
            category: Filter by error category
            outcome: Filter by outcome
            limit: Maximum records to return

        Returns:
            List of records
        """
        # Filter records from index
        filtered_records = self._index.get("records", [])

        if category:
            filtered_records = [r for r in filtered_records if r.get("category") == category]

        if outcome:
            filtered_records = [r for r in filtered_records if r.get("outcome") == outcome.value]

        # Sort by created_at (newest first)
        filtered_records.sort(key=lambda r: r.get("created_at", ""), reverse=True)

        # Apply limit
        filtered_records = filtered_records[:limit]

        # Load full records
        records = []
        for record_info in filtered_records:
            record = self.load_record(record_info["record_id"])
            if record:
                records.append(record)

        logger.debug("Listed %s records (category=%s, outcome=%s)", len(records), category, outcome)

        return records

    def get_statistics(self) -> Dict[str, any]:
        """Get learning statistics.

        Returns:
            Dictionary with statistics
        """
        total_records = len(self._index.get("records", []))

        outcome_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for record_info in self._index.get("records", []):
            outcome_counts[record_info.get("outcome", "unknown")] += 1
            category_counts[record_info.get("category", "unknown")] += 1

        success_count = outcome_counts.get("success", 0)
        failure_count = outcome_counts.get("failure", 0)
        total_outcomes = success_count + failure_count

        success_rate = success_count / total_outcomes if total_outcomes > 0 else 0.0

        return {
            "total_records": total_records,
            "success_count": success_count,
            "failure_count": failure_count,
            "partial_count": outcome_counts.get("partial", 0),
            "success_rate": success_rate,
            "category_counts": dict(category_counts),
            "total_categories": len(category_counts),
        }

    def delete_old_records(self, max_age_days: int = 90) -> int:
        """Delete records older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        deleted_count = 0

        # Find old records in index
        old_records = [
            r
            for r in self._index.get("records", [])
            if datetime.fromisoformat(r["created_at"]) < cutoff_date
        ]

        for record_info in old_records:
            # Delete file
            record_path = self.learning_dir / record_info["path"]
            try:
                if record_path.exists():
                    record_path.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete record file %s: %s", record_path, e)

            # Remove from index
            self._index["records"].remove(record_info)

            # Remove from category index
            category = record_info.get("category")
            if category in self._index.get("categories", {}):
                with contextlib.suppress(ValueError):
                    self._index["categories"][category].remove(record_info["record_id"])

        self._save_index()

        logger.info("Deleted %s learning records older than %s days", deleted_count, max_age_days)

        return deleted_count

    def get_records_by_category(self, category: str) -> List[LearningRecord]:
        """Get all records for a specific category.

        Args:
            category: Error category

        Returns:
            List of records for that category
        """
        return self.list_records(category=category, limit=1000)

    def get_success_patterns(
        self, category: Optional[str] = None, min_success_rate: float = 0.7
    ) -> List[dict]:
        """Get successful fix patterns.

        Args:
            category: Optional category filter
            min_success_rate: Minimum success rate to include

        Returns:
            List of successful patterns
        """
        records = self.list_records(category=category, limit=1000)

        # Group by fix_applied
        fix_groups = defaultdict(list)
        for record in records:
            fix_groups[record.fix_applied].append(record)

        # Calculate success rates
        patterns = []
        for fix, fix_records in fix_groups.items():
            success_count = sum(1 for r in fix_records if r.outcome == FixOutcome.SUCCESS)
            total_count = len(fix_records)
            success_rate = success_count / total_count if total_count > 0 else 0.0

            if success_rate >= min_success_rate and total_count >= 2:
                patterns.append(
                    {
                        "fix": fix,
                        "success_count": success_count,
                        "total_count": total_count,
                        "success_rate": success_rate,
                        "category": category or "mixed",
                        "models": [r.model_name for r in fix_records if r.model_name],
                    }
                )

        # Sort by success rate then count
        patterns.sort(key=lambda p: (p["success_rate"], p["total_count"]), reverse=True)

        return patterns
