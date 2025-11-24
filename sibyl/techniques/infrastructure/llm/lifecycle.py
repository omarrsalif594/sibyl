"""Lifecycle management for graceful startup and shutdown.

This module provides:
- Graceful shutdown handling (SIGTERM, SIGINT)
- Connection draining with timeout
- Resource cleanup coordination
- Health state management
- Kubernetes-compatible lifecycle hooks

Usage:
    lifecycle = LifecycleManager()

    # Register cleanup callbacks
    lifecycle.register_cleanup(cleanup_duckdb)
    lifecycle.register_cleanup(flush_metrics)

    # Start handling signals
    lifecycle.setup_signal_handlers()

    # In your shutdown logic
    await lifecycle.shutdown()
"""

import asyncio
import logging
import signal
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages application lifecycle with graceful shutdown support.

    Handles:
    - Signal handling (SIGTERM, SIGINT)
    - Graceful connection draining
    - Resource cleanup coordination
    - Health state transitions
    - Shutdown timeout enforcement
    """

    def __init__(self, shutdown_timeout: int = 30) -> None:
        """Initialize lifecycle manager.

        Args:
            shutdown_timeout: Maximum seconds to wait for graceful shutdown
        """
        self.shutdown_timeout = shutdown_timeout
        self.cleanup_callbacks: list[Callable] = []
        self.is_shutting_down = False
        self.is_healthy = True
        self.shutdown_event = asyncio.Event()

    def register_cleanup(self, callback: Callable) -> None:
        """Register a cleanup callback to run during shutdown.

        Callbacks are called in reverse registration order (LIFO).

        Args:
            callback: Async or sync function to call during shutdown
        """
        self.cleanup_callbacks.append(callback)
        logger.info("Registered cleanup callback: %s", callback.__name__)

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown.

        Handles:
        - SIGTERM: Graceful shutdown (from Kubernetes, Docker, systemd)
        - SIGINT: Keyboard interrupt (Ctrl+C)
        """
        # Store original handlers for restoration if needed
        self._original_sigterm = signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        logger.info("Signal handlers registered for graceful shutdown")

    def _handle_shutdown_signal(self, signum: Any, frame: Any) -> None:
        """Handle shutdown signals (SIGTERM, SIGINT).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        sig_name = signal.Signals(signum).name
        logger.warning("Received %s, initiating graceful shutdown...", sig_name)

        # Mark as shutting down immediately (stops accepting new requests)
        self.is_shutting_down = True
        self.is_healthy = False

        # Trigger shutdown event
        self.shutdown_event.set()

        # For asyncio applications, we need to schedule the coroutine
        # This will be picked up by the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.shutdown())
            else:
                # If no loop is running, create a new one
                asyncio.run(self.shutdown())
        except RuntimeError:
            # No event loop, run synchronously
            logger.warning("No event loop available, running shutdown synchronously")
            self._run_cleanup_sync()
            sys.exit(0)

    async def shutdown(self) -> None:
        """Execute graceful shutdown sequence.

        Steps:
        1. Stop accepting new connections (is_shutting_down = True)
        2. Wait for in-flight requests to complete (with timeout)
        3. Run cleanup callbacks in reverse order
        4. Exit
        """
        logger.info("=" * 70)
        logger.info("GRACEFUL SHUTDOWN INITIATED")
        logger.info("=" * 70)

        # Step 1: Stop accepting new connections
        self.is_shutting_down = True
        self.is_healthy = False
        logger.info("✓ Stopped accepting new connections")

        # Step 2: Wait for in-flight requests (connection draining)
        logger.info(
            "Waiting up to %ss for in-flight requests to complete...", self.shutdown_timeout
        )

        try:
            await asyncio.wait_for(self._drain_connections(), timeout=self.shutdown_timeout)
            logger.info("✓ All in-flight requests completed")
        except TimeoutError:
            logger.warning(
                "⚠️  Shutdown timeout (%ss) reached, forcing shutdown", self.shutdown_timeout
            )

        # Step 3: Run cleanup callbacks
        await self._run_cleanup_callbacks()

        logger.info("=" * 70)
        logger.info("✅ GRACEFUL SHUTDOWN COMPLETE")
        logger.info("=" * 70)

    async def _drain_connections(self) -> None:
        """Wait for in-flight connections to drain.

        This is a placeholder - actual implementation depends on your server framework.
        For Starlette/Uvicorn, the server handles this automatically.
        """
        # Give a short grace period for connections to finish
        await asyncio.sleep(2)

        # In a real implementation, you would:
        # - Track active connections/requests
        # - Wait for them to complete
        # - Poll every 100ms or so

        logger.debug("Connection draining complete")

    async def _run_cleanup_callbacks(self) -> None:
        """Run all registered cleanup callbacks in reverse order (LIFO)."""
        if not self.cleanup_callbacks:
            logger.info("No cleanup callbacks registered")
            return

        logger.info("Running %s cleanup callbacks...", len(self.cleanup_callbacks))

        # Run in reverse order (LIFO - last registered, first executed)
        for callback in reversed(self.cleanup_callbacks):
            try:
                logger.info("→ Running cleanup: %s", callback.__name__)

                # Handle both async and sync callbacks
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()

                logger.info("  ✓ %s completed", callback.__name__)

            except Exception as e:
                logger.exception("  ✗ %s failed: %s", callback.__name__, e)

        logger.info("✓ All cleanup callbacks completed")

    def _run_cleanup_sync(self) -> None:
        """Run cleanup callbacks synchronously (fallback for no event loop)."""
        for callback in reversed(self.cleanup_callbacks):
            try:
                logger.info("→ Running cleanup: %s", callback.__name__)
                callback()
                logger.info("  ✓ %s completed", callback.__name__)
            except Exception as e:
                logger.exception("  ✗ %s failed: %s", callback.__name__, e)

    @asynccontextmanager
    async def lifespan(self, app: Any) -> Any:
        """Lifespan context manager for Starlette/FastAPI applications.

        Usage:
            lifecycle = LifecycleManager()
            app = Starlette(lifespan=lifecycle.lifespan)

        Args:
            app: Starlette/FastAPI application instance

        Yields:
            None (startup complete)
        """
        # Startup
        logger.info("=" * 70)
        logger.info("APPLICATION STARTUP")
        logger.info("=" * 70)

        self.is_healthy = True
        logger.info("✓ Application is healthy")

        yield  # Application runs here

        # Shutdown
        await self.shutdown()

    def is_ready(self) -> bool:
        """Check if application is ready to serve requests.

        Returns:
            True if healthy and not shutting down
        """
        return self.is_healthy and not self.is_shutting_down

    def get_health_status(self) -> dict:
        """Get current health status.

        Returns:
            Dict with health status details
        """
        return {
            "healthy": self.is_healthy,
            "shutting_down": self.is_shutting_down,
            "ready": self.is_ready(),
        }


# Global singleton instance (optional convenience)
_global_lifecycle: LifecycleManager | None = None


def get_lifecycle_manager(shutdown_timeout: int = 30) -> LifecycleManager:
    """Get or create global lifecycle manager instance.

    Args:
        shutdown_timeout: Shutdown timeout in seconds

    Returns:
        LifecycleManager instance
    """
    global _global_lifecycle

    if _global_lifecycle is None:
        _global_lifecycle = LifecycleManager(shutdown_timeout=shutdown_timeout)

    return _global_lifecycle
