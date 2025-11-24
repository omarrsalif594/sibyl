"""Filesystem Markdown document source provider.

This module provides a document source implementation that reads markdown files
from the local filesystem, implementing the DocumentSourceProvider protocol.
"""

import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from sibyl.core.protocols.infrastructure.data_providers import (
    Document,
    DocumentMetadata,
)

logger = logging.getLogger(__name__)


class FilesystemMarkdownSource:
    """Document source that reads markdown files from filesystem.

    This provider scans a directory tree for markdown files and provides
    access to them through the DocumentSourceProvider protocol interface.

    Features:
    - Glob pattern matching for file discovery
    - Metadata extraction from file stats and content
    - Title extraction from first H1 heading or filename
    - Filtering by modification time and limits

    Example:
        >>> source = FilesystemMarkdownSource(
        ...     root="./docs",
        ...     pattern="**/*.md"
        ... )
        >>> docs = list(source.iterate_documents())
        >>> print(f"Found {len(docs)} documents")
    """

    def __init__(self, root: str, pattern: str = "**/*.md", **kwargs) -> None:
        """Initialize filesystem markdown source.

        Args:
            root: Root directory path to search for markdown files
            pattern: Glob pattern for matching files (default: "**/*.md")
            **kwargs: Additional configuration options (reserved for future use)
        """
        self.root = Path(root)
        self.pattern = pattern
        self.kwargs = kwargs

        if not self.root.exists():
            msg = f"Root directory does not exist: {self.root}"
            raise ValueError(msg)
        if not self.root.is_dir():
            msg = f"Root path is not a directory: {self.root}"
            raise ValueError(msg)

        logger.info(
            f"Initialized FilesystemMarkdownSource: root={self.root}, pattern={self.pattern}"
        )

    def list_documents(self, **filters) -> list[DocumentMetadata]:
        """List all markdown files matching pattern.

        Args:
            **filters: Optional filters to apply:
                - modified_after (datetime): Only include files modified after this time
                - limit (int): Maximum number of documents to return

        Returns:
            List of DocumentMetadata objects for matching files
        """
        modified_after = filters.get("modified_after")
        limit = filters.get("limit")

        metadata_list = []
        file_paths = self.root.glob(self.pattern)

        for file_path in sorted(file_paths):
            if not file_path.is_file():
                continue

            # Apply modification time filter
            if modified_after:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < modified_after:
                    continue

            # Create metadata
            metadata = self._create_metadata(file_path)
            metadata_list.append(metadata)

            # Apply limit filter
            if limit and len(metadata_list) >= limit:
                break

        logger.debug("Found %s documents matching filters", len(metadata_list))
        return metadata_list

    def get_document(self, doc_id: str) -> Document:
        """Read a specific markdown file.

        Args:
            doc_id: Document identifier (relative file path from root)

        Returns:
            Document object with content and metadata

        Raises:
            KeyError: If document not found
            IOError: If file cannot be read
        """
        # Reconstruct file path from doc_id
        file_path = self.root / doc_id

        if not file_path.exists():
            msg = f"Document not found: {doc_id}"
            raise KeyError(msg)

        if not file_path.is_file():
            msg = f"Document path is not a file: {doc_id}"
            raise KeyError(msg)

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            msg = f"Failed to read document {doc_id}: {e}"
            raise OSError(msg) from e

        # Get file stats
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        # Extract title from content or filename
        title = self._extract_title(content, file_path)

        # Create document
        document = Document(
            id=doc_id,
            content=content,
            metadata={
                "title": title,
                "size": stat.st_size,
                "path": str(file_path),
            },
            uri=f"file://{file_path.absolute()}",
            created_at=created_at,
            updated_at=updated_at,
        )

        logger.debug("Retrieved document: %s", doc_id)
        return document

    def iterate_documents(self, **filters) -> Iterator[Document]:
        """Stream documents one by one.

        Args:
            **filters: Optional filters (same as list_documents)

        Yields:
            Document objects one at a time
        """
        modified_after = filters.get("modified_after")
        limit = filters.get("limit")

        count = 0
        file_paths = self.root.glob(self.pattern)

        for file_path in sorted(file_paths):
            if not file_path.is_file():
                continue

            # Apply modification time filter
            if modified_after:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < modified_after:
                    continue

            # Create and yield document
            try:
                doc_id = str(file_path.relative_to(self.root))
                document = self.get_document(doc_id)
                yield document
                count += 1
            except Exception as e:
                logger.warning("Failed to read document %s: %s", file_path, e)
                continue

            # Apply limit filter
            if limit and count >= limit:
                break

        logger.debug("Iterated over %s documents", count)

    def _create_metadata(self, file_path: Path) -> DocumentMetadata:
        """Create metadata object for a file.

        Args:
            file_path: Path to the file

        Returns:
            DocumentMetadata object
        """
        stat = file_path.stat()
        doc_id = str(file_path.relative_to(self.root))

        # Try to extract title from file (peek at first few lines)
        title = None
        try:
            with file_path.open("r", encoding="utf-8") as f:
                # Read first 10 lines to find title
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
        except Exception as e:
            logger.debug("Could not extract title from %s: %s", file_path, e)

        # Fallback to filename if no title found
        if not title:
            title = file_path.stem.replace("_", " ").replace("-", " ").title()

        return DocumentMetadata(
            id=doc_id,
            uri=f"file://{file_path.absolute()}",
            title=title,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            updated_at=datetime.fromtimestamp(stat.st_mtime),
            metadata={
                "size": stat.st_size,
                "path": str(file_path),
            },
        )

    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from markdown content or filename.

        Args:
            content: Markdown file content
            file_path: Path to the file (fallback for title)

        Returns:
            Extracted title string
        """
        # Try to find first H1 heading
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fallback to filename
        return file_path.stem.replace("_", " ").replace("-", " ").title()
