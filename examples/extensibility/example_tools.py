"""
Sibyl Framework - Example Tools

These examples demonstrate how to build tools using the Sibyl framework:
1. Create simple tools (SearchModelsTool)
2. Create composable tools (AnalyzeModelTool)
3. Integrate with Sibyl resources (vector index, lineage graph, pattern library)

The examples use ExampleDomain (inventory management) as a concrete use case,
but the patterns apply to any domain.

Usage:
    from sibyl.platform.extensibility.example_tools import create_example_tools
    from sibyl.framework.tools.tool_registry import ToolRegistry

    # Create tools
    tools = create_example_tools(vector_index, lineage_graph, pattern_library)

    # Register tools
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)

    # Execute
    result = registry.execute("search_models", {
        "query": "inventory data",
        "top_k": 10
    })
"""

import logging
from typing import Any

from sibyl.framework.tools import ComposableTool, SibylTool, ToolMetadata, ToolResult

logger = logging.getLogger(__name__)


class SearchModelsTool(SibylTool):
    """
    Search models by semantic similarity using Sibyl's vector index.

    This example tool demonstrates how to wrap Sibyl's semantic search
    capabilities. In the ExampleDomain example, it searches inventory models,
    but the pattern applies to any domain.
    """

    def __init__(self, vector_index: Any) -> None:
        """
        Initialize with vector index.

        Args:
            vector_index: VectorIndex instance
        """
        super().__init__()
        self.vector_index = vector_index

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="search_models",
            description="Search ExampleDomain models by semantic similarity using vector embeddings",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (natural language)"},
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "model_id": {"type": "string"},
                                "score": {"type": "number"},
                                "file_path": {"type": "string"},
                            },
                        },
                    },
                    "query": {"type": "string"},
                    "total_results": {"type": "integer"},
                },
            },
            tags=["search", "vector", "semantic"],
            version="1.0.0",
            author="sibyl",
            examples=[
                {
                    "description": "Search for inventory-related models",
                    "input": {"query": "inventory stock reorder", "top_k": 5},
                    "output": {"results": [...], "query": "...", "total_results": 5},
                }
            ],
        )

    def execute(self, query: str, top_k: int = 10) -> ToolResult:
        """
        Execute semantic search.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            ToolResult with search results
        """
        try:
            # Perform vector search
            results = self.vector_index.search(query, top_k=top_k)

            return ToolResult(
                success=True,
                data={"results": results, "query": query, "total_results": len(results)},
                metadata={"search_type": "vector", "index_type": "faiss"},
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {e!s}")


class GetModelInfoTool(SibylTool):
    """
    Get detailed information about a model using Sibyl's lineage graph.

    This example tool demonstrates how to use Sibyl's lineage tracking.
    In the ExampleDomain example, it retrieves inventory model information,
    but the pattern applies to any domain with dependency tracking.
    """

    def __init__(self, lineage_graph: Any) -> None:
        """
        Initialize with lineage graph.

        Args:
            lineage_graph: LineageGraph instance
        """
        super().__init__()
        self.lineage_graph = lineage_graph

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="get_model_info",
            description="Get detailed information about a specific ExampleDomain model including dependencies",
            input_schema={
                "type": "object",
                "properties": {"model_id": {"type": "string", "description": "Model identifier"}},
                "required": ["model_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "model_id": {"type": "string"},
                    "file_path": {"type": "string"},
                    "depth": {"type": "integer"},
                    "layer": {"type": "string"},
                    "upstream_models": {"type": "array", "items": {"type": "string"}},
                    "downstream_models": {"type": "array", "items": {"type": "string"}},
                    "upstream_count": {"type": "integer"},
                    "downstream_count": {"type": "integer"},
                },
            },
            tags=["model", "lineage", "dependencies"],
            version="1.0.0",
            author="sibyl",
        )

    def execute(self, model_id: str) -> ToolResult:
        """
        Get model information.

        Args:
            model_id: Model identifier

        Returns:
            ToolResult with model info
        """
        try:
            info = self.lineage_graph.get_model_info(model_id)

            if info is None:
                return ToolResult(success=False, error=f"Model not found: {model_id}")

            return ToolResult(success=True, data=info, metadata={"source": "lineage_graph"})

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to get model info: {e!s}")


class FindPatternsTool(SibylTool):
    """
    Find similar patterns for a given error or issue using Sibyl's pattern library.

    This example tool demonstrates how to use Sibyl's pattern learning and
    recognition capabilities to find solutions to common problems.
    """

    def __init__(self, pattern_library: Any) -> None:
        """
        Initialize with pattern library.

        Args:
            pattern_library: PatternLibrary instance
        """
        super().__init__()
        self.pattern_library = pattern_library

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="find_patterns",
            description="Find similar patterns for a given error or issue from pattern library",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Error message or issue description",
                    },
                    "pattern_type": {
                        "type": "string",
                        "description": "Optional pattern type filter (sql_error, schema, logic, performance)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of patterns to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            tags=["patterns", "search", "errors"],
            version="1.0.0",
            author="sibyl",
        )

    def execute(self, query: str, pattern_type: str | None = None, limit: int = 10) -> ToolResult:
        """
        Find similar patterns.

        Args:
            query: Error message or issue
            pattern_type: Optional pattern type filter
            limit: Max results

        Returns:
            ToolResult with matching patterns
        """
        try:
            patterns = self.pattern_library.find_similar_patterns(
                query=query, pattern_type=pattern_type, limit=limit
            )

            return ToolResult(
                success=True,
                data={"patterns": patterns, "query": query, "total_patterns": len(patterns)},
                metadata={"pattern_type": pattern_type, "search_method": "keyword"},
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Pattern search failed: {e!s}")


class AnalyzeModelTool(ComposableTool):
    """
    Comprehensive model analysis combining multiple tools.

    This is an example of a composable tool that uses:
    - get_model_info: Get model metadata
    - search_models: Find similar models
    - find_patterns: Check for known issues

    Demonstrates how to build higher-level tools from existing ones.
    """

    def __init__(
        self,
        get_model_info_tool: GetModelInfoTool,
        search_models_tool: SearchModelsTool,
        find_patterns_tool: FindPatternsTool,
    ) -> None:
        """
        Initialize with child tools.

        Args:
            get_model_info_tool: Tool to get model info
            search_models_tool: Tool to search models
            find_patterns_tool: Tool to find patterns
        """
        super().__init__([get_model_info_tool, search_models_tool, find_patterns_tool])

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        return ToolMetadata(
            name="analyze_model",
            description="Comprehensive model analysis: info, similar models, and potential issues",
            input_schema={
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "Model identifier to analyze"},
                    "include_similar": {
                        "type": "boolean",
                        "description": "Whether to find similar models",
                        "default": True,
                    },
                    "check_patterns": {
                        "type": "boolean",
                        "description": "Whether to check for known issues",
                        "default": True,
                    },
                },
                "required": ["model_id"],
            },
            tags=["analysis", "composite", "model"],
            version="1.0.0",
            author="sibyl",
        )

    def execute(
        self, model_id: str, include_similar: bool = True, check_patterns: bool = True
    ) -> ToolResult:
        """
        Analyze model comprehensively.

        Args:
            model_id: Model to analyze
            include_similar: Find similar models
            check_patterns: Check for known issues

        Returns:
            ToolResult with comprehensive analysis
        """
        analysis = {}

        # Step 1: Get model info
        info_result = self.execute_child("get_model_info", model_id=model_id)
        if not info_result.success:
            return ToolResult(success=False, error=f"Failed to get model info: {info_result.error}")

        analysis["model_info"] = info_result.data

        # Step 2: Find similar models (optional)
        if include_similar:
            # Use model_id as search query
            search_result = self.execute_child(
                "search_models", query=model_id.replace("_", " "), top_k=5
            )
            if search_result.success:
                analysis["similar_models"] = search_result.data["results"]
            else:
                analysis["similar_models_error"] = search_result.error

        # Step 3: Check for known issues (optional)
        if check_patterns:
            # Use model_id as pattern query
            pattern_result = self.execute_child("find_patterns", query=model_id, limit=5)
            if pattern_result.success:
                analysis["relevant_patterns"] = pattern_result.data["patterns"]
            else:
                analysis["patterns_error"] = pattern_result.error

        return ToolResult(
            success=True,
            data=analysis,
            metadata={
                "model_id": model_id,
                "included_similar": include_similar,
                "checked_patterns": check_patterns,
            },
        )


def create_example_tools(
    vector_index: Any = None, lineage_graph: Any = None, pattern_library: Any = None
) -> list[SibylTool]:
    """
    Create all example Sibyl tools.

    This factory function creates a set of example tools that demonstrate
    Sibyl's capabilities. These tools can be used as-is for the ExampleDomain
    example or adapted for other domains.

    Args:
        vector_index: Optional VectorIndex instance for semantic search
        lineage_graph: Optional LineageGraph instance for dependency tracking
        pattern_library: Optional PatternLibrary instance for pattern matching

    Returns:
        List of configured Sibyl tool instances
    """
    tools = []

    if vector_index:
        tools.append(SearchModelsTool(vector_index))

    if lineage_graph:
        tools.append(GetModelInfoTool(lineage_graph))

    if pattern_library:
        tools.append(FindPatternsTool(pattern_library))

    # Create composable tool if all dependencies available
    if vector_index and lineage_graph and pattern_library:
        tools.append(
            AnalyzeModelTool(
                get_model_info_tool=GetModelInfoTool(lineage_graph),
                search_models_tool=SearchModelsTool(vector_index),
                find_patterns_tool=FindPatternsTool(pattern_library),
            )
        )

    return tools
