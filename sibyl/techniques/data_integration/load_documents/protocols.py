"""Protocols for load documents technique."""

from dataclasses import dataclass
from typing import Any


@dataclass
class LoadDocumentsResult:
    """Result from document loading operation.

    Attributes:
        documents: List of loaded documents
        count: Number of documents loaded
        source: Source name
    """

    documents: list[dict[str, Any]]
    count: int
    source: str
