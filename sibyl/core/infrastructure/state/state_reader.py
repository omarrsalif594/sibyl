"""
State reader for read-only query operations.

Provides thread-safe, read-only access to state database.
Can be used independently without write operations.
"""

import logging
from typing import Any

from .blob_manager import BlobManager
from .duckdb_client import DuckDBClient

logger = logging.getLogger(__name__)


class StateReader:
    """
    Read-only state query operations.

    Single Responsibility: Data retrieval

    Features:
    - Thread-safe (read-only operations)
    - No write dependencies
    - Can be replicated/load-balanced
    - Lightweight (no write queue overhead)

    Usage:
        client = DuckDBClient(db_path, read_only=True)
        reader = StateReader(client, blob_manager)

        conversation = await reader.get_conversation("conv-123")
        stats = await reader.get_stats()
    """

    def __init__(self, client: DuckDBClient, blob_manager: BlobManager | None = None) -> None:
        """
        Initialize state reader.

        Args:
            client: DuckDB client (should be read-only for safety)
            blob_manager: Optional blob manager for loading blobs
        """
        self.client = client
        self.blob_manager = blob_manager

        logger.debug("StateReader initialized")

    # =========================================================================
    # Conversation Queries
    # =========================================================================

    def get_conversation(self, id: str) -> dict[str, Any] | None:
        """
        Get conversation by ID.

        Args:
            id: Conversation ID

        Returns:
            Conversation dict or None
        """
        results = self.client.execute_read("SELECT * FROM conversations WHERE id = ?", (id,))
        if results:
            # Convert row tuple to dict
            row = results[0]
            columns = self._get_conversation_columns()
            return dict(zip(columns, row, strict=False))
        return None

    def list_conversations(
        self,
        status: str | None = None,
        workflow_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List conversations with optional filters.

        Args:
            status: Optional status filter
            workflow_type: Optional workflow type filter
            limit: Maximum number of results (default: 100)
            offset: Result offset for pagination (default: 0)

        Returns:
            List of conversation dicts
        """
        sql = "SELECT * FROM conversations WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)

        if workflow_type:
            sql += " AND workflow_type = ?"
            params.append(workflow_type)

        sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        results = self.client.execute_read(sql, tuple(params))
        columns = self._get_conversation_columns()

        return [dict(zip(columns, row, strict=False)) for row in results]

    def count_conversations(
        self, status: str | None = None, workflow_type: str | None = None
    ) -> int:
        """
        Count conversations with optional filters.

        Args:
            status: Optional status filter
            workflow_type: Optional workflow type filter

        Returns:
            Count of matching conversations
        """
        sql = "SELECT COUNT(*) FROM conversations WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)

        if workflow_type:
            sql += " AND workflow_type = ?"
            params.append(workflow_type)

        result = self.client.execute_read(sql, tuple(params))
        return result[0][0] if result else 0

    # =========================================================================
    # Checkpoint Queries
    # =========================================================================

    def get_checkpoint(self, id: str) -> dict[str, Any] | None:
        """
        Get checkpoint by ID.

        Args:
            id: Checkpoint ID

        Returns:
            Checkpoint dict or None
        """
        results = self.client.execute_read("SELECT * FROM phase_checkpoints WHERE id = ?", (id,))
        if results:
            columns = self._get_checkpoint_columns()
            return dict(zip(columns, results[0], strict=False))
        return None

    def list_checkpoints(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        List checkpoints for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of checkpoint dicts
        """
        results = self.client.execute_read(
            "SELECT * FROM phase_checkpoints WHERE conversation_id = ? ORDER BY phase_number",
            (conversation_id,),
        )
        columns = self._get_checkpoint_columns()
        return [dict(zip(columns, row, strict=False)) for row in results]

    # =========================================================================
    # Subagent Call Queries
    # =========================================================================

    def get_call(self, id: str) -> dict[str, Any] | None:
        """
        Get subagent call by ID.

        Args:
            id: Call ID

        Returns:
            Call dict or None
        """
        results = self.client.execute_read("SELECT * FROM subagent_calls WHERE id = ?", (id,))
        if results:
            columns = self._get_call_columns()
            return dict(zip(columns, results[0], strict=False))
        return None

    def query_subagent_calls(
        self, conversation_id: str, phase: str | None = None, agent_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Query subagent calls for a conversation.

        Args:
            conversation_id: Conversation ID
            phase: Optional phase filter
            agent_type: Optional agent type filter

        Returns:
            List of subagent call dicts
        """
        sql = "SELECT * FROM subagent_calls WHERE conversation_id = ?"
        params = [conversation_id]

        if phase:
            sql += " AND phase = ?"
            params.append(phase)

        if agent_type:
            sql += " AND agent_type = ?"
            params.append(agent_type)

        sql += " ORDER BY queued_at"

        results = self.client.execute_read(sql, tuple(params))
        columns = self._get_call_columns()
        return [dict(zip(columns, row, strict=False)) for row in results]

    # =========================================================================
    # Analytics Queries
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """
        Get state store statistics.

        Returns:
            Dict with various stats
        """
        # Conversation counts by status
        conv_stats = self.client.execute_read(
            "SELECT status, COUNT(*) as count FROM conversations GROUP BY status"
        )

        # Blob stats (if blob manager available)
        blob_stats = {}
        if self.blob_manager:
            blob_stats = self.blob_manager.get_stats()

        # Total tokens/cost
        totals = self.client.execute_read(
            "SELECT SUM(token_spent) as total_tokens, SUM(cost_usd) as total_cost FROM conversations"
        )

        return {
            "conversations": {row[0]: row[1] for row in conv_stats},
            "blobs": blob_stats,
            "totals": {
                "total_tokens": totals[0][0] if totals and totals[0][0] else 0,
                "total_cost": totals[0][1] if totals and totals[0][1] else 0.0,
            },
        }

    def get_token_usage(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """
        Get token usage statistics for a date range.

        Args:
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)

        Returns:
            Dict with token usage stats
        """
        sql = """
            SELECT
                COUNT(*) as conversation_count,
                SUM(token_spent) as total_tokens,
                AVG(token_spent) as avg_tokens,
                MAX(token_spent) as max_tokens,
                SUM(cost_usd) as total_cost
            FROM conversations
            WHERE 1=1
        """
        params = []

        if start_date:
            sql += " AND started_at >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND started_at <= ?"
            params.append(end_date)

        result = self.client.execute_read(sql, tuple(params))

        if result and result[0]:
            return {
                "conversation_count": result[0][0] or 0,
                "total_tokens": result[0][1] or 0,
                "avg_tokens": result[0][2] or 0.0,
                "max_tokens": result[0][3] or 0,
                "total_cost": result[0][4] or 0.0,
            }

        return {
            "conversation_count": 0,
            "total_tokens": 0,
            "avg_tokens": 0.0,
            "max_tokens": 0,
            "total_cost": 0.0,
        }

    # =========================================================================
    # Blob Operations
    # =========================================================================

    def load_blob(self, ref: str) -> str:
        """
        Load blob by reference.

        Args:
            ref: Blob SHA256 reference

        Returns:
            Blob content

        Raises:
            FileNotFoundError: If blob not found
            RuntimeError: If blob manager not configured
        """
        if not self.blob_manager:
            msg = "Blob manager not configured"
            raise RuntimeError(msg)

        return self.blob_manager.load(ref)

    def load_blob_preview(self, ref: str) -> str:
        """
        Load blob preview (safe, capped at 500 chars).

        Args:
            ref: Blob SHA256 reference

        Returns:
            Blob preview

        Raises:
            RuntimeError: If blob manager not configured
        """
        if not self.blob_manager:
            msg = "Blob manager not configured"
            raise RuntimeError(msg)

        return self.blob_manager.load_preview(ref)

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_conversation_columns(self) -> list[str]:
        """Get conversation table column names."""
        return [
            "id",
            "workflow_type",
            "started_at",
            "finished_at",
            "status",
            "token_budget",
            "token_spent",
            "cost_usd",
            "context_hash",
            "config_version",
            "created_by",
            "tags",
        ]

    def _get_checkpoint_columns(self) -> list[str]:
        """Get checkpoint table column names."""
        return [
            "id",
            "conversation_id",
            "phase",
            "phase_number",
            "status",
            "context_hash",
            "context_summary",
            "worker_count",
            "started_at",
            "finished_at",
            "duration_ms",
            "failures",
            "error",
        ]

    def _get_call_columns(self) -> list[str]:
        """Get subagent_calls table column names."""
        return [
            "call_key",
            "id",
            "conversation_id",
            "phase",
            "agent_type",
            "model_name",
            "temperature",
            "top_p",
            "system_prompt",
            "seed",
            "provider_fingerprint",
            "prompt_ref",
            "response_ref",
            "tokens_in_reserved",
            "tokens_in_actual",
            "tokens_out_actual",
            "cost_usd",
            "queued_at",
            "started_at",
            "finished_at",
            "queue_wait_ms",
            "provider_latency_ms",
            "total_duration_ms",
            "retry_of",
            "retry_count",
            "finish_reason",
            "error",
            "correlation_id",
            "span_id",
        ]
