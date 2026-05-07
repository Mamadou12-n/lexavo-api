"""DEPRECATED — rag/indexer.py (ChromaDB) archivé dans rag/_archived/.

Utilisez rag/indexer_qdrant.py à la place.

Ce fichier reste pour compatibilité mais redirige toutes les fonctions vers Qdrant.
"""
import warnings

warnings.warn(
    "rag/indexer.py (ChromaDB) est deprecated. "
    "Utilisez rag/indexer_qdrant.py. "
    "Code legacy disponible dans rag/_archived/indexer_chromadb_legacy.py",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exports pour ne pas casser les imports existants
from rag.indexer_qdrant import (
    build_index,
    get_index_stats,
    search,
    create_payload_indexes,
    COLLECTION_NAME,
    EMBED_MODEL,
)

__all__ = [
    "build_index",
    "get_index_stats",
    "search",
    "create_payload_indexes",
    "COLLECTION_NAME",
    "EMBED_MODEL",
]
