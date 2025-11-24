"""
Simple SQL chunker for core plugin system.

This is a deliberately basic SQL chunker that splits on statement boundaries.
"""

import hashlib
import re

from sibyl.core.protocols.rag_pipeline.code_processing import Chunk, CodeType


class SimpleSQLChunker:
    """
    Basic SQL chunker that splits on statement boundaries.

    This chunker:
    - Splits on semicolons (statement terminators)
    - Recognizes basic CTE boundaries (WITH clauses)
    - Does NOT perform advanced pattern detection
    - Does NOT contain proprietary SQL intelligence
    """

    def supports(self, code_type: CodeType) -> bool:
        """Support SQL type only."""
        return code_type == CodeType.SQL

    def chunk(self, code: str, code_type: CodeType, **opts) -> list[Chunk]:
        """
        Split SQL into statement-level chunks.

        Args:
            code: SQL code to chunk
            code_type: Must be CodeType.SQL
            **opts: Reserved for future options

        Returns:
            List of Chunk objects, one per statement
        """
        if not self.supports(code_type):
            msg = f"SimpleSQLChunker does not support {code_type}"
            raise ValueError(msg)

        # Split on semicolons, preserving the semicolon
        statements = self._split_statements(code)

        chunks = []
        line_offset = 1

        for idx, stmt in enumerate(statements):
            if not stmt.strip():
                continue

            stmt_lines = stmt.split("\n")
            start_line = line_offset
            end_line = line_offset + len(stmt_lines) - 1

            chunk = self._create_chunk(stmt, start_line, end_line, idx)
            chunks.append(chunk)

            line_offset = end_line + 1

        return chunks if chunks else [self._create_chunk(code, 1, len(code.split("\n")), 0)]

    def _split_statements(self, sql: str) -> list[str]:
        """
        Split SQL into statements on semicolons.

        This is a simple split that doesn't handle:
        - Semicolons in strings
        - Semicolons in comments
        - Complex nested structures

        For production use, consider a proper SQL parser.

        Args:
            sql: SQL code

        Returns:
            List of statement strings
        """
        # Simple split on semicolon followed by whitespace/newline
        statements = re.split(r";\s*\n", sql)

        # Re-add semicolons (except for last statement if it didn't have one)
        result = []
        for i, stmt in enumerate(statements):
            if i < len(statements) - 1:
                result.append(stmt + ";")
            elif stmt.strip():
                result.append(stmt)

        return result

    def _create_chunk(self, content: str, start_line: int, end_line: int, chunk_num: int) -> Chunk:
        """
        Create a Chunk object for a SQL statement.

        Args:
            content: SQL statement content
            start_line: Starting line number
            end_line: Ending line number
            chunk_num: Sequential chunk number

        Returns:
            Chunk object
        """
        # Determine basic statement type
        stmt_type = self._detect_statement_type(content)

        # Generate stable chunk ID
        chunk_id = hashlib.sha256(
            f"sql:{start_line}:{end_line}:{content[:100]}".encode()
        ).hexdigest()[:16]

        return Chunk(
            chunk_id=chunk_id,
            content=content,
            metadata={
                "code_type": "sql",
                "chunk_number": chunk_num,
                "statement_type": stmt_type,
                "line_count": end_line - start_line + 1,
            },
            start_line=start_line,
            end_line=end_line,
            description=f"SQL {stmt_type} statement",
        )

    def _detect_statement_type(self, sql: str) -> str:
        """
        Detect basic SQL statement type.

        Args:
            sql: SQL statement

        Returns:
            Statement type string (select, insert, update, delete, etc.)
        """
        sql_upper = sql.strip().upper()

        if sql_upper.startswith("WITH"):
            return "cte"
        if sql_upper.startswith("SELECT"):
            return "select"
        if sql_upper.startswith("INSERT"):
            return "insert"
        if sql_upper.startswith("UPDATE"):
            return "update"
        if sql_upper.startswith("DELETE"):
            return "delete"
        if sql_upper.startswith("CREATE"):
            return "create"
        if sql_upper.startswith("ALTER"):
            return "alter"
        if sql_upper.startswith("DROP"):
            return "drop"
        return "statement"
