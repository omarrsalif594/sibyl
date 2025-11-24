"""Single-writer queue for DuckDB with batched transactions."""

import asyncio
import contextlib
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateWriter:
    """Single-writer pattern for DuckDB to avoid lock contention.

    Features:
    - Async queue for write operations
    - Batched transactions (up to 100 writes per batch)
    - 100ms batch window for low latency
    - Error handling with future completion
    """

    MAX_BATCH_SIZE = 100
    BATCH_WINDOW_MS = 100

    def __init__(self, db_path: Path) -> None:
        """Initialize state writer.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self._queue: asyncio.Queue[tuple[str, tuple, asyncio.Future]] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._conn = None
        self._running = False

        logger.info("State writer initialized for: %s", db_path)

    async def start(self) -> None:
        """Start the writer worker loop."""
        if self._running:
            logger.warning("Writer already running")
            return

        # Import DuckDB
        try:
            import duckdb  # optional dependency

            self._duckdb = duckdb
        except ImportError:
            msg = "DuckDB not installed. Install with: pip install duckdb"
            raise ImportError(msg)

        # Open connection
        self._conn = self._duckdb.connect(str(self.db_path))

        # Start worker
        self._running = True
        self._worker_task = asyncio.create_task(self._writer_loop())

        logger.info("State writer started")

    async def stop(self) -> None:
        """Stop the writer worker loop."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        if self._conn:
            self._conn.close()
            self._conn = None

        logger.info("State writer stopped")

    async def write(self, query: str, params: tuple = ()) -> None:
        """Enqueue write operation.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Awaitable that completes when write is committed

        Raises:
            Exception: If write fails
        """
        if not self._running:
            msg = "Writer not running. Call start() first."
            raise RuntimeError(msg)

        future: asyncio.Future = asyncio.Future()
        await self._queue.put((query, params, future))

        # Wait for write to complete
        return await future

    async def write_many(self, operations: list[tuple[str, tuple]]) -> None:
        """Enqueue multiple write operations (will be batched).

        Args:
            operations: List of (query, params) tuples

        Returns:
            Awaitable that completes when all writes are committed
        """
        futures = []

        for query, params in operations:
            future: asyncio.Future = asyncio.Future()
            await self._queue.put((query, params, future))
            futures.append(future)

        # Wait for all writes
        await asyncio.gather(*futures)

    async def _writer_loop(self) -> None:
        """Main writer loop - processes queue in batches."""
        logger.info("Writer loop started")

        while self._running:
            try:
                batch = await self._collect_batch()

                if batch:
                    await self._execute_batch(batch)

            except asyncio.CancelledError:
                logger.info("Writer loop cancelled")
                break

            except Exception as e:
                logger.exception("Error in writer loop: %s", e)
                # Continue running despite errors

        logger.info("Writer loop stopped")

    async def _collect_batch(self) -> list[tuple[str, tuple, asyncio.Future]]:
        """Collect a batch of writes.

        Returns:
            List of (query, params, future) tuples
        """
        batch = []
        deadline = time.monotonic() + (self.BATCH_WINDOW_MS / 1000.0)

        while len(batch) < self.MAX_BATCH_SIZE and time.monotonic() < deadline:
            try:
                timeout = max(0, deadline - time.monotonic())
                item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                batch.append(item)

            except TimeoutError:
                # Batch window expired
                break

        return batch

    async def _execute_batch(self, batch: list[tuple[str, tuple, asyncio.Future]]) -> None:
        """Execute batch in a single transaction.

        Args:
            batch: List of (query, params, future) tuples
        """
        if not batch:
            return

        start_time = time.monotonic()

        try:
            # Begin transaction
            self._conn.begin()

            # Execute all queries
            for query, params, _ in batch:
                self._conn.execute(query, params)

            # Commit transaction
            self._conn.commit()

            # Mark all futures as completed
            for _, _, future in batch:
                if not future.done():
                    future.set_result(None)

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.debug("Batch committed: %s operations in %sms", len(batch), elapsed_ms)
        except Exception as e:
            # Rollback on error
            try:
                self._conn.rollback()
            except Exception as rollback_error:
                logger.exception("Error during rollback: %s", rollback_error)

            # Mark all futures as failed
            for _, _, future in batch:
                if not future.done():
                    future.set_exception(e)

            logger.exception("Batch failed: %s", e)

    def query(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute read query (synchronous, safe for concurrent reads).

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dicts
        """
        if not self._conn:
            msg = "Writer not started"
            raise RuntimeError(msg)

        result = self._conn.execute(query, params).fetchall()

        # Convert to list of dicts
        if result:
            columns = [desc[0] for desc in self._conn.description]
            return [dict(zip(columns, row, strict=False)) for row in result]
        return []

    async def query_async(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute read query (async wrapper).

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dicts
        """
        # DuckDB reads are safe even with single writer
        return self.query(query, params)
