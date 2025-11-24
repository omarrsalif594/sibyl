"""Load documents technique for data integration.

This technique loads documents from a DocumentSourceProvider and prepares them
for processing in a RAG pipeline.
"""

from sibyl.techniques.data_integration.load_documents.technique import build_technique

__all__ = ["build_technique"]
