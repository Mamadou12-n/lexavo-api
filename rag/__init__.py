"""RAG — Retrieval-Augmented Generation pour App Droit Belgique."""
from rag.pipeline import ask
from rag.retriever import retrieve, format_context
from rag.indexer import build_index, get_index_stats

__all__ = ["ask", "retrieve", "format_context", "build_index", "get_index_stats"]
