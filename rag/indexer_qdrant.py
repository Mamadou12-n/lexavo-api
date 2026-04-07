"""
RAG Indexer Qdrant — App Droit Belgique
Indexation sur Qdrant (stockage disque) pour gérer des millions de documents.

Qdrant tourne déjà sur Docker (port 6333) pour Phantom.
Modèle : paraphrase-multilingual-MiniLM-L12-v2 (384 dim, multilingue FR/NL/DE/EN)

Avantages vs ChromaDB :
  - Stockage sur disque (pas tout en RAM)
  - Peut gérer des millions de vecteurs
  - Filtrage avancé par métadonnées
  - API REST + gRPC
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("indexer_qdrant")

# ─── Configuration ────────────────────────────────────────────────────────────
NORMALIZED_DIR = OUTPUT_DIR / "normalized"
COLLECTION_NAME = "legal_docs_be"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBED_DIM = 384
QDRANT_URL = "http://localhost:6333"

# Paramètres de chunking (mêmes que indexer.py)
CHUNK_SIZE = 512
CHUNK_SIZE_CODE = 1500
CHUNK_OVERLAP = 64
CHUNK_OVERLAP_CODE = 200
MAX_CHUNKS_PER_DOC_DEFAULT = 20
MAX_CHUNKS_PER_DOC_CODE = 2000

SOURCES_CODES = {"JUSTEL", "Codex Vlaanderen", "GalliLex", "WalLex", "ETAAMB",
                 "SPF Finances", "SPF Emploi", "Bruxelles"}


# ─── Chunking (identique à indexer.py) ───────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            words = para.split()
            temp = ""
            for word in words:
                if len(temp) + len(word) + 1 > chunk_size:
                    if temp:
                        chunks.append(temp.strip())
                    temp = current_chunk[-overlap:] + word + " " if current_chunk else word + " "
                    current_chunk = ""
                else:
                    temp += word + " "
            if temp:
                current_chunk = temp
        else:
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return [c for c in chunks if len(c) >= 50]


# ─── Indexation Qdrant ───────────────────────────────────────────────────────

def build_index(
    normalized_dir: Path = NORMALIZED_DIR,
    batch_size: int = 200,
    max_docs: Optional[int] = None,
    reset: bool = False,
) -> int:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        OptimizersConfigDiff, HnswConfigDiff,
    )
    from sentence_transformers import SentenceTransformer

    log.info("=== Démarrage indexation Qdrant ===")
    log.info(f"  Modèle embeddings : {EMBED_MODEL}")
    log.info(f"  Qdrant : {QDRANT_URL}")
    log.info(f"  Répertoire docs : {normalized_dir}")

    # Connexion Qdrant
    client = QdrantClient(url=QDRANT_URL, timeout=60)
    info = client.get_collections()
    existing_names = [c.name for c in info.collections]

    if reset and COLLECTION_NAME in existing_names:
        log.info("  Reset : suppression collection existante")
        client.delete_collection(COLLECTION_NAME)
        existing_names.remove(COLLECTION_NAME)

    if COLLECTION_NAME not in existing_names:
        log.info(f"  Création collection '{COLLECTION_NAME}' (dim={EMBED_DIM})")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBED_DIM,
                distance=Distance.COSINE,
                on_disk=True,  # Vecteurs sur disque — pas en RAM
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=128,
                on_disk=True,  # Index HNSW sur disque aussi
            ),
            optimizers_config=OptimizersConfigDiff(
                memmap_threshold=10000,  # Basculer sur disque après 10K vecteurs
                indexing_threshold=20000,
            ),
        )

    # Charger le modèle d'embedding
    log.info("Chargement modèle d'embedding...")
    model = SentenceTransformer(EMBED_MODEL)
    log.info(f"  Modèle chargé (dim={model.get_sentence_embedding_dimension()})")

    # Charger les doc_ids déjà indexés
    existing_doc_ids = set()
    if not reset:
        try:
            count = client.count(COLLECTION_NAME).count
            log.info(f"  Points existants : {count}")
            if count > 0:
                log.info("  Chargement des doc_ids existants pour skip rapide...")
                offset = None
                while True:
                    result = client.scroll(
                        collection_name=COLLECTION_NAME,
                        limit=1000,
                        offset=offset,
                        with_payload=["doc_id"],
                        with_vectors=False,
                    )
                    points, next_offset = result
                    if not points:
                        break
                    for p in points:
                        existing_doc_ids.add(p.payload.get("doc_id", ""))
                    offset = next_offset
                    if offset is None:
                        break
                log.info(f"  {len(existing_doc_ids)} docs déjà indexés")
        except Exception as e:
            log.warning(f"  Erreur lecture existants : {e}")

    # Charger les fichiers
    files = sorted(normalized_dir.glob("*.json"))
    if max_docs:
        files = files[:max_docs]
    log.info(f"  {len(files)} documents à indexer")

    # Indexer
    total_chunks = 0
    batch_points = []

    for i, json_file in enumerate(files):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            log.warning(f"  Erreur lecture {json_file.name}: {e}")
            continue

        doc_id = doc.get("doc_id", json_file.stem)
        text = doc.get("full_text", "") or doc.get("title", "")
        title = doc.get("title", "")
        source = doc.get("source", "")
        date = doc.get("date", "")
        url = doc.get("url", "")
        ecli = doc.get("ecli", "")
        doc_type = doc.get("doc_type", "")
        jurisdiction = doc.get("jurisdiction", "")

        if not text:
            continue

        if existing_doc_ids and doc_id in existing_doc_ids:
            continue

        enriched_text = f"{title}\n\n{text}" if title and title not in text[:200] else text

        is_code = (
            source in SOURCES_CODES
            or "coordonné" in doc_type.lower()
            or title.lower().startswith("code ")
            or title.lower().startswith("nouveau code ")
            or title.lower().startswith("loi ")
            or title.lower().startswith("arrêté ")
            or title.lower().startswith("décret ")
            or title.lower().startswith("constitution")
        )
        if is_code:
            c_size, c_overlap, max_chunks = CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE
        else:
            c_size, c_overlap, max_chunks = CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT

        chunks = chunk_text(enriched_text, chunk_size=c_size, overlap=c_overlap)[:max_chunks]
        if not chunks:
            continue

        # Encoder les chunks
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        for j, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}__chunk_{j:03d}"))
            batch_points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "source": source,
                    "doc_type": doc_type,
                    "jurisdiction": jurisdiction,
                    "title": title[:200],
                    "date": date,
                    "url": url[:500],
                    "ecli": ecli,
                    "chunk_idx": j,
                    "chunk_count": len(chunks),
                    "text": chunk,
                },
            ))

            if len(batch_points) >= batch_size:
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch_points,
                )
                total_chunks += len(batch_points)
                batch_points = []
                log.info(f"  [{i+1}/{len(files)}] +{batch_size} chunks (total: {total_chunks})")

    # Dernier batch
    if batch_points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch_points,
        )
        total_chunks += len(batch_points)

    log.info(f"=== Indexation Qdrant terminée : {total_chunks} chunks ===")

    # Stats
    count = client.count(COLLECTION_NAME).count
    log.info(f"  Total dans Qdrant : {count} points")

    return total_chunks


def get_index_stats() -> Dict:
    from qdrant_client import QdrantClient
    try:
        client = QdrantClient(url=QDRANT_URL, timeout=10)
        info = client.get_collection(COLLECTION_NAME)
        count = client.count(COLLECTION_NAME).count

        # Échantillon pour stats par source
        sources = {}
        doc_ids = set()
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=5000,
            with_payload=["source", "doc_id"],
            with_vectors=False,
        )
        for p in result[0]:
            src = p.payload.get("source", "?")
            sources[src] = sources.get(src, 0) + 1
            doc_ids.add(p.payload.get("doc_id", ""))

        return {
            "status": "ok",
            "backend": "qdrant",
            "collection": COLLECTION_NAME,
            "total_chunks": count,
            "total_documents_sample": len(doc_ids),
            "sources_sample": sources,
            "vectors_on_disk": True,
        }
    except Exception as e:
        return {"status": "erreur", "error": str(e)}


def search(query: str, top_k: int = 10, source_filter: str = None) -> List[Dict]:
    """Recherche sémantique dans l'index Qdrant."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    from sentence_transformers import SentenceTransformer

    client = QdrantClient(url=QDRANT_URL, timeout=30)
    model = SentenceTransformer(EMBED_MODEL)

    query_vec = model.encode(query).tolist()

    search_filter = None
    if source_filter:
        search_filter = Filter(must=[
            FieldCondition(key="source", match=MatchValue(value=source_filter))
        ])

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vec,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )

    return [
        {
            "score": hit.score,
            "text": hit.payload.get("text", ""),
            "title": hit.payload.get("title", ""),
            "source": hit.payload.get("source", ""),
            "date": hit.payload.get("date", ""),
            "url": hit.payload.get("url", ""),
            "doc_id": hit.payload.get("doc_id", ""),
        }
        for hit in results
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Indexer Qdrant — App Droit Belgique")
    parser.add_argument("--reset", action="store_true", help="Réinitialiser l'index")
    parser.add_argument("--max", type=int, default=None, help="Limite de docs")
    parser.add_argument("--stats", action="store_true", help="Afficher les stats")
    parser.add_argument("--search", type=str, default=None, help="Recherche sémantique")
    parser.add_argument("--normalize-first", action="store_true", help="Normaliser avant indexation")
    args = parser.parse_args()

    if args.stats:
        stats = get_index_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif args.search:
        results = search(args.search)
        for r in results:
            print(f"  [{r['score']:.3f}] {r['source']} | {r['title'][:60]} | {r['date']}")
            print(f"    {r['text'][:150]}...")
            print()
    else:
        if args.normalize_first:
            from processors.cleaner import process_all_sources
            stats = process_all_sources()
            total_valid = sum(s["valid"] for s in stats.values())
            log.info(f"Normalisation : {total_valid} docs valides")

        count = build_index(reset=args.reset, max_docs=args.max)
        print(f"\nIndex Qdrant construit : {count} chunks")
