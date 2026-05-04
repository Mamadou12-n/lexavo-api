"""
Migration ChromaDB (legal_docs_be) → Qdrant (legal_docs_be).

- 262 500 chunks ChromaDB → upsert dans Qdrant existant (2 047 080 points).
- Pas de re-embedding : vecteurs ChromaDB réutilisés (même modèle).
- Skip chunks déjà présents dans Qdrant (par chunk_id).
- Préfixe LEGACY_ ajouté aux doc_ids ChromaDB pour les distinguer.

CLAUDE.md :
- §1 zéro invention : on garde les payloads ChromaDB tels quels
- §6 retriever non touché ici (étape suivante)
- §8 vérifier 2× : count avant/après + sample search
"""
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

CHROMA_DIR      = BASE_DIR / "output" / "chroma_db"
LOG_DIR         = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CHROMA_COLLECTION = "legal_docs_be"
QDRANT_URL        = "http://localhost:6333"
QDRANT_COLLECTION = "legal_docs_be"
VECTOR_DIM        = 384
BATCH_SIZE        = 2000   # chunks par batch (lecture + upsert)

LEGACY_PREFIX = "LEGACY_"  # marqueur pour distinguer les anciens chunks


def hr(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


def main():
    import chromadb
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    log_file = LOG_DIR / f"migrate_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )
    log = logging.getLogger("migrate")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("=" * 60)
    log.info("MIGRATION ChromaDB → Qdrant")
    log.info("=" * 60)

    # 1) ChromaDB
    if not CHROMA_DIR.exists():
        log.error(f"ChromaDB introuvable: {CHROMA_DIR}")
        sys.exit(1)

    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    chroma_col = chroma.get_collection(CHROMA_COLLECTION)
    chroma_count = chroma_col.count()
    log.info(f"ChromaDB.{CHROMA_COLLECTION}: {hr(chroma_count)} chunks")

    # 2) Qdrant
    qdrant = QdrantClient(url=QDRANT_URL, timeout=180)
    initial = qdrant.count(collection_name=QDRANT_COLLECTION, exact=True).count
    log.info(f"Qdrant.{QDRANT_COLLECTION} (initial): {hr(initial)} points")

    # 3) Migration en batch
    t0 = time.time()
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    offset = 0

    while offset < chroma_count:
        try:
            res = chroma_col.get(
                limit=BATCH_SIZE,
                offset=offset,
                include=["embeddings", "documents", "metadatas"],
            )
        except Exception as e:
            log.error(f"Erreur lecture ChromaDB offset={offset}: {e}")
            offset += BATCH_SIZE
            total_errors += 1
            continue

        ids       = res.get("ids") or []
        embs      = res.get("embeddings") or []
        docs      = res.get("documents") or []
        metas     = res.get("metadatas") or []

        if not ids:
            log.info(f"  offset={offset}: vide, fin")
            break

        points = []
        for i, chunk_id in enumerate(ids):
            try:
                emb = embs[i] if i < len(embs) else None
                if emb is None or len(emb) != VECTOR_DIM:
                    total_skipped += 1
                    continue

                meta = metas[i] if i < len(metas) else {}
                text = docs[i] if i < len(docs) else ""

                # Préfixe LEGACY_ pour distinguer (et éviter collision UUID)
                legacy_chunk_id = f"{LEGACY_PREFIX}{chunk_id}"
                doc_id = meta.get("doc_id", "")
                legacy_doc_id = f"{LEGACY_PREFIX}{doc_id}" if doc_id and not doc_id.startswith(LEGACY_PREFIX) else doc_id

                payload = {
                    "doc_id":       legacy_doc_id,
                    "chunk_id":     legacy_chunk_id,
                    "source":       meta.get("source", ""),
                    "doc_type":     meta.get("doc_type", ""),
                    "jurisdiction": meta.get("jurisdiction", ""),
                    "title":        (meta.get("title", "") or "")[:200],
                    "date":         meta.get("date", ""),
                    "url":          (meta.get("url", "") or "")[:500],
                    "ecli":         meta.get("ecli", ""),
                    "chunk_idx":    int(meta.get("chunk_idx", 0)) if meta.get("chunk_idx") is not None else 0,
                    "chunk_count":  int(meta.get("chunk_count", 1)) if meta.get("chunk_count") is not None else 1,
                    "text":         text,
                    "legacy":       True,  # flag pour identifier les chunks migrés
                }

                points.append(PointStruct(
                    id=chunk_id_to_uuid(legacy_chunk_id),
                    vector=list(emb),
                    payload=payload,
                ))
            except Exception as e:
                total_errors += 1
                log.warning(f"  Erreur chunk {chunk_id}: {e}")
                continue

        # Upsert Qdrant avec retry
        if points:
            for attempt in range(3):
                try:
                    qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=False)
                    total_migrated += len(points)
                    break
                except Exception as e:
                    log.warning(f"  upsert retry {attempt+1}: {e}")
                    time.sleep(2)
            else:
                total_errors += len(points)
                log.error(f"  Upsert échec offset={offset} après 3 tentatives")

        offset += BATCH_SIZE

        # Log progress
        elapsed = time.time() - t0
        rate = total_migrated / elapsed if elapsed > 0 else 0
        progress = min(100, 100 * offset / chroma_count)
        log.info(f"  [{progress:5.1f}%] {hr(total_migrated)}/{hr(chroma_count)} migrés (skip: {total_skipped}, err: {total_errors}) — {rate:.0f} chunks/s")

    elapsed = time.time() - t0
    final = qdrant.count(collection_name=QDRANT_COLLECTION, exact=True).count
    log.info("")
    log.info("=" * 60)
    log.info(f"MIGRATION TERMINÉE en {timedelta(seconds=int(elapsed))}")
    log.info("=" * 60)
    log.info(f"  Chunks ChromaDB lus    : {hr(chroma_count)}")
    log.info(f"  Chunks migrés Qdrant   : {hr(total_migrated)}")
    log.info(f"  Skip (vecteur invalide): {hr(total_skipped)}")
    log.info(f"  Erreurs                : {hr(total_errors)}")
    log.info(f"  Qdrant avant : {hr(initial)}")
    log.info(f"  Qdrant après : {hr(final)}")
    log.info(f"  Delta        : {hr(final - initial)}")

    # Vérification : sample search sur un legacy chunk
    log.info("")
    log.info("VÉRIFICATION (sample search legacy)")
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    res = qdrant.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="legacy", match=MatchValue(value=True))]),
        limit=3,
        with_payload=True,
        with_vectors=False,
    )
    points = res[0] if isinstance(res, tuple) else res
    log.info(f"  Sample legacy points: {len(points)}")
    for p in points[:3]:
        pl = p.payload or {}
        log.info(f"    - {pl.get('chunk_id', '')[:60]} | {pl.get('source', '')} | {pl.get('title', '')[:60]}")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
