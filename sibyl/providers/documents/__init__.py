"""Document source providers for Sibyl.

This package contains implementations of DocumentSourceProvider protocol
for various document backends (filesystem, S3, databases, etc.).
"""

from sibyl.providers.documents.filesystem_markdown import FilesystemMarkdownSource

__all__ = ["FilesystemMarkdownSource"]
