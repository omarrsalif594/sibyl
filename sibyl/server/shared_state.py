"""
Shared State Manager for MCP Server

Thread-safe state management shared between stdio and HTTP transports.
Allows VS Code extension (HTTP) and Claude Code (stdio) to share context.
"""

import logging
from datetime import datetime
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class SharedStateManager:
    """Thread-safe state manager shared between stdio and HTTP servers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = {
            "workspace_context": {
                "root_path": None,
                "current_model": None,
                "open_files": [],
            },
            "file_events": [],  # Recent file open/close events
            "test_results": {},  # Recent test results by model name
            "last_event_timestamp": None,
        }
        logger.info("SharedStateManager initialized")

    def set_workspace_root(self, root_path: str) -> None:
        """Set the workspace root path."""
        with self._lock:
            self._state["workspace_context"]["root_path"] = root_path
            logger.info("Workspace root set to: %s", root_path)

    def set_current_model(self, model_name: str | None) -> None:
        """Set the currently active model."""
        with self._lock:
            self._state["workspace_context"]["current_model"] = model_name
            if model_name:
                logger.info("Current model set to: %s", model_name)

    def add_file_event(self, event_type: str, model_name: str, file_path: str) -> None:
        """
        Record file event from VS Code.

        Args:
            event_type: Type of event ('opened', 'closed', 'changed', 'button_test', etc.)
            model_name: Name of the model
            file_path: Full path to the file
        """
        with self._lock:
            event = {
                "type": event_type,
                "model": model_name,
                "path": file_path,
                "timestamp": datetime.now().isoformat(),
            }
            self._state["file_events"].append(event)
            self._state["last_event_timestamp"] = datetime.now()

            # Update current model if file opened
            if event_type == "opened":
                self._state["workspace_context"]["current_model"] = model_name

                # Add to open files list if not already there
                if file_path not in self._state["workspace_context"]["open_files"]:
                    self._state["workspace_context"]["open_files"].append(file_path)

            # Remove from open files if closed
            elif event_type == "closed":
                if file_path in self._state["workspace_context"]["open_files"]:
                    self._state["workspace_context"]["open_files"].remove(file_path)

            # Keep only last 100 events
            if len(self._state["file_events"]) > 100:
                self._state["file_events"] = self._state["file_events"][-100:]

            logger.info("File event recorded: %s - %s", event_type, model_name)

    def get_recent_events(self, since_seconds: int = 10) -> list[dict]:
        """
        Get recent file events.

        Args:
            since_seconds: How many seconds back to look

        Returns:
            List of event dictionaries
        """
        with self._lock:
            if not self._state["file_events"]:
                return []

            cutoff = datetime.now().timestamp() - since_seconds
            return [
                e
                for e in self._state["file_events"]
                if datetime.fromisoformat(e["timestamp"]).timestamp() > cutoff
            ]

    def get_current_context(self) -> dict[str, Any]:
        """
        Get current workspace context.

        Returns:
            Dictionary with workspace context
        """
        with self._lock:
            return self._state["workspace_context"].copy()

    def get_current_model(self) -> str | None:
        """Get the currently active model name."""
        with self._lock:
            return self._state["workspace_context"]["current_model"]

    def get_open_files(self) -> list[str]:
        """Get list of currently open files."""
        with self._lock:
            return self._state["workspace_context"]["open_files"].copy()

    def update_test_result(self, model_name: str, result: dict[str, Any]) -> None:
        """
        Store test result for a model.

        Args:
            model_name: Name of the model
            result: Test result dictionary
        """
        with self._lock:
            self._state["test_results"][model_name] = {
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
            logger.info("Test result stored for: %s", model_name)

    def get_test_result(self, model_name: str) -> dict[str, Any] | None:
        """
        Get stored test result for a model.

        Args:
            model_name: Name of the model

        Returns:
            Test result dictionary or None
        """
        with self._lock:
            return self._state["test_results"].get(model_name)

    def get_all_test_results(self) -> dict[str, dict[str, Any]]:
        """Get all stored test results."""
        with self._lock:
            return self._state["test_results"].copy()

    def clear_test_results(self) -> None:
        """Clear all stored test results."""
        with self._lock:
            self._state["test_results"].clear()
            logger.info("Test results cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the current state."""
        with self._lock:
            return {
                "total_events": len(self._state["file_events"]),
                "open_files_count": len(self._state["workspace_context"]["open_files"]),
                "test_results_count": len(self._state["test_results"]),
                "current_model": self._state["workspace_context"]["current_model"],
                "last_event_timestamp": self._state["last_event_timestamp"].isoformat()
                if self._state["last_event_timestamp"]
                else None,
            }


# Global singleton instance
state_manager = SharedStateManager()
