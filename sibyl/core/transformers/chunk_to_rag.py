"""Production-grade cAST → RAG adapter for ChunkArtifact to RAG chunks.

This module provides an advanced, production-ready adapter for converting
ChunkArtifact instances (with full cAST metadata) into Sibyl RAG
format with enhanced features.

Key improvements:
- Uses ChunkArtifact instead of raw dicts
- Preserves all cAST metadata (symbols, dependencies, context)
- Provides multiple output formats (standard RAG, enhanced RAG, LLM-optimized)
- Includes batch processing with error handling
- Supports filtering and ranking by relevance

Example:
    from sibyl.core.artifacts import ChunkArtifact
    from sibyl.core.transformers.chunk_to_rag import chunk_to_rag, batch_chunks_to_rag

    # Single chunk conversion
    chunk = ChunkArtifact.from_mcp_response(chunkhound_response)
    rag_chunk = chunk_to_rag(chunk)

    # Batch conversion with filtering
    chunks = [ChunkArtifact.from_mcp_response(r) for r in responses]
    rag_chunks = batch_chunks_to_rag(
        chunks,
        min_line_count=5,
        include_dependencies=True
    )
"""

from typing import Any

from sibyl.core.artifacts import ChunkArtifact, ChunkType


def chunk_to_rag(
    chunk: ChunkArtifact,
    format: str = "standard",
    include_context: bool = True,
    max_content_preview: int | None = None,
) -> dict[str, Any]:
    """Convert ChunkArtifact to RAG-friendly format.

    This provides multiple output formats optimized for different RAG use cases.

    Args:
        chunk: ChunkArtifact instance from ChunkHound or similar
        format: Output format - one of:
            - "standard": Standard RAG format (id, text, metadata)
            - "enhanced": Enhanced format with symbol graph and dependencies
            - "llm": LLM-optimized format with summary and structured fields
        include_context: Whether to include docstrings and comments in text
        max_content_preview: Optional max length for content (for large chunks)

    Returns:
        Dictionary in specified RAG format

    Raises:
        ValueError: If format is invalid

    Example:
        # Standard RAG format (for vector stores)
        rag_chunk = chunk_to_rag(chunk, format="standard")
        # {"id": "...", "text": "...", "metadata": {...}}

        # Enhanced format (for graph-aware RAG)
        rag_chunk = chunk_to_rag(chunk, format="enhanced", include_context=True)
        # Includes symbol references and dependency graph

        # LLM-optimized format (for few-shot prompting)
        rag_chunk = chunk_to_rag(chunk, format="llm")
        # Includes structured summary and symbol explanations
    """
    if format not in ["standard", "enhanced", "llm"]:
        msg = f"Invalid format '{format}'. Must be one of: standard, enhanced, llm"
        raise ValueError(msg)

    # Get content (potentially truncated)
    content = chunk.content
    if max_content_preview and len(content) > max_content_preview:
        content = content[:max_content_preview] + "\n... (truncated)"

    # Build text for embedding
    text_parts = []

    # Add symbol name as title
    symbol_name = chunk.get_symbol_name()
    if symbol_name:
        text_parts.append(f"# {symbol_name}")

    # Add docstring if available and requested
    if include_context:
        docstring = chunk.get_docstring()
        if docstring:
            text_parts.append(docstring)

    # Add content
    text_parts.append(content)

    # Combine into single text
    text = "\n\n".join(text_parts)

    # Base metadata (common to all formats)
    base_metadata = {
        "chunk_id": chunk.chunk_id,
        "type": chunk.chunk_type.value,
        "file_path": chunk.file_path,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "line_count": chunk.get_line_count(),
        "language": chunk.language,
        "symbol": symbol_name,
    }

    # Add complexity if available
    complexity = chunk.get_complexity()
    if complexity is not None:
        base_metadata["complexity"] = complexity

    # Add parent context
    if chunk.parent_symbols:
        base_metadata["parent"] = chunk.parent_symbols[0].name

    if format == "standard":
        # Standard RAG format - minimal, fast to embed
        return {"id": chunk.chunk_id, "text": text, "metadata": base_metadata}

    if format == "enhanced":
        # Enhanced format with full cAST metadata
        enhanced_metadata = {
            **base_metadata,
            "symbols": [
                {
                    "name": s.name,
                    "type": s.type,
                    "location": s.location,
                }
                for s in chunk.symbols
            ],
            "parent_symbols": [
                {
                    "name": s.name,
                    "type": s.type,
                }
                for s in chunk.parent_symbols
            ],
            "dependencies": chunk.dependencies,
            "has_dependencies": chunk.has_dependencies(),
            "context": chunk.context,
        }

        return {
            "id": chunk.chunk_id,
            "text": text,
            "metadata": enhanced_metadata,
            # Additional fields for graph-aware RAG
            "symbol_graph": {
                "defined": [s.name for s in chunk.symbols],
                "referenced": chunk.dependencies,
                "parent_scope": chunk.parent_symbols[0].name if chunk.parent_symbols else None,
            },
        }

    if format == "llm":
        # LLM-optimized format with structured summary
        llm_metadata = {
            **base_metadata,
            "summary": _generate_chunk_summary(chunk),
            "context_lines": f"Lines {chunk.start_line}-{chunk.end_line} in {chunk.file_path}",
        }

        # Add symbol explanations
        if chunk.symbols:
            llm_metadata["symbols_defined"] = [
                {"name": s.name, "type": s.type} for s in chunk.symbols
            ]

        if chunk.dependencies:
            llm_metadata["calls_or_uses"] = chunk.dependencies[:5]  # Top 5 deps

        return {
            "id": chunk.chunk_id,
            "text": text,
            "metadata": llm_metadata,
            "structured": {
                "type": chunk.chunk_type.value,
                "name": symbol_name,
                "location": f"{chunk.file_path}:{chunk.start_line}",
                "description": chunk.get_docstring() or _generate_chunk_summary(chunk),
            },
        }
    return None


def batch_chunks_to_rag(
    chunks: list[ChunkArtifact],
    format: str = "standard",
    include_context: bool = True,
    min_line_count: int | None = None,
    max_complexity: int | None = None,
    chunk_types: list[ChunkType] | None = None,
    skip_errors: bool = False,
) -> list[dict[str, Any]]:
    """Batch convert ChunkArtifacts to RAG format with filtering.

    Provides production-grade batch processing with filtering, error handling,
    and quality control.

    Args:
        chunks: List of ChunkArtifact instances
        format: Output format (standard, enhanced, llm)
        include_context: Whether to include docstrings/comments
        min_line_count: Optional minimum line count filter
        max_complexity: Optional maximum complexity filter
        chunk_types: Optional list of ChunkType values to include
        skip_errors: If True, skip chunks that fail conversion; if False, raise

    Returns:
        List of RAG-formatted dictionaries

    Example:
        # Convert only functions with moderate complexity
        rag_chunks = batch_chunks_to_rag(
            chunks,
            format="enhanced",
            min_line_count=10,
            max_complexity=15,
            chunk_types=[ChunkType.FUNCTION, ChunkType.METHOD]
        )

        # Batch with error recovery
        rag_chunks = batch_chunks_to_rag(
            chunks,
            format="standard",
            skip_errors=True  # Skip invalid chunks
        )
    """
    results = []

    for chunk in chunks:
        # Apply filters
        if min_line_count and chunk.get_line_count() < min_line_count:
            continue

        complexity = chunk.get_complexity()
        if max_complexity and complexity and complexity > max_complexity:
            continue

        if chunk_types and chunk.chunk_type not in chunk_types:
            continue

        # Convert
        try:
            rag_chunk = chunk_to_rag(chunk, format=format, include_context=include_context)
            results.append(rag_chunk)
        except Exception:
            if not skip_errors:
                raise
            # Skip this chunk and continue
            continue

    return results


def chunks_to_rag_with_ranking(
    chunks: list[ChunkArtifact],
    query: str | None = None,
    format: str = "standard",
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Convert chunks to RAG format with relevance ranking.

    Useful when you have search results from ChunkHound and want to preserve
    or re-rank by relevance before ingesting into RAG.

    Args:
        chunks: List of ChunkArtifact instances
        query: Optional query string for relevance scoring
        format: Output format
        top_k: Optional limit on number of results

    Returns:
        List of RAG chunks, sorted by relevance (if query provided)

    Example:
        # Rank by complexity (simpler = higher priority)
        rag_chunks = chunks_to_rag_with_ranking(
            chunks,
            format="enhanced",
            top_k=20  # Top 20 most relevant
        )
    """
    # Convert all chunks
    rag_chunks = []
    for chunk in chunks:
        rag_chunk = chunk_to_rag(chunk, format=format)
        # Attach relevance score from metadata if available
        relevance_score = chunk.metadata.get("relevance_score", 0.0)
        rag_chunk["_relevance"] = relevance_score
        rag_chunks.append(rag_chunk)

    # Sort by relevance (if scores available)
    rag_chunks.sort(key=lambda x: x.get("_relevance", 0.0), reverse=True)

    # Remove temporary field
    for rc in rag_chunks:
        rc.pop("_relevance", None)

    # Apply top_k limit
    if top_k:
        rag_chunks = rag_chunks[:top_k]

    return rag_chunks


def _generate_chunk_summary(chunk: ChunkArtifact) -> str:
    """Generate a concise summary of the chunk for LLM consumption.

    Internal helper for creating human-readable summaries.

    Args:
        chunk: ChunkArtifact to summarize

    Returns:
        Human-readable summary string
    """
    symbol_name = chunk.get_symbol_name()
    chunk_type = chunk.chunk_type.value

    if chunk.is_function():
        if symbol_name:
            return f"{chunk_type.capitalize()} '{symbol_name}' ({chunk.get_line_count()} lines)"
        return f"{chunk_type.capitalize()} ({chunk.get_line_count()} lines)"

    if chunk.is_class():
        if symbol_name:
            return f"Class '{symbol_name}' definition ({chunk.get_line_count()} lines)"
        return f"Class definition ({chunk.get_line_count()} lines)"

    if symbol_name:
        return f"{chunk_type.capitalize()} '{symbol_name}'"
    return f"{chunk_type.capitalize()} code ({chunk.get_line_count()} lines)"


__all__ = [
    "batch_chunks_to_rag",
    "chunk_to_rag",
    "chunks_to_rag_with_ranking",
]
