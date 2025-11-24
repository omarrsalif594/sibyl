"""
Tool registry for managing MCP tools with versioning.

Provides centralized registration, discovery, and versioned tool retrieval.

Usage:
    from sibyl.framework.container import DIContainer
    container = DIContainer()
    registry = container.get_tool_registry()
"""

import json
import logging
from pathlib import Path

from .tool_interface import Tool, ToolMetadata

logger = logging.getLogger(__name__)


def parse_semver(version: str) -> tuple[int, int, int]:
    """
    Parse semver string into comparable tuple.

    Args:
        version: Semver string (e.g., "2.10.0")

    Returns:
        Tuple of (major, minor, patch) as integers

    Raises:
        ValueError: If version is not valid semver
    """
    parts = version.split(".")
    if len(parts) != 3:
        msg = f"Invalid semver (expected X.Y.Z): {version}"
        raise ValueError(msg)
    try:
        return tuple(int(p) for p in parts)  # type: ignore
    except ValueError as e:
        msg = f"Invalid semver (non-integer part): {version}"
        raise ValueError(msg) from e


class ToolRegistry:
    """
    Central registry for all MCP tools.

    This class is thread-safe for read operations (get, list_tools).
    Write operations (register) should be performed during initialization only.

    Features:
    - Semver versioning with "latest" support
    - Category-based organization
    - Tag-based indexing for discovery
    - Execution routing with statistics
    - MCP and OpenAPI tool definitions
    - Tool lifecycle management

    Metrics tracked:
    - tool_registry_operations_total: Total operations (register, get, list)
    - registered_tools_count: Current number of registered tools
    """

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Tool]] = {}  # {name: {version: tool}}
        self._version_cache: dict[str, list[tuple[int, int, int]]] = {}  # {name: [sorted versions]}
        self._tags_index: dict[str, list[str]] = {}  # {tag: [tool_names]}

        # Metrics
        self._metrics = {
            "operations_total": 0,
            "register_total": 0,
            "get_total": 0,
            "list_total": 0,
            "execute_total": 0,
        }

        # Execution statistics per tool
        self._execution_stats: dict[str, dict[str, any]] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool with name+version.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool is invalid or already registered
        """
        self._metrics["operations_total"] += 1
        self._metrics["register_total"] += 1

        name = tool.metadata.name
        version = tool.metadata.version

        # Validate semver
        try:
            parse_semver(version)
        except ValueError as e:
            msg = f"Cannot register tool '{name}': {e}"
            raise ValueError(msg) from e

        # Check for duplicates
        if name in self._tools and version in self._tools[name]:
            msg = f"Tool '{name}@{version}' already registered"
            raise ValueError(msg)

        # Register
        if name not in self._tools:
            self._tools[name] = {}
            self._version_cache[name] = []

        self._tools[name][version] = tool
        self._version_cache[name].append(parse_semver(version))
        self._version_cache[name].sort(reverse=True)  # Highest first

        # Index by tags
        for tag in tool.metadata.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            # Store as name@version for tag lookup
            tool_key = f"{name}@{version}"
            if tool_key not in self._tags_index[tag]:
                self._tags_index[tag].append(tool_key)

        # Initialize execution stats
        if name not in self._execution_stats:
            self._execution_stats[name] = {}
        self._execution_stats[name][version] = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0,
        }

        logger.info(
            f"Registered tool: {name}@{version} "
            f"(category={tool.metadata.category}, max_time={tool.metadata.max_execution_time_ms}ms, tags={tool.metadata.tags})"
        )

    def get(self, name: str, version: str = "latest") -> Tool | None:
        """
        Get tool by name and version.

        Args:
            name: Tool name
            version: Tool version or "latest" for highest semver

        Returns:
            Tool instance or None if not found
        """
        self._metrics["operations_total"] += 1
        self._metrics["get_total"] += 1

        if name not in self._tools:
            return None

        if version == "latest":
            # Get highest semver version
            if not self._version_cache[name]:
                return None
            highest = self._version_cache[name][0]  # Already sorted
            version_str = ".".join(str(p) for p in highest)
            return self._tools[name].get(version_str)

        return self._tools[name].get(version)

    def get_tool(self, name: str, version: str = "latest") -> Tool | None:
        """
        Get tool by name and version (alias for get()).

        Args:
            name: Tool name
            version: Tool version or "latest" for highest semver

        Returns:
            Tool instance or None if not found
        """
        return self.get(name, version)

    def list_tools(self, category: str | None = None) -> list[ToolMetadata]:
        """
        List all registered tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool metadata
        """
        self._metrics["operations_total"] += 1
        self._metrics["list_total"] += 1

        tools = []
        for _name, versions in self._tools.items():
            for _version, tool in versions.items():
                if category is None or tool.metadata.category == category:
                    tools.append(tool.metadata)

        # Sort by category then name
        return sorted(tools, key=lambda m: (m.category, m.name, parse_semver(m.version)))

    def list_tool_names(self) -> list[str]:
        """
        List all tool names (without versions).

        Returns:
            List of unique tool names
        """
        return sorted(self._tools.keys())

    def list_categories(self) -> list[str]:
        """Get list of all tool categories."""
        categories = set()
        for versions in self._tools.values():
            for tool in versions.values():
                categories.add(tool.metadata.category)
        return sorted(categories)

    def list_tags(self) -> list[str]:
        """
        Get list of all tags.

        Returns:
            List of unique tags
        """
        return sorted(self._tags_index.keys())

    def list_tools_by_tag(self, tag: str) -> list[ToolMetadata]:
        """
        List tools with specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of tool metadata
        """
        tool_keys = self._tags_index.get(tag, [])
        result = []
        for tool_key in tool_keys:
            # Parse name@version
            if "@" in tool_key:
                name, version = tool_key.rsplit("@", 1)
                if name in self._tools and version in self._tools[name]:
                    result.append(self._tools[name][version].metadata)
        return result

    def unregister(self, name: str, version: str = "latest") -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name
            version: Tool version or "latest"

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False

        # Resolve "latest" to actual version
        if version == "latest":
            if not self._version_cache[name]:
                return False
            highest = self._version_cache[name][0]
            version = ".".join(str(p) for p in highest)

        if version not in self._tools[name]:
            return False

        # Get tool for tag cleanup
        tool = self._tools[name][version]
        tool_key = f"{name}@{version}"

        # Remove from tags index
        for tag in tool.metadata.tags:
            if tag in self._tags_index:
                self._tags_index[tag] = [key for key in self._tags_index[tag] if key != tool_key]
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

        # Remove tool
        del self._tools[name][version]

        # Remove version from cache
        self._version_cache[name] = [
            v for v in self._version_cache[name] if v != parse_semver(version)
        ]

        # Clean up if no versions left
        if not self._tools[name]:
            del self._tools[name]
            del self._version_cache[name]

        # Keep execution stats for historical purposes

        logger.info("Unregistered tool: %s@%s", name, version)
        return True

    def get_stats(self) -> dict[str, any]:
        """
        Get registry statistics.

        Returns:
            Statistics about registered tools, executions, and performance
        """
        total_tools = sum(len(versions) for versions in self._tools.values())
        categories = self.list_categories()
        tools_by_category = {
            cat: len([m for m in self.list_tools() if m.category == cat]) for cat in categories
        }

        # Calculate execution stats
        total_executions = 0
        total_successes = 0
        total_failures = 0
        for tool_versions in self._execution_stats.values():
            for stats in tool_versions.values():
                total_executions += stats.get("executions", 0)
                total_successes += stats.get("successes", 0)
                total_failures += stats.get("failures", 0)

        return {
            "total_tools": total_tools,
            "unique_tools": len(self._tools),
            "categories": categories,
            "tools_by_category": tools_by_category,
            "total_tags": len(self._tags_index),
            "total_executions": total_executions,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": total_successes / total_executions if total_executions > 0 else 0.0,
            "metrics": self._metrics.copy(),
        }

    def get_tool_stats(self, name: str, version: str = "latest") -> dict[str, any] | None:
        """
        Get statistics for specific tool.

        Args:
            name: Tool name
            version: Tool version or "latest"

        Returns:
            Tool stats or None if not found
        """
        if name not in self._execution_stats:
            return None

        # Resolve "latest" to actual version
        if version == "latest":
            if name not in self._version_cache or not self._version_cache[name]:
                return None
            highest = self._version_cache[name][0]
            version = ".".join(str(p) for p in highest)

        return self._execution_stats[name].get(version)

    def get_metrics(self) -> dict[str, int]:
        """
        Get registry metrics.

        Returns:
            Dictionary with operation counters
        """
        return self._metrics.copy()

    def get_mcp_tool_definitions(self) -> list[dict[str, any]]:
        """
        Get MCP tool definitions for all registered tools.

        Returns latest version of each tool.

        Returns:
            List of MCP Tool definitions
        """
        definitions = []
        for name in self._tools:
            tool = self.get(name, "latest")
            if tool:
                definitions.append(
                    {
                        "name": tool.metadata.name,
                        "description": tool.metadata.description,
                        "inputSchema": tool.metadata.input_schema,
                    }
                )
        return definitions

    def get_openapi_definitions(self) -> dict[str, any]:
        """
        Get OpenAPI definitions for all registered tools.

        Returns latest version of each tool as API endpoints.

        Returns:
            OpenAPI paths object
        """
        paths = {}
        for name in self._tools:
            tool = self.get(name, "latest")
            if tool:
                path = f"/api/tools/{tool.metadata.name}"
                paths[path] = {
                    "post": {
                        "operationId": tool.metadata.name,
                        "summary": tool.metadata.description,
                        "tags": tool.metadata.tags,
                        "requestBody": {
                            "content": {"application/json": {"schema": tool.metadata.input_schema}}
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": tool.metadata.output_schema or {"type": "object"}
                                    }
                                },
                            }
                        },
                    }
                }
        return paths

    def execute(self, tool_name: str, inputs: dict[str, any], version: str = "latest") -> any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            inputs: Input parameters dict
            version: Tool version or "latest"

        Returns:
            Tool execution result (format depends on tool implementation)
        """
        from sibyl.framework.tools import ToolResult

        self._metrics["operations_total"] += 1
        self._metrics["execute_total"] += 1

        # Get tool
        tool = self.get(tool_name, version)
        if not tool:
            # Return error result if using SibylTool-style tools
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}@{version}",
                metadata={"tool_name": tool_name, "version": version},
            )

        # Determine which interface the tool uses
        # Check if it's a SibylTool (has safe_execute)
        if hasattr(tool, "safe_execute"):
            result = tool.safe_execute(**inputs)
        # Check if it's a framework Tool (has execute(ctx, input_data))
        elif hasattr(tool, "execute"):
            # For framework tools, we'd need a ToolContext
            # For now, assume it's SibylTool-compatible
            result = tool.execute(**inputs)
        else:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' has invalid interface",
                metadata={"tool_name": tool_name},
            )

        # Update stats
        actual_version = (
            version if version != "latest" else self._get_actual_version(tool_name, version)
        )
        if (
            actual_version
            and tool_name in self._execution_stats
            and actual_version in self._execution_stats[tool_name]
        ):
            stats = self._execution_stats[tool_name][actual_version]
            stats["executions"] += 1

            # Check if result is a ToolResult
            if isinstance(result, ToolResult):
                if result.success:
                    stats["successes"] += 1
                else:
                    stats["failures"] += 1

                if result.execution_time_ms:
                    stats["total_time_ms"] += result.execution_time_ms
                    stats["avg_time_ms"] = stats["total_time_ms"] / stats["executions"]

        return result

    def _get_actual_version(self, name: str, version: str) -> str | None:
        """Get actual version string from 'latest' or specific version."""
        if version == "latest":
            if name not in self._version_cache or not self._version_cache[name]:
                return None
            highest = self._version_cache[name][0]
            return ".".join(str(p) for p in highest)
        return version

    def batch_execute(self, executions: list[dict[str, any]]) -> list[any]:
        """
        Execute multiple tools in sequence.

        Args:
            executions: List of {"tool": tool_name, "inputs": {...}, "version": "..."} dicts
                       version is optional and defaults to "latest"

        Returns:
            List of results
        """
        results = []
        for execution in executions:
            tool_name = execution["tool"]
            inputs = execution.get("inputs", {})
            version = execution.get("version", "latest")
            result = self.execute(tool_name, inputs, version)
            results.append(result)

        return results

    def generate_catalog(self, output_path: Path) -> None:
        """
        Generate machine-readable catalog.

        Args:
            output_path: Path to write catalog JSON
        """
        catalog = {
            "version": "1.0",
            "generated_at": None,  # Set by caller
            "stats": self.get_stats(),
            "tools": [
                {
                    "name": meta.name,
                    "version": meta.version,
                    "category": meta.category,
                    "description": meta.description,
                    "input_schema": meta.input_schema,
                    "output_schema": meta.output_schema,
                    "max_execution_time_ms": meta.max_execution_time_ms,
                    "examples": meta.examples,
                    "tags": meta.tags,
                }
                for meta in self.list_tools()
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(catalog, indent=2))
        logger.info(
            "Generated tool catalog: %s (%s tools)", output_path, catalog["stats"]["total_tools"]
        )
