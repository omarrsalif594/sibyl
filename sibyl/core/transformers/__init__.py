"""Cross-MCP transformation utilities.

This package provides pure transformation utilities for cross-MCP workflows:

Baseline:
1. Graph Transformers - Convert between Graphiti and NetworkX formats
2. cAST Adapter (Baseline) - Convert ChunkHound cAST chunks to Sibyl RAG chunks

Advanced:
3. Chunk → RAG Adapter (Production) - Production-grade ChunkArtifact to RAG
4. AST Normalizer - Normalize AST Server and OXC Parser outputs
5. Metric Annotators - Enrich GraphArtifact with GraphMetricsArtifact data

Design Principles:
- Small and Pure: No hidden I/O, just input → output transformations
- Obvious Mappings: Transformation logic is clear from code
- No Surprises: Predictable behavior, no magic conventions
- Well Documented: Each transformer has clear examples

Example: Production RAG Adapter
    from sibyl.core.artifacts import ChunkArtifact
    from sibyl.core.transformers import chunk_to_rag, batch_chunks_to_rag

    # From ChunkHound
    chunk = ChunkArtifact.from_mcp_response(chunkhound_result)

    # Production conversion with enhanced metadata
    rag_chunk = chunk_to_rag(chunk, format="enhanced")

    # Batch with filtering
    rag_chunks = batch_chunks_to_rag(
        chunks,
        min_line_count=10,
        chunk_types=[ChunkType.FUNCTION, ChunkType.METHOD]
    )

Example: AST Normalization
    from sibyl.core.transformers import (
        normalize_ast_server_response,
        normalize_oxc_parser_response,
        compare_asts
    )

    # Normalize Python AST
    py_ast = normalize_ast_server_response(ast_server_result, "example.py")

    # Normalize JavaScript AST
    js_ast = normalize_oxc_parser_response(oxc_result, "example.js")

    # Use unified API
    py_functions = py_ast.query("FunctionDef")
    js_functions = js_ast.query("FunctionDef")

    # Compare for similarity
    comparison = compare_asts(py_ast, js_ast)

Example: Metric Annotators
    from sibyl.core.transformers import (
        annotate_graph_with_metric_artifact,
        annotate_with_communities
    )

    # Compute metrics
    metrics = GraphMetricsArtifact.from_networkx_result(
        scores=nx.pagerank(nx_graph),
        algorithm="pagerank"
    )

    # Annotate graph
    annotated = annotate_graph_with_metric_artifact(graph, metrics)

Example: Graph Transformation
    from sibyl.core.artifacts import GraphArtifact
    from sibyl.core.transformers import annotate_graph_with_metrics, extract_top_nodes
    import networkx as nx

    # Convert Graphiti → GraphArtifact → NetworkX
    graph = GraphArtifact.from_graphiti_search(nodes, facts)
    nx_graph = graph.to_networkx()

    # Analyze with NetworkX
    pagerank = nx.pagerank(nx_graph)

    # Add metrics back to graph
    annotated = annotate_graph_with_metrics(graph, {"pagerank": pagerank})

    # Extract top nodes
    top_nodes = extract_top_nodes(annotated, "pagerank", top_k=5)

Example: Baseline cAST Conversion
    from sibyl.core.transformers import cast_chunk_to_sibyl_chunk

    # ChunkHound search result (baseline - uses raw dicts)
    cast_chunk = {
        "chunk_id": "chunk_001",
        "content": "def authenticate(...):\\n    ...",
        "chunk_type": "function",
        "context": {"related_symbols": ["verify_password"]}
    }

    # Convert to Sibyl RAG chunk
    sibyl_chunk = cast_chunk_to_sibyl_chunk(cast_chunk)

    # Use in RAG pipeline
    rag_store.add_chunk(sibyl_chunk)
"""

# Baseline transformers
from sibyl.core.transformers.ast_normalizer import (
    compare_asts,
    merge_asts,
    normalize_ast_server_response,
    normalize_oxc_parser_response,
)
from sibyl.core.transformers.cast_adapter import (
    cast_chunk_to_sibyl_chunk,
    cast_chunks_to_sibyl_chunks,
)

# Advanced transformers
from sibyl.core.transformers.chunk_to_rag import (
    batch_chunks_to_rag,
    chunk_to_rag,
    chunks_to_rag_with_ranking,
)

# Cross-MCP wiring helpers
from sibyl.core.transformers.cross_mcp import (
    chunkhound_to_rag_chunks,
    graphiti_to_networkx,
    networkx_metrics_to_annotations,
    pattern_to_recommendations,
    timeseries_to_forecast_summary,
)
from sibyl.core.transformers.graph import (
    annotate_graph_with_metrics,
    extract_top_nodes,
    merge_graph_artifacts,
)
from sibyl.core.transformers.metric_annotator import (
    annotate_graph_with_metric_artifact,
    annotate_with_communities,
    annotate_with_multiple_metrics,
    extract_metric_summary,
    filter_graph_by_metric,
    rank_nodes_by_metric,
)

__all__ = [
    # Advanced - Metric annotators
    "annotate_graph_with_metric_artifact",
    # Baseline - Graph transformers
    "annotate_graph_with_metrics",
    "annotate_with_communities",
    "annotate_with_multiple_metrics",
    "batch_chunks_to_rag",
    # Baseline - cAST adapter
    "cast_chunk_to_sibyl_chunk",
    "cast_chunks_to_sibyl_chunks",
    # Advanced - Chunk → RAG (production-grade)
    "chunk_to_rag",
    "chunkhound_to_rag_chunks",
    "chunks_to_rag_with_ranking",
    "compare_asts",
    "extract_metric_summary",
    "extract_top_nodes",
    "filter_graph_by_metric",
    # Cross-MCP wiring helpers
    "graphiti_to_networkx",
    "merge_asts",
    "merge_graph_artifacts",
    "networkx_metrics_to_annotations",
    # Advanced - AST normalizer
    "normalize_ast_server_response",
    "normalize_oxc_parser_response",
    "pattern_to_recommendations",
    "rank_nodes_by_metric",
    "timeseries_to_forecast_summary",
]
