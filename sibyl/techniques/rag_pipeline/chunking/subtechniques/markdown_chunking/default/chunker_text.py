"""
Text and markdown chunker for core plugin system.

This chunker handles generic text and markdown content by splitting
on headings, paragraph boundaries, and other natural divisions.
"""

import hashlib
import re

from sibyl.core.protocols.rag_pipeline.code_processing import Chunk, CodeType


class TextChunker:
    """
    Generic text and markdown chunker.

    Splits content by:
    - Markdown headings (for markdown)
    - Paragraph boundaries (double newlines)
    - Maximum chunk size (to prevent overly large chunks)
    """

    def __init__(self, max_chunk_lines: int = 50, min_chunk_lines: int = 3) -> None:
        """
        Initialize the text chunker.

        Args:
            max_chunk_lines: Maximum lines per chunk
            min_chunk_lines: Minimum lines to consider a chunk
        """
        self.max_chunk_lines = max_chunk_lines
        self.min_chunk_lines = min_chunk_lines

    def supports(self, code_type: CodeType) -> bool:
        """Support TEXT and MARKDOWN types."""
        return code_type in (CodeType.TEXT, CodeType.MARKDOWN)

    def chunk(self, code: str, code_type: CodeType, **opts) -> list[Chunk]:
        """
        Split text/markdown into logical chunks.

        Args:
            code: The text content to chunk
            code_type: TEXT or MARKDOWN
            **opts: Optional overrides for max_chunk_lines, min_chunk_lines

        Returns:
            List of Chunk objects
        """
        if not self.supports(code_type):
            msg = f"TextChunker does not support {code_type}"
            raise ValueError(msg)

        max_lines = opts.get("max_chunk_lines", self.max_chunk_lines)
        min_lines = opts.get("min_chunk_lines", self.min_chunk_lines)

        if code_type == CodeType.MARKDOWN:
            return self._chunk_markdown(code, max_lines, min_lines)
        return self._chunk_text(code, max_lines, min_lines)

    def _chunk_markdown(self, content: str, max_lines: int, min_lines: int) -> list[Chunk]:
        """
        Chunk markdown by headings and paragraph boundaries.

        Args:
            content: Markdown content
            max_lines: Maximum lines per chunk
            min_lines: Minimum lines per chunk

        Returns:
            List of Chunk objects
        """
        lines = content.split("\n")
        chunks = []
        current_chunk_lines = []
        current_start = 1
        chunk_num = 0

        for i, line in enumerate(lines, start=1):
            # Check for markdown heading
            is_heading = re.match(r"^#{1,6}\s+", line)

            # Start new chunk on heading (if we have content)
            if is_heading and current_chunk_lines:
                chunk_content = "\n".join(current_chunk_lines)
                if len(current_chunk_lines) >= min_lines:
                    chunks.append(
                        self._create_chunk(
                            chunk_content, CodeType.MARKDOWN, current_start, i - 1, chunk_num
                        )
                    )
                    chunk_num += 1
                current_chunk_lines = [line]
                current_start = i
            else:
                current_chunk_lines.append(line)

            # Split if chunk gets too large
            if len(current_chunk_lines) >= max_lines:
                chunk_content = "\n".join(current_chunk_lines)
                chunks.append(
                    self._create_chunk(
                        chunk_content, CodeType.MARKDOWN, current_start, i, chunk_num
                    )
                )
                chunk_num += 1
                current_chunk_lines = []
                current_start = i + 1

        # Add final chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if len(current_chunk_lines) >= min_lines or not chunks:
                chunks.append(
                    self._create_chunk(
                        chunk_content, CodeType.MARKDOWN, current_start, len(lines), chunk_num
                    )
                )

        return (
            chunks if chunks else [self._create_chunk(content, CodeType.MARKDOWN, 1, len(lines), 0)]
        )

    def _chunk_text(self, content: str, max_lines: int, min_lines: int) -> list[Chunk]:
        """
        Chunk plain text by paragraph boundaries.

        Args:
            content: Text content
            max_lines: Maximum lines per chunk
            min_lines: Minimum lines per chunk

        Returns:
            List of Chunk objects
        """
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r"\n\s*\n", content)

        chunks = []
        current_chunk_lines = []
        current_start = 1
        chunk_num = 0
        line_num = 1

        for para in paragraphs:
            para_lines = para.split("\n")

            # If adding this paragraph exceeds max, flush current chunk
            if current_chunk_lines and len(current_chunk_lines) + len(para_lines) > max_lines:
                chunk_content = "\n".join(current_chunk_lines)
                if len(current_chunk_lines) >= min_lines:
                    chunks.append(
                        self._create_chunk(
                            chunk_content, CodeType.TEXT, current_start, line_num - 1, chunk_num
                        )
                    )
                    chunk_num += 1
                current_chunk_lines = []
                current_start = line_num

            current_chunk_lines.extend(para_lines)
            current_chunk_lines.append("")  # Preserve paragraph break
            line_num += len(para_lines) + 1

        # Add final chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines).rstrip()
            if len(current_chunk_lines) >= min_lines or not chunks:
                chunks.append(
                    self._create_chunk(
                        chunk_content, CodeType.TEXT, current_start, line_num - 1, chunk_num
                    )
                )

        return (
            chunks
            if chunks
            else [self._create_chunk(content, CodeType.TEXT, 1, len(content.split("\n")), 0)]
        )

    def _create_chunk(
        self, content: str, code_type: CodeType, start_line: int, end_line: int, chunk_num: int
    ) -> Chunk:
        """
        Create a Chunk object with metadata.

        Args:
            content: Chunk content
            code_type: Type of code
            start_line: Starting line number
            end_line: Ending line number
            chunk_num: Sequential chunk number

        Returns:
            Chunk object
        """
        # Generate stable chunk ID
        chunk_id = hashlib.sha256(
            f"{code_type}:{start_line}:{end_line}:{content[:100]}".encode()
        ).hexdigest()[:16]

        return Chunk(
            chunk_id=chunk_id,
            content=content,
            metadata={
                "code_type": code_type.value,
                "chunk_number": chunk_num,
                "line_count": end_line - start_line + 1,
            },
            start_line=start_line,
            end_line=end_line,
            description=f"{code_type.value} chunk {chunk_num}",
        )
