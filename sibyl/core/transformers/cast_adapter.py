"""cAST adapter for converting ChunkHound chunks to Sibyl RAG chunks.

This module provides utilities to convert ChunkHound's cAST (context-aware AST)
chunks into Sibyl's standard RAG chunk format. This enables using ChunkHound's
superior code chunking quality (+4.3 Recall@5) in Sibyl RAG pipelines.

ChunkHound uses AST-based chunking that preserves semantic boundaries and context,
producing higher quality chunks than traditional fixed-size or sliding window approaches.

Example:
    from sibyl.core.transformers.cast_adapter import cast_chunk_to_sibyl_chunk

    # From ChunkHound semantic_search result
    chunkhound_result = {
        "chunk_id": "chunk_auth_001",
        "file": "/workspace/auth.py",
        "chunk_type": "function",
        "content": "def authenticate_user(username, password):\\n    ...",
        "start_line": 4,
        "end_line": 13,
        "score": 0.92,
        "context": {
            "parent_scope": "module",
            "related_symbols": ["verify_password", "find_user"]
        },
        "metadata": {
            "language": "python",
            "chunk_strategy": "cast"
        }
    }

    # Convert to Sibyl chunk
    sibyl_chunk = cast_chunk_to_sibyl_chunk(chunkhound_result)

    # Use in RAG pipeline
    print(sibyl_chunk.content)
    print(sibyl_chunk.metadata["chunk_type"])  # "function"
    print(sibyl_chunk.metadata["related_symbols"])  # ["verify_password", "find_user"]

Batch conversion example:
    from sibyl.core.transformers.cast_adapter import cast_chunks_to_sibyl_chunks

    # From ChunkHound search results
    search_result = await mcp_adapter(
        provider="chunkhound",
        tool="semantic_search",
        params={"query": "authentication"}
    )

    # Convert all chunks
    sibyl_chunks = cast_chunks_to_sibyl_chunks(search_result["results"])

    # Store in RAG
    for chunk in sibyl_chunks:
        rag_store.add_chunk(chunk)
"""

from dataclasses import dataclass
from typing import Any

# NOTE: We define Chunk locally to avoid circular imports from sibyl.core.protocols package.
# This is a copy of sibyl.core.protocols.rag_pipeline.code_processing.Chunk
# Keep in sync with that definition.


@dataclass
class Chunk:
    """Represents a chunk of code with metadata.

    This is a simple, AST-free representation that works across all code types.
    This matches the definition in sibyl.core.protocols.rag_pipeline.code_processing.

    Attributes:
        chunk_id: Unique identifier for the chunk
        content: Actual content of the chunk
        metadata: Arbitrary metadata (code_type, source, etc.)
        start_line: Optional starting line number
        end_line: Optional ending line number
        description: Optional human-readable description
    """

    chunk_id: str
    content: str
    metadata: dict[str, Any]
    start_line: int | None = None
    end_line: int | None = None
    description: str | None = None


def cast_chunk_to_sibyl_chunk(cast_chunk: dict[str, Any]) -> Chunk:
    """Convert ChunkHound cAST chunk to Sibyl RAG chunk format.

    This function transforms ChunkHound's cAST chunk format into Sibyl's standard
    Chunk dataclass, preserving all semantic information from the AST-based chunking.

    Args:
        cast_chunk: ChunkHound output with fields:
            Required:
                - chunk_id (str): Unique chunk identifier
                - content (str): Actual code content
                - chunk_type (str): One of "function", "class", "method", "module"
            Optional:
                - file (str): Source file path
                - start_line (int): Starting line number
                - end_line (int): Ending line number
                - score (float): Relevance score (0.0-1.0)
                - context (dict): AST context information
                    - parent_scope (str): Parent scope ("module", "class", etc.)
                    - related_symbols (List[str]): Related function/class names
                    - called_by (List[str]): Functions that call this one
                - metadata (dict): Chunk metadata
                    - language (str): Programming language
                    - chunk_strategy (str): Usually "cast"
                    - preserves_structure (bool): Whether AST structure is preserved

    Returns:
        Sibyl Chunk with semantic information preserved in metadata.

    Raises:
        ValueError: If required fields (chunk_id, content, chunk_type) are missing

    Example:
        # Complete cAST chunk with all fields
        cast_chunk = {
            "chunk_id": "chunk_auth_001",
            "file": "/workspace/auth.py",
            "chunk_type": "function",
            "content": "def authenticate_user(username, password):\\n    ...",
            "start_line": 4,
            "end_line": 13,
            "score": 0.92,
            "context": {
                "parent_scope": "module",
                "related_symbols": ["verify_password", "find_user"]
            },
            "metadata": {
                "language": "python",
                "chunk_strategy": "cast",
                "preserves_structure": True
            }
        }

        sibyl_chunk = cast_chunk_to_sibyl_chunk(cast_chunk)

        # Access preserved information
        assert sibyl_chunk.chunk_id == "chunk_auth_001"
        assert sibyl_chunk.start_line == 4
        assert sibyl_chunk.metadata["chunk_type"] == "function"
        assert sibyl_chunk.metadata["language"] == "python"
        assert "verify_password" in sibyl_chunk.metadata["related_symbols"]

    Example with minimal fields:
        # Minimal cAST chunk (only required fields)
        minimal_chunk = {
            "chunk_id": "chunk_001",
            "content": "class User:\\n    pass",
            "chunk_type": "class"
        }

        sibyl_chunk = cast_chunk_to_sibyl_chunk(minimal_chunk)
        assert sibyl_chunk.metadata["chunk_type"] == "class"
        # Optional fields will be None or empty

    Note:
        - All cAST context information is preserved in metadata
        - Relevance score (if present) is stored as metadata["relevance_score"]
        - Source file path is stored as metadata["source_file"]
        - Description is auto-generated from chunk_type and content
    """
    # Validate required fields
    required_fields = ["chunk_id", "content", "chunk_type"]
    missing_fields = [f for f in required_fields if f not in cast_chunk]

    if missing_fields:
        msg = (
            f"cAST chunk missing required fields: {missing_fields}. "
            f"Required fields are: {required_fields}"
        )
        raise ValueError(msg)

    chunk_id = cast_chunk["chunk_id"]
    content = cast_chunk["content"]
    chunk_type = cast_chunk["chunk_type"]

    # Extract optional fields
    source_file = cast_chunk.get("file")
    start_line = cast_chunk.get("start_line")
    end_line = cast_chunk.get("end_line")
    score = cast_chunk.get("score")
    context = cast_chunk.get("context", {})
    cast_metadata = cast_chunk.get("metadata", {})

    # Build Sibyl metadata by merging context and metadata
    sibyl_metadata = {
        "chunk_type": chunk_type,
    }

    # Add optional fields to metadata
    if source_file is not None:
        sibyl_metadata["source_file"] = source_file

    if score is not None:
        sibyl_metadata["relevance_score"] = score

    # Add context fields
    if context:
        if "parent_scope" in context:
            sibyl_metadata["parent_scope"] = context["parent_scope"]

        if "related_symbols" in context:
            sibyl_metadata["related_symbols"] = context["related_symbols"]

        if "called_by" in context:
            sibyl_metadata["called_by"] = context["called_by"]

        # Add any other context fields not explicitly handled
        for key, value in context.items():
            if key not in ["parent_scope", "related_symbols", "called_by"]:
                sibyl_metadata[f"context_{key}"] = value

    # Add cAST metadata fields
    if cast_metadata:
        if "language" in cast_metadata:
            sibyl_metadata["language"] = cast_metadata["language"]

        if "chunk_strategy" in cast_metadata:
            sibyl_metadata["chunk_strategy"] = cast_metadata["chunk_strategy"]

        if "preserves_structure" in cast_metadata:
            sibyl_metadata["preserves_structure"] = cast_metadata["preserves_structure"]

        # Add any other metadata fields not explicitly handled
        for key, value in cast_metadata.items():
            if key not in ["language", "chunk_strategy", "preserves_structure"]:
                sibyl_metadata[f"cast_{key}"] = value

    # Generate description
    description = _generate_chunk_description(chunk_type, content, context)

    # Create Sibyl Chunk
    return Chunk(
        chunk_id=chunk_id,
        content=content,
        metadata=sibyl_metadata,
        start_line=start_line,
        end_line=end_line,
        description=description,
    )


def cast_chunks_to_sibyl_chunks(cast_chunks: list[dict[str, Any]]) -> list[Chunk]:
    """Convert list of ChunkHound cAST chunks to Sibyl chunks.

    Batch conversion utility for processing multiple chunks from ChunkHound
    search results or indexing operations.

    Args:
        cast_chunks: List of ChunkHound cAST chunks (each a dict)

    Returns:
        List of Sibyl Chunks

    Raises:
        ValueError: If any chunk is missing required fields (propagated from cast_chunk_to_sibyl_chunk)

    Example:
        # From ChunkHound semantic_search results
        search_result = await mcp_adapter(
            provider="chunkhound",
            tool="semantic_search",
            params={
                "query": "authentication logic",
                "top_k": 20,
                "include_context": True
            }
        )

        # Convert all results
        sibyl_chunks = cast_chunks_to_sibyl_chunks(search_result["results"])

        # Process chunks
        print(f"Converted {len(sibyl_chunks)} chunks")
        for chunk in sibyl_chunks:
            print(f"  {chunk.chunk_id}: {chunk.metadata['chunk_type']}")

    Example with error handling:
        try:
            sibyl_chunks = cast_chunks_to_sibyl_chunks(cast_results)
        except ValueError as e:
            print(f"Invalid chunk format: {e}")
            # Handle error - maybe skip invalid chunks

    Note:
        - Conversion is performed sequentially
        - If any chunk fails validation, the entire operation fails
        - For partial conversion (skipping invalid chunks), wrap individual calls
    """
    return [cast_chunk_to_sibyl_chunk(chunk) for chunk in cast_chunks]


def _generate_chunk_description(
    chunk_type: str, content: str, context: dict[str, Any] | None = None
) -> str:
    """Generate human-readable description for chunk.

    This internal helper generates a description based on chunk type and content.
    Used when converting cAST chunks that don't have explicit descriptions.

    Args:
        chunk_type: Type of chunk ("function", "class", "method", "module")
        content: Chunk content (code)
        context: Optional context dict with related_symbols, parent_scope, etc.

    Returns:
        Human-readable description string

    Example outputs:
        - "Function: authenticate_user"
        - "Class: UserAuthentication"
        - "Method: verify_password (in class User)"
        - "Module-level code"

    Note:
        This is a best-effort description generator. It extracts the name from
        the first line of content using simple heuristics.
    """
    if not content or not content.strip():
        return f"{chunk_type.capitalize()} chunk"

    # Extract first non-empty line
    first_line = ""
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_line = stripped
            break

    if not first_line:
        return f"{chunk_type.capitalize()} chunk"

    # Try to extract name from first line
    # Common patterns: "def name(...)", "class Name:", "async def name(...)"
    name = None

    # Remove common keywords
    for keyword in [
        "def ",
        "async def ",
        "class ",
        "async ",
        "function ",
        "const ",
        "let ",
        "var ",
    ]:
        if first_line.startswith(keyword):
            rest = first_line[len(keyword) :].strip()
            # Extract name (up to first ( or : or space)
            for delimiter in ["(", ":", " ", "="]:
                if delimiter in rest:
                    name = rest.split(delimiter)[0].strip()
                    break
            if name:
                break

    if not name:
        # Fallback: use first word
        name = first_line.split()[0] if first_line.split() else "unnamed"

    # Build description
    description = f"{chunk_type.capitalize()}: {name}"

    # Add context if available
    if context:
        parent_scope = context.get("parent_scope")
        if parent_scope and parent_scope != "module":
            description += f" (in {parent_scope})"

    return description


__all__ = [
    "cast_chunk_to_sibyl_chunk",
    "cast_chunks_to_sibyl_chunks",
]
