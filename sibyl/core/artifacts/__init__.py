"""Typed artifact classes for complex MCP outputs.

This package provides typed artifact classes that replace generic dict outputs
from MCP tools with type-safe structures and domain-specific methods.

Artifacts:
    Core:
    - SolverResultArtifact: For constraint solver results (MCP Solver, Z3, PySAT)
    - GraphArtifact: For graph structures (Graphiti, NetworkX)
    - ASTArtifact: For abstract syntax trees (AST Server, OXC Parser, ast-grep)
    - PollableJobHandle: For long-running jobs with automatic polling (Conductor, Chronulus, etc.)

    Advanced:
    - PatternArtifact: For learned code patterns (In-Memoria)
    - GraphMetricsArtifact: For graph analysis metrics (NetworkX PageRank, centrality, communities)
    - TimeSeriesArtifact: For forecasts and temporal data (Chronulus)
    - ChunkArtifact: For cAST-aware code chunks (ChunkHound)

Example:
    from sibyl.core.artifacts import SolverResultArtifact, GraphArtifact, ASTArtifact

    # Solver results
    solver_result = SolverResultArtifact.from_mcp_response(response, backend="MiniZinc")
    if solver_result.is_feasible():
        print(solver_result.solution)

    # Graph structures
    graph = GraphArtifact.from_graphiti_search(nodes, facts)
    nx_graph = graph.to_networkx()

    # Abstract syntax trees
    ast = ASTArtifact.from_mcp_response(response, language="python")
    functions = ast.query("FunctionDef")

    # Long-running jobs
    handle = PollableJobHandle.from_mcp_response(response, provider="conductor", status_tool="get_status")
    result = await handle.await_completion(mcp_adapter)
"""

# Core artifacts
from sibyl.core.artifacts.ast import ASTArtifact, ASTNode, Location
from sibyl.core.artifacts.chunk import (
    ChunkArtifact,
    ChunkType,
    SymbolReference,
)
from sibyl.core.artifacts.external_handle import (
    ExternalHandle,
    ExternalResourceError,
    ResourceAlreadyDeletedError,
    ResourceNotFoundError,
    ResourceType,
)
from sibyl.core.artifacts.graph import Edge, GraphArtifact, GraphType, Node
from sibyl.core.artifacts.graph_metrics import (
    Community,
    GraphMetricsArtifact,
    MetricType,
    RankedNode,
)
from sibyl.core.artifacts.job_handle import (
    JobCancelledError,
    JobError,
    JobFailedError,
    JobStatus,
    JobTimeoutError,
    PollableJobHandle,
)

# Advanced artifacts
from sibyl.core.artifacts.pattern import PatternArtifact, PatternCategory

# Artifact registry
from sibyl.core.artifacts.registry import (
    ArtifactMapping,
    ArtifactRegistry,
    convert_mcp_response,
    get_registry,
)
from sibyl.core.artifacts.session_handle import (
    Checkpoint,
    CheckpointNotFoundError,
    SessionError,
    SessionHandle,
    SessionNotFoundError,
    SessionStateError,
    SessionStatus,
)
from sibyl.core.artifacts.solver import SolverResultArtifact, SolverStatus
from sibyl.core.artifacts.timeseries import (
    TimePoint,
    TimeSeriesArtifact,
    TimeSeriesFrequency,
)

__all__ = [
    # AST artifacts
    "ASTArtifact",
    "ASTNode",
    "ArtifactMapping",
    # Artifact registry
    "ArtifactRegistry",
    "Checkpoint",
    "CheckpointNotFoundError",
    # Chunk artifacts (ChunkHound)
    "ChunkArtifact",
    "ChunkType",
    "Community",
    "Edge",
    # External handle artifacts
    "ExternalHandle",
    "ExternalResourceError",
    # Graph artifacts
    "GraphArtifact",
    # Graph metrics artifacts (NetworkX)
    "GraphMetricsArtifact",
    "GraphType",
    "JobCancelledError",
    "JobError",
    "JobFailedError",
    "JobStatus",
    "JobTimeoutError",
    "Location",
    "MetricType",
    "Node",
    # Advanced artifacts
    # Pattern artifacts (In-Memoria)
    "PatternArtifact",
    "PatternCategory",
    # Job handle artifacts
    "PollableJobHandle",
    "RankedNode",
    "ResourceAlreadyDeletedError",
    "ResourceNotFoundError",
    "ResourceType",
    "SessionError",
    # Session handle artifacts
    "SessionHandle",
    "SessionNotFoundError",
    "SessionStateError",
    "SessionStatus",
    # Core artifacts
    # Solver artifacts
    "SolverResultArtifact",
    "SolverStatus",
    "SymbolReference",
    "TimePoint",
    # Time series artifacts (Chronulus)
    "TimeSeriesArtifact",
    "TimeSeriesFrequency",
    "convert_mcp_response",
    "get_registry",
]
