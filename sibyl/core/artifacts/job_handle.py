"""Pollable Job Handle Artifact for long-running MCP operations.

This module provides typed artifacts for long-running jobs returned by MCP tools
like Conductor workflows, Chronulus forecasts, and Deep Code Reasoning conversations.
It implements automatic exponential backoff polling with configurable parameters.

Example:
    from sibyl.core.artifacts.job_handle import PollableJobHandle, JobStatus

    # Create from MCP response
    response = {"job_id": "wf_12345", "status": "pending"}
    handle = PollableJobHandle.from_mcp_response(
        response,
        provider="conductor",
        status_tool="get_workflow_status"
    )

    # Automatic polling with progress callback
    def on_progress(status):
        print(f"Progress: {status.get('progress', 0)}%")

    result = await handle.await_completion(mcp_adapter, on_progress)
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Standard job statuses across MCPs.

    These statuses normalize the various status strings returned by different
    MCP providers (Conductor, Chronulus, Deep Code Reasoning, etc.).
    """

    PENDING = "pending"  # Job queued but not started
    RUNNING = "running"  # Job actively executing
    COMPLETED = "completed"  # Job finished successfully
    FAILED = "failed"  # Job encountered an error
    TIMEOUT = "timeout"  # Job exceeded time limit
    CANCELLED = "cancelled"  # Job was explicitly cancelled


@dataclass
class PollableJobHandle:
    """Artifact for long-running MCP jobs with automatic polling.

    This artifact represents a job handle returned by an MCP tool that requires
    polling to check completion status. It provides automatic exponential backoff
    polling with configurable parameters.

    Design Principles:
    - Explicit: All network calls require passing MCPToolAdapter
    - Serializable: Can be JSON-serialized for persistence/debugging
    - Configurable: All polling parameters adjustable
    - Simple: No magic, clear control flow

    Attributes:
        provider: MCP provider name (e.g., "conductor", "chronulus")
        job_id: Unique job identifier from MCP
        job_type: Type of job (e.g., "workflow", "forecast", "conversation")
        status_tool: Tool name for checking job status
        result_tool: Optional tool name for retrieving final results
        initial_delay: Initial polling delay in seconds (default: 1.0)
        max_delay: Maximum polling delay in seconds (default: 60.0)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        timeout: Maximum time to wait in seconds (default: 3600.0 = 1 hour)
        current_status: Current job status (updated during polling)
        result: Final job result (set when completed)
        start_time: Timestamp when polling started
        poll_count: Number of status checks performed

    Example:
        # Automatic polling
        handle = PollableJobHandle(
            provider="conductor",
            job_id="wf_12345",
            job_type="workflow",
            status_tool="get_workflow_status",
            result_tool="get_workflow_execution"
        )
        result = await handle.await_completion(mcp_adapter)

        # Manual polling with progress callback
        def on_progress(status_result):
            print(f"Progress: {status_result.get('progress', 0)}%")

        result = await handle.await_completion(
            mcp_adapter,
            progress_callback=on_progress
        )
    """

    # Core identifiers
    provider: str
    job_id: str
    job_type: str
    status_tool: str
    result_tool: str | None = None

    # Polling configuration
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    timeout: float = 3600.0

    # State tracking
    current_status: JobStatus = JobStatus.PENDING
    result: dict[str, Any] | None = None
    start_time: datetime | None = None
    poll_count: int = 0

    async def await_completion(
        self,
        mcp_adapter: "MCPToolAdapter",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Poll until job completes with exponential backoff.

        This method polls the MCP provider using the specified status_tool until
        the job reaches a terminal state (COMPLETED, FAILED, CANCELLED, TIMEOUT).
        It uses exponential backoff to avoid overwhelming the MCP server.

        Args:
            mcp_adapter: MCP adapter instance for making tool calls
            progress_callback: Optional callback invoked after each poll with status result

        Returns:
            Final job result dictionary

        Raises:
            JobTimeoutError: If job exceeds timeout without completing
            JobFailedError: If job status indicates failure
            JobCancelledError: If job was cancelled
            MCPToolExecutionError: If status polling fails

        Example:
            adapter = MCPToolAdapter(provider, "start_workflow")
            result = await adapter(workflow_name="etl")

            handle = PollableJobHandle.from_mcp_response(result, provider, "get_status")
            final_result = await handle.await_completion(adapter)
        """
        # Record start time
        if self.start_time is None:
            self.start_time = datetime.now()

        start_timestamp = asyncio.get_event_loop().time()
        delay = self.initial_delay

        logger.info(
            f"Starting job polling: provider={self.provider}, "
            f"job_id={self.job_id}, timeout={self.timeout}s"
        )

        while True:
            self.poll_count += 1

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_timestamp
            if elapsed > self.timeout:
                logger.error(
                    f"Job {self.job_id} timed out after {elapsed:.1f}s ({self.poll_count} polls)"
                )
                msg = f"Job {self.job_id} timed out after {elapsed:.1f}s"
                raise JobTimeoutError(msg)

            # Poll status
            logger.debug(
                f"Poll #{self.poll_count} for job {self.job_id} "
                f"(delay={delay:.1f}s, elapsed={elapsed:.1f}s)"
            )

            status_result = await mcp_adapter(job_id=self.job_id)

            # Update status
            previous_status = self.current_status
            self.current_status = self._parse_status(status_result)

            if previous_status != self.current_status:
                logger.info(
                    f"Job {self.job_id} status changed: "
                    f"{previous_status.value} -> {self.current_status.value}"
                )

            # Invoke progress callback
            if progress_callback:
                try:
                    progress_callback(status_result)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}", exc_info=True)

            # Check terminal states
            if self.current_status == JobStatus.COMPLETED:
                logger.info(
                    f"Job {self.job_id} completed after {elapsed:.1f}s ({self.poll_count} polls)"
                )

                # Get final result if result_tool specified
                if self.result_tool:
                    # Create new adapter for result tool
                    from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

                    result_adapter = MCPToolAdapter(mcp_adapter.provider, self.result_tool)
                    self.result = await result_adapter(job_id=self.job_id)
                else:
                    self.result = status_result

                return self.result

            if self.current_status == JobStatus.FAILED:
                error_msg = status_result.get("error", "Unknown error")
                logger.error("Job %s failed: %s", self.job_id, error_msg)
                msg = f"Job {self.job_id} failed: {error_msg}"
                raise JobFailedError(msg)

            if self.current_status == JobStatus.CANCELLED:
                logger.warning("Job %s was cancelled", self.job_id)
                msg = f"Job {self.job_id} was cancelled"
                raise JobCancelledError(msg)

            # Sleep with exponential backoff
            await asyncio.sleep(delay)
            delay = min(delay * self.backoff_factor, self.max_delay)

    def _parse_status(self, status_result: dict[str, Any]) -> JobStatus:
        """Parse status from MCP tool response.

        This method normalizes various status strings from different MCP providers
        into the standard JobStatus enum. It handles common status strings like
        "running", "in_progress", "completed", "succeeded", etc.

        Args:
            status_result: Raw status response from MCP tool

        Returns:
            Normalized JobStatus enum value

        Note:
            If status cannot be determined, defaults to RUNNING to continue polling.
        """
        # Check for explicit status field
        status_str = status_result.get("status", "").lower()

        # Map common status strings to JobStatus enum
        status_map = {
            # Pending states
            "pending": JobStatus.PENDING,
            "queued": JobStatus.PENDING,
            "submitted": JobStatus.PENDING,
            # Running states
            "running": JobStatus.RUNNING,
            "in_progress": JobStatus.RUNNING,
            "processing": JobStatus.RUNNING,
            "executing": JobStatus.RUNNING,
            # Completed states
            "completed": JobStatus.COMPLETED,
            "succeeded": JobStatus.COMPLETED,
            "finished": JobStatus.COMPLETED,
            "done": JobStatus.COMPLETED,
            "success": JobStatus.COMPLETED,
            # Failed states
            "failed": JobStatus.FAILED,
            "error": JobStatus.FAILED,
            "errored": JobStatus.FAILED,
            # Timeout states
            "timeout": JobStatus.TIMEOUT,
            "timed_out": JobStatus.TIMEOUT,
            # Cancelled states
            "cancelled": JobStatus.CANCELLED,
            "canceled": JobStatus.CANCELLED,
            "aborted": JobStatus.CANCELLED,
            "terminated": JobStatus.CANCELLED,
        }

        mapped_status = status_map.get(status_str)
        if mapped_status:
            return mapped_status

        # Fallback: check for boolean 'completed' field
        if status_result.get("completed") is True:
            return JobStatus.COMPLETED

        # Default to RUNNING to continue polling
        logger.debug(f"Unknown status '{status_str}' for job {self.job_id}, defaulting to RUNNING")
        return JobStatus.RUNNING

    async def cancel(self, mcp_adapter: "MCPToolAdapter") -> None:
        """Attempt to cancel the running job.

        This method attempts to cancel the job by calling a cancel tool on the
        MCP provider. Not all providers support cancellation. If the cancel tool
        is not found, a warning is logged but no error is raised.

        Args:
            mcp_adapter: MCP adapter instance for making tool calls

        Raises:
            MCPToolExecutionError: If cancellation call fails (other than not found)

        Example:
            handle = PollableJobHandle(...)
            await handle.cancel(adapter)
        """
        try:
            # Try to call cancel_job tool
            from sibyl.runtime.providers.mcp_adapters import MCPToolAdapter

            cancel_adapter = MCPToolAdapter(mcp_adapter.provider, "cancel_job")
            await cancel_adapter(job_id=self.job_id)

            self.current_status = JobStatus.CANCELLED
            logger.info("Job %s cancellation requested", self.job_id)

        except Exception as e:
            # Check if tool not found
            if "not found" in str(e).lower():
                logger.warning("Provider %s does not support job cancellation", self.provider)
            else:
                logger.exception("Failed to cancel job %s: %s", self.job_id, e)
                raise

    @classmethod
    def from_mcp_response(
        cls,
        response: dict[str, Any],
        provider: str,
        status_tool: str,
        job_type: str = "unknown",
        result_tool: str | None = None,
        **kwargs,
    ) -> "PollableJobHandle":
        """Factory method to create handle from MCP tool response.

        This convenience method extracts the job_id from an MCP response and
        creates a PollableJobHandle. It's useful for pipeline integration.

        Args:
            response: MCP tool response containing job_id
            provider: MCP provider name
            status_tool: Tool name for checking status
            job_type: Type of job (optional)
            result_tool: Tool name for retrieving results (optional)
            **kwargs: Additional PollableJobHandle parameters

        Returns:
            New PollableJobHandle instance

        Raises:
            ValueError: If response doesn't contain job_id

        Example:
            response = await start_workflow_tool(name="etl")
            handle = PollableJobHandle.from_mcp_response(
                response,
                provider="conductor",
                status_tool="get_workflow_status"
            )
        """
        job_id = response.get("job_id")
        if not job_id:
            msg = f"MCP response does not contain job_id: {response}"
            raise ValueError(msg)

        return cls(
            provider=provider,
            job_id=job_id,
            job_type=job_type,
            status_tool=status_tool,
            result_tool=result_tool,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for debugging/persistence.

        Returns:
            Dictionary representation (JSON-serializable)
        """
        return {
            "provider": self.provider,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status_tool": self.status_tool,
            "result_tool": self.result_tool,
            "initial_delay": self.initial_delay,
            "max_delay": self.max_delay,
            "backoff_factor": self.backoff_factor,
            "timeout": self.timeout,
            "current_status": self.current_status.value,
            "poll_count": self.poll_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }


# Custom exceptions
class JobError(Exception):
    """Base exception for job-related errors."""


class JobTimeoutError(JobError):
    """Raised when job exceeds timeout without completing."""


class JobFailedError(JobError):
    """Raised when job status indicates failure."""


class JobCancelledError(JobError):
    """Raised when job was cancelled."""
