"""Chunk Artifact for cAST-aware code chunks from ChunkHound.

This module provides typed artifacts for code chunks with enhanced cAST metadata,
symbol information, and semantic context. It enables integration with Sibyl RAG
and leverages ChunkHound's 4.3 point Recall@5 improvement.

Example:
    from sibyl.core.artifacts.chunk import ChunkArtifact, ChunkType

    # Create from ChunkHound response
    chunk = ChunkArtifact.from_mcp_response(
        response={"chunk_id": "func_123", "content": "def foo():", ...},
        provider="chunkhound"
    )

    # Check chunk properties
    if chunk.chunk_type == ChunkType.FUNCTION:
        print(f"Function: {chunk.get_symbol_name()}")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChunkType(Enum):
    """Types of code chunks."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    BLOCK = "block"
    STATEMENT = "statement"
    IMPORT = "import"
    COMMENT = "comment"
    DOCSTRING = "docstring"
    OTHER = "other"


@dataclass
class SymbolReference:
    """A reference to a symbol (function, class, variable, etc.).

    Attributes:
        name: Symbol name
        type: Symbol type (e.g., "function", "class", "variable")
        location: Optional location information (file, line, column)
        properties: Additional properties (scope, modifiers, etc.)

    Example:
        ref = SymbolReference(
            name="calculate_total",
            type="function",
            location="src/utils.py:42",
            properties={"scope": "module", "async": False}
        )
    """

    name: str
    type: str
    location: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkArtifact:
    """Artifact for cAST-aware code chunks.

    This artifact represents a code chunk with enhanced metadata from ChunkHound
    or similar cAST-aware chunking tools. It includes symbol information, semantic
    context, and helpers for RAG integration.

    Attributes:
        chunk_id: Unique chunk identifier
        chunk_type: Type of chunk (function, class, method, etc.)
        content: Code content
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        start_column: Optional starting column (0-indexed)
        end_column: Optional ending column (0-indexed)
        file_path: Source file path
        language: Programming language
        symbols: List of symbols defined or referenced in this chunk
        parent_symbols: List of parent symbols (containing class, module, etc.)
        dependencies: List of chunks this chunk depends on
        context: Semantic context (docstrings, comments, surrounding code)
        metadata: Additional metadata (complexity metrics, etc.)

    Example:
        chunk = ChunkArtifact(
            chunk_id="func_calculate_total",
            chunk_type=ChunkType.FUNCTION,
            content="def calculate_total(items):\\n    return sum(items)",
            start_line=42,
            end_line=43,
            file_path="src/utils.py",
            language="python",
            symbols=[
                SymbolReference("calculate_total", "function"),
                SymbolReference("sum", "builtin_function")
            ],
            context={"docstring": "Calculate total of items"}
        )

        # Check if it's a function
        if chunk.is_function():
            print(f"Function: {chunk.get_symbol_name()}")
    """

    chunk_id: str
    chunk_type: ChunkType
    content: str
    start_line: int
    end_line: int
    file_path: str
    language: str
    start_column: int | None = None
    end_column: int | None = None
    symbols: list[SymbolReference] = field(default_factory=list)
    parent_symbols: list[SymbolReference] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_function(self) -> bool:
        """Check if chunk is a function or method.

        Returns:
            True if chunk_type is FUNCTION or METHOD

        Example:
            if chunk.is_function():
                complexity = chunk.get_complexity()
        """
        return self.chunk_type in {ChunkType.FUNCTION, ChunkType.METHOD}

    def is_class(self) -> bool:
        """Check if chunk is a class definition.

        Returns:
            True if chunk_type is CLASS

        Example:
            if chunk.is_class():
                methods = chunk.get_methods()
        """
        return self.chunk_type == ChunkType.CLASS

    def get_symbol_name(self) -> str | None:
        """Get primary symbol name for this chunk.

        Returns the name of the main symbol defined in this chunk
        (e.g., function name, class name).

        Returns:
            Primary symbol name or None

        Example:
            name = chunk.get_symbol_name()
            print(f"Chunk defines: {name}")
        """
        if self.symbols:
            # First symbol is typically the primary definition
            return self.symbols[0].name
        return None

    def get_line_count(self) -> int:
        """Get number of lines in this chunk.

        Returns:
            Number of lines (inclusive)

        Example:
            if chunk.get_line_count() > 50:
                print("Large chunk - consider refactoring")
        """
        return self.end_line - self.start_line + 1

    def get_complexity(self) -> int | None:
        """Get cyclomatic complexity if available.

        Returns:
            Complexity score or None

        Example:
            complexity = chunk.get_complexity()
            if complexity and complexity > 10:
                print("High complexity")
        """
        return self.metadata.get("complexity", self.metadata.get("cyclomatic_complexity"))

    def get_docstring(self) -> str | None:
        """Get docstring/documentation for this chunk.

        Returns:
            Docstring text or None

        Example:
            doc = chunk.get_docstring()
            if doc:
                print(f"Documentation: {doc}")
        """
        return self.context.get("docstring", self.context.get("documentation"))

    def has_dependencies(self) -> bool:
        """Check if chunk has dependencies on other chunks.

        Returns:
            True if dependencies list is non-empty

        Example:
            if chunk.has_dependencies():
                print(f"Depends on: {chunk.dependencies}")
        """
        return len(self.dependencies) > 0

    def summarize_for_llm(self, max_content_length: int = 200, include_context: bool = True) -> str:
        """Generate LLM-friendly summary of the chunk.

        Creates a concise text summary suitable for inclusion in LLM prompts,
        including chunk metadata, symbols, and optionally the content.

        Args:
            max_content_length: Maximum content length to include
            include_context: Whether to include context (docstring, etc.)

        Returns:
            Formatted string summary

        Example:
            summary = chunk.summarize_for_llm(max_content_length=100)
            llm_prompt = f"Analyze this code:\\n{summary}\\nSuggest improvements..."
        """
        lines = [
            f"Chunk: {self.chunk_id}",
            f"Type: {self.chunk_type.value}",
            f"File: {self.file_path}",
            f"Lines: {self.start_line}-{self.end_line} ({self.get_line_count()} lines)",
            f"Language: {self.language}",
        ]

        # Add primary symbol
        symbol_name = self.get_symbol_name()
        if symbol_name:
            lines.append(f"Symbol: {symbol_name}")

        # Add parent context
        if self.parent_symbols:
            parent_names = ", ".join(s.name for s in self.parent_symbols)
            lines.append(f"Parent: {parent_names}")

        # Add complexity
        complexity = self.get_complexity()
        if complexity is not None:
            lines.append(f"Complexity: {complexity}")

        # Add docstring
        if include_context:
            docstring = self.get_docstring()
            if docstring:
                # Truncate long docstrings
                doc_summary = docstring[:100] + "..." if len(docstring) > 100 else docstring
                lines.append(f"Documentation: {doc_summary}")

        # Add dependencies
        if self.dependencies:
            deps_str = ", ".join(self.dependencies[:3])
            if len(self.dependencies) > 3:
                deps_str += f" (+{len(self.dependencies) - 3} more)"
            lines.append(f"Dependencies: {deps_str}")

        # Add content preview
        content_preview = self.content
        if len(content_preview) > max_content_length:
            content_preview = content_preview[:max_content_length] + "..."
        lines.append(f"\nContent Preview:\n{content_preview}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary.

        Returns:
            Dictionary representation of the artifact

        Example:
            data = chunk.to_dict()
            json.dumps(data)
        """
        return {
            "chunk_id": self.chunk_id,
            "chunk_type": self.chunk_type.value,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_column": self.start_column,
            "end_column": self.end_column,
            "file_path": self.file_path,
            "language": self.language,
            "symbols": [
                {
                    "name": s.name,
                    "type": s.type,
                    "location": s.location,
                    "properties": s.properties,
                }
                for s in self.symbols
            ],
            "parent_symbols": [
                {
                    "name": s.name,
                    "type": s.type,
                    "location": s.location,
                    "properties": s.properties,
                }
                for s in self.parent_symbols
            ],
            "dependencies": self.dependencies,
            "context": self.context,
            "metadata": self.metadata,
        }

    def to_rag_chunk(self) -> dict[str, Any]:
        """Convert to RAG-friendly format.

        Creates a dictionary suitable for ingestion into RAG systems,
        with content, metadata, and semantic information.

        Returns:
            RAG-compatible dictionary

        Example:
            rag_chunk = chunk.to_rag_chunk()
            rag_system.ingest(rag_chunk)
        """
        # Primary text for embedding
        text_parts = []

        # Add symbol name as title
        symbol_name = self.get_symbol_name()
        if symbol_name:
            text_parts.append(f"# {symbol_name}")

        # Add docstring if available
        docstring = self.get_docstring()
        if docstring:
            text_parts.append(docstring)

        # Add content
        text_parts.append(self.content)

        # Combine into single text
        text = "\n\n".join(text_parts)

        return {
            "id": self.chunk_id,
            "text": text,
            "metadata": {
                "type": self.chunk_type.value,
                "file_path": self.file_path,
                "start_line": self.start_line,
                "end_line": self.end_line,
                "language": self.language,
                "symbol": symbol_name,
                "line_count": self.get_line_count(),
                "complexity": self.get_complexity(),
                "has_dependencies": self.has_dependencies(),
                # Include parent for context
                "parent": self.parent_symbols[0].name if self.parent_symbols else None,
            },
        }

    @classmethod
    def from_mcp_response(
        cls, response: dict[str, Any], provider: str = "chunkhound"
    ) -> "ChunkArtifact":
        """Create ChunkArtifact from MCP response.

        This factory method handles various response formats from cAST-aware
        chunking tools like ChunkHound, normalizing them to a standard artifact structure.

        Args:
            response: Raw response dictionary from MCP chunking tool
            provider: Chunking provider name (default "chunkhound")

        Returns:
            ChunkArtifact instance

        Example:
            # From ChunkHound
            mcp_result = await mcp_adapter(
                provider="chunkhound",
                tool="chunk_file",
                params={"file_path": "src/utils.py"}
            )

            # Response might contain a list of chunks
            chunks = []
            for chunk_data in mcp_result.get("chunks", [mcp_result]):
                chunk = ChunkArtifact.from_mcp_response(
                    chunk_data,
                    provider="chunkhound"
                )
                chunks.append(chunk)

        Note:
            Expected response format:
            {
                "chunk_id": "func_calculate_total",
                "type": "function",
                "content": "def calculate_total(...):\\n    ...",
                "start_line": 42,
                "end_line": 45,
                "file_path": "src/utils.py",
                "language": "python",
                "symbols": [
                    {"name": "calculate_total", "type": "function"}
                ],
                "parent_symbols": [
                    {"name": "Utils", "type": "class"}
                ],
                "dependencies": ["chunk_id_2", "chunk_id_3"],
                "context": {
                    "docstring": "Calculate total of items"
                }
            }
        """
        # Extract chunk ID
        chunk_id = response.get("chunk_id", response.get("id", "unknown_chunk"))

        # Parse chunk type
        type_str = response.get("type", response.get("chunk_type", "other")).lower()
        type_mapping = {
            "function": ChunkType.FUNCTION,
            "method": ChunkType.METHOD,
            "class": ChunkType.CLASS,
            "module": ChunkType.MODULE,
            "block": ChunkType.BLOCK,
            "statement": ChunkType.STATEMENT,
            "import": ChunkType.IMPORT,
            "comment": ChunkType.COMMENT,
            "docstring": ChunkType.DOCSTRING,
            "other": ChunkType.OTHER,
        }
        chunk_type = type_mapping.get(type_str, ChunkType.OTHER)

        # Extract content
        content = response.get("content", response.get("code", ""))

        # Extract line numbers
        start_line = int(response.get("start_line", response.get("line_start", 1)))
        end_line = int(response.get("end_line", response.get("line_end", start_line)))

        # Extract column numbers (optional)
        start_column = response.get("start_column", response.get("col_start"))
        end_column = response.get("end_column", response.get("col_end"))

        if start_column is not None:
            start_column = int(start_column)
        if end_column is not None:
            end_column = int(end_column)

        # Extract file path
        file_path = response.get("file_path", response.get("file", response.get("path", "")))

        # Extract language
        language = response.get("language", response.get("lang", "unknown"))

        # Parse symbols
        symbols = []
        for symbol_data in response.get("symbols", []):
            if isinstance(symbol_data, dict):
                symbols.append(
                    SymbolReference(
                        name=symbol_data.get("name", ""),
                        type=symbol_data.get("type", "symbol"),
                        location=symbol_data.get("location"),
                        properties=symbol_data.get("properties", {}),
                    )
                )
            elif isinstance(symbol_data, str):
                # Simple string symbol
                symbols.append(SymbolReference(name=symbol_data, type="symbol"))

        # Parse parent symbols
        parent_symbols = []
        for parent_data in response.get("parent_symbols", response.get("parents", [])):
            if isinstance(parent_data, dict):
                parent_symbols.append(
                    SymbolReference(
                        name=parent_data.get("name", ""),
                        type=parent_data.get("type", "symbol"),
                        location=parent_data.get("location"),
                        properties=parent_data.get("properties", {}),
                    )
                )
            elif isinstance(parent_data, str):
                parent_symbols.append(SymbolReference(name=parent_data, type="symbol"))

        # Extract dependencies
        dependencies = response.get("dependencies", response.get("depends_on", []))
        if not isinstance(dependencies, list):
            dependencies = []

        # Extract context
        context = response.get("context", {})
        if not isinstance(context, dict):
            context = {}

        # Add docstring to context if present at top level
        if "docstring" in response and "docstring" not in context:
            context["docstring"] = response["docstring"]

        # Extract metadata
        metadata = {
            "provider": provider,
        }

        # Include common metadata fields
        for key in [
            "complexity",
            "cyclomatic_complexity",
            "cognitive_complexity",
            "lines_of_code",
            "parameters",
            "return_type",
        ]:
            if key in response:
                metadata[key] = response[key]

        return cls(
            chunk_id=chunk_id,
            chunk_type=chunk_type,
            content=content,
            start_line=start_line,
            end_line=end_line,
            start_column=start_column,
            end_column=end_column,
            file_path=file_path,
            language=language,
            symbols=symbols,
            parent_symbols=parent_symbols,
            dependencies=dependencies,
            context=context,
            metadata=metadata,
        )
