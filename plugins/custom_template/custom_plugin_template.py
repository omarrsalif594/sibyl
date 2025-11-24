"""
Custom Plugin Template

This template provides a starting point for creating custom Sibyl frontend plugins.
Adapt this for your frontend by mapping your events/actions to Sibyl pipelines.

Architecture:
- Event-based design for flexible integration
- Configuration-driven pipeline mapping
- Built-in error handling and logging
- Guardrails-aware execution

Usage:
1. Copy this template to your project
2. Modify template_config.yaml to map your events to pipelines
3. Implement your frontend-specific event handling
4. Add custom validation and guardrails as needed
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sibyl.runtime import WorkspaceRuntime, load_workspace_runtime

logger = logging.getLogger(__name__)


@dataclass
class PluginEvent:
    """
    Represents an event from your frontend.

    Attributes:
        event_type: Type of event (e.g., "user_query", "button_click")
        payload: Event data (parameters, context, etc.)
        user_id: Optional user identifier
        session_id: Optional session identifier
        metadata: Optional additional metadata
    """

    event_type: str
    payload: dict[str, Any]
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class PluginResponse:
    """
    Response from plugin execution.

    Attributes:
        success: Whether execution was successful
        result: Pipeline execution results
        event_type: Original event type
        execution_time_ms: Execution time in milliseconds
        error: Error message if execution failed
        metadata: Additional response metadata
    """

    success: bool
    result: Any
    event_type: str
    execution_time_ms: float
    error: str | None = None
    metadata: dict[str, Any] | None = None


class PluginConfigError(Exception):
    """Raised when plugin configuration is invalid."""


class PluginExecutionError(Exception):
    """Raised when plugin execution fails."""


class CustomPlugin:
    """
    Template for creating custom frontend plugins.

    This class provides:
    - Event-to-pipeline mapping
    - Workspace management
    - Error handling
    - Logging and metrics
    - Guardrails integration

    Adapt this template by:
    1. Modifying the configuration file to map your events
    2. Adding custom event handlers
    3. Implementing frontend-specific logic
    4. Adding validation and guardrails
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """
        Initialize the custom plugin.

        Args:
            config_path: Path to template_config.yaml. If None, uses default location.

        Raises:
            PluginConfigError: If configuration is invalid or missing
        """
        if config_path is None:
            module_dir = Path(__file__).parent
            config_path = module_dir / "template_config.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.workspace_cache: dict[str, WorkspaceRuntime] = {}
        self.event_handlers: dict[str, Callable] = {}

        # Register default event handlers
        self._register_default_handlers()

        logger.info("Custom plugin initialized with %s events", len(self.config["events"]))

    def _load_config(self) -> dict[str, Any]:
        """
        Load and validate plugin configuration.

        Returns:
            Parsed configuration dictionary

        Raises:
            PluginConfigError: If config is invalid or missing
        """
        if not self.config_path.exists():
            msg = f"Config file not found: {self.config_path}"
            raise PluginConfigError(msg)

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Failed to parse config YAML: {e}"
            raise PluginConfigError(msg) from e
        except Exception as e:
            msg = f"Failed to load config: {e}"
            raise PluginConfigError(msg) from e
        else:
            if not config or "events" not in config:
                msg = "Config must contain 'events' key"
                raise PluginConfigError(msg)

            # Validate each event mapping
            for event_type, event_config in config["events"].items():
                if "workspace" not in event_config:
                    msg = f"Event '{event_type}' missing 'workspace' field"
                    raise PluginConfigError(msg)
                if "pipeline" not in event_config:
                    msg = f"Event '{event_type}' missing 'pipeline' field"
                    raise PluginConfigError(msg)

            return config

    def _register_default_handlers(self) -> None:
        """
        Register default event handlers.

        Override this method to add custom event handlers for your frontend.
        """
        # Default handler for generic events
        self.register_handler("*", self._default_handler)

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a custom event handler.

        Event handlers are called before pipeline execution and can:
        - Modify the event payload
        - Add validation logic
        - Implement custom preprocessing
        - Return early if needed

        Args:
            event_type: Type of event to handle ("*" for all events)
            handler: Callable that takes (event: PluginEvent) -> PluginEvent
        """
        self.event_handlers[event_type] = handler
        logger.debug("Registered handler for event type: %s", event_type)

    def _default_handler(self, event: PluginEvent) -> PluginEvent:
        """
        Default event handler (pass-through).

        Override or replace this with custom logic.

        Args:
            event: Plugin event

        Returns:
            Modified or original event
        """
        return event

    def _get_workspace_runtime(self, workspace_path: str) -> WorkspaceRuntime:
        """
        Get or create a workspace runtime instance.

        Uses caching to avoid reloading the same workspace.

        Args:
            workspace_path: Path to workspace configuration

        Returns:
            WorkspaceRuntime instance

        Raises:
            PluginExecutionError: If workspace cannot be loaded
        """
        if workspace_path in self.workspace_cache:
            return self.workspace_cache[workspace_path]

        try:
            runtime = load_workspace_runtime(workspace_path)
            self.workspace_cache[workspace_path] = runtime
            logger.debug("Loaded workspace runtime: %s", workspace_path)
            return runtime
        except Exception as e:
            msg = f"Failed to load workspace '{workspace_path}': {e}"
            raise PluginExecutionError(msg) from e

    def get_event_config(self, event_type: str) -> dict[str, Any]:
        """
        Get configuration for a specific event type.

        Args:
            event_type: Type of event

        Returns:
            Event configuration dictionary

        Raises:
            PluginConfigError: If event type not found
        """
        if event_type not in self.config["events"]:
            available = ", ".join(self.config["events"].keys())
            msg = f"Event type '{event_type}' not found. Available events: {available}"
            raise PluginConfigError(msg)

        return self.config["events"][event_type]

    async def handle_event(self, event: PluginEvent) -> PluginResponse:
        """
        Handle a frontend event by executing the corresponding pipeline.

        This is the main entry point for plugin execution. It:
        1. Looks up the event configuration
        2. Applies custom event handlers
        3. Loads the appropriate workspace
        4. Executes the pipeline
        5. Returns results

        Args:
            event: Plugin event to handle

        Returns:
            PluginResponse with execution results

        Example:
            >>> plugin = CustomPlugin()
            >>> event = PluginEvent(
            ...     event_type="user_query_analytics",
            ...     payload={"question": "Show revenue"}
            ... )
            >>> response = await plugin.handle_event(event)
            >>> if response.success:
            ...     print(response.result)
        """
        import time  # noqa: PLC0415 - plugin registration

        start_time = time.time()

        try:
            # Get event configuration
            event_config = self.get_event_config(event.event_type)

            # Apply custom event handlers
            processed_event = self._apply_handlers(event)

            workspace_path = event_config["workspace"]
            pipeline_name = event_config["pipeline"]

            logger.info("Handling event '%s' -> pipeline '%s'", event.event_type, pipeline_name)
            logger.debug("Event payload: %s", processed_event.payload)

            # Get workspace runtime
            runtime = self._get_workspace_runtime(workspace_path)

            # Execute pipeline
            result = await runtime.run_pipeline(pipeline_name, **processed_event.payload)

            execution_time_ms = (time.time() - start_time) * 1000

            # Build response
            response = PluginResponse(
                success=True,
                result=result,
                event_type=event.event_type,
                execution_time_ms=execution_time_ms,
                metadata={
                    "pipeline_name": pipeline_name,
                    "workspace": workspace_path,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                },
            )

            logger.info("Event '%s' completed in %sms", event.event_type, execution_time_ms)
            return response

        except PluginConfigError as e:
            logger.exception("Configuration error: %s", e)
            raise

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.exception("Event handling failed: %s", e)

            return PluginResponse(
                success=False,
                result=None,
                event_type=event.event_type,
                execution_time_ms=execution_time_ms,
                error=str(e),
            )

    def _apply_handlers(self, event: PluginEvent) -> PluginEvent:
        """
        Apply registered event handlers to an event.

        Args:
            event: Original event

        Returns:
            Processed event (potentially modified by handlers)
        """
        # Apply specific handler if registered
        if event.event_type in self.event_handlers:
            event = self.event_handlers[event.event_type](event)

        # Apply wildcard handler if registered and no specific handler
        elif "*" in self.event_handlers:
            event = self.event_handlers["*"](event)

        return event

    def list_events(self) -> list[str]:
        """
        List all configured event types.

        Returns:
            List of event type names
        """
        return list(self.config["events"].keys())

    def get_event_description(self, event_type: str) -> str:
        """
        Get description of an event type.

        Args:
            event_type: Type of event

        Returns:
            Event description if available, otherwise empty string
        """
        event_config = self.get_event_config(event_type)
        return event_config.get("description", "")


# =============================================================================
# Example Custom Handler
# =============================================================================


def example_validation_handler(event: PluginEvent) -> PluginEvent:
    """
    Example custom event handler with validation.

    This demonstrates how to:
    - Validate event payload
    - Add metadata
    - Modify parameters
    - Implement guardrails

    Args:
        event: Original event

    Returns:
        Validated and potentially modified event

    Raises:
        ValueError: If validation fails
    """
    # Example: Validate required fields
    if "question" in event.payload:
        question = event.payload["question"]
        if not question or len(question.strip()) == 0:
            msg = "Question cannot be empty"
            raise ValueError(msg)

        # Example: Add safety guardrail
        forbidden_terms = ["delete", "drop", "truncate"]
        question_lower = question.lower()
        if any(term in question_lower for term in forbidden_terms):
            msg = "Question contains forbidden term"
            raise ValueError(msg)

    # Example: Add metadata
    if event.metadata is None:
        event.metadata = {}
    event.metadata["validated"] = True

    return event


# =============================================================================
# Example Usage
# =============================================================================


async def example_usage() -> None:
    """
    Example demonstrating custom plugin usage.
    """
    # Initialize plugin
    plugin = CustomPlugin()

    # Register custom handler
    plugin.register_handler("user_query_analytics", example_validation_handler)

    # Create event
    event = PluginEvent(
        event_type="user_query_analytics",
        payload={
            "question": "What is our Q3 revenue?",
            "time_period": "2024-Q3",
        },
        user_id="user123",
        session_id="session456",
    )

    # Handle event
    response = await plugin.handle_event(event)

    # Process response
    if response.success:
        pass
    else:
        pass


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())


__all__ = [
    "CustomPlugin",
    "PluginConfigError",
    "PluginEvent",
    "PluginExecutionError",
    "PluginResponse",
    "example_validation_handler",
]
