"""
Indexation sélective vers QDRANT (port 6333) — sources CONFORMES uniquement.
Bypass ChromaDB (RAM saturée). Mêmes chunks, mêmes embeddings.

Modèle : paraphrase-multilingual-MiniLM-L12-v2 (384 dims, FR/NL/DE/EN)
Distance : cosine
Collection Qdrant : legal_docs_be
"""
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR
from rag.indexer import (
    chunk_text,
    CHUNK_SIZE, CHUNK_SIZE_CODE,
    CHUNK_OVERLAP, CHUNK_OVERLAP_CODE,
    MAX_CHUNKS_PER_DOC_DEFAULT, MAX_CHUNKS_PER_DOC_CODE,
    SOURCES_CODES, EMBED_MODEL,
)

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

QDRANT_URL      = "http://localhost:6333"
COLLECTION_NAME = "legal_docs_be"
VECTOR_DIM      = 384
BATCH_SIZE      = 1000

CONFORME_PREFIXES = (
    "CONSEIL_ETAT_", "CCE_", "CODEX_VL_", "CONSCONST_", "CHAMBRE_",
    "FSMA_", "CCREK_", "DATAGOV_", "APD_", "CBE_", "CNT_",
    "WALLEX_", "BRUXELLES_", "FISCONET_", "KULEUVEN_", "HUDOC_", "GALLILEX_",
)

stamp    = datetime.now().strftime("%Y%m%d_%H%M")
log_file = LOG_DIR / f"index_qdrant_{stamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
    ],
)
log = logging.getLogger("index_qdrant")


def hr(n: int) -> str:
    return f"{n:,}".replace(",", "\u00a0")


def chunk_id_to_uuid(chunk_id: str) -> str:
    """Qdrant n'accepte que des UUID ou des entiers. Hash déterministe stem__chunk_NNN -> UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, PointStruct,
        PayloadSchemaType, OptimizersConfigDiff,
    )
    from sentence_transformers import SentenceTransformer

    log.info("=" * 60)
    log.info("INDEXATION QDRANT — SOURCES CONFORMES")
    log.info("=" * 60)

    # 1) Filtrer les fichiers conformes
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    log.info(f"Total normalisés: {hr(len(all_files))}")

    files = sorted([
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ])
    log.info(f"Conformes à indexer: {hr(len(files))}")

    # 2) Connexion Qdrant + collection
    client = QdrantClient(url=QDRANT_URL, timeout=60)
    log.info(f"Qdrant: {QDRANT_URL}")

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            optimizers_config=OptimizersConfigDiff(memmap_threshold=20000),
        )
        log.info(f"Collection créée: {COLLECTION_NAME}")
        # Index sur doc_id pour dedup rapide
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="doc_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass
    else:
        log.info(f"Collection existante: {COLLECTION_NAME}")

    initial_count = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"Chunks déjà dans Qdrant: {hr(initial_count)}")

    # 3) Charger embedding model
    log.info(f"Chargement modèle: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    log.info(f"  dim={model.get_sentence_embedding_dimension()}")

    # 4) Skip rapide: récupérer doc_ids déjà indexés
    existing_doc_ids = set()
    if initial_count > 0:
        log.info("Chargement doc_ids existants pour dedup...")
        offset = None
        while True:
            res, offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=5000,
                offset=offset,
                with_payload=["doc_id"],
                with_vectors=False,
            )
            for p in res:
                did = (p.payload or {}).get("doc_id")
                if did:
                    existing_doc_ids.add(did)
            if offset is None:
                break
        log.info(f"  {hr(len(existing_doc_ids))} doc_ids déjà indexés")

    # 5) Indexer en batch
    total_chunks = 0
    batch_texts, batch_points = [], []
    t0 = time.time()

    for i, json_file in enumerate(files):
        try:
            doc = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"  Erreur lecture {json_file.name}: {e}")
            continue

        doc_id   = doc.get("doc_id", json_file.stem)
        text     = doc.get("full_text", "") or doc.get("title", "")
        title    = doc.get("title", "")
        source   = doc.get("source", "")
        date     = doc.get("date", "")
        url      = doc.get("url", "")
        ecli     = doc.get("ecli", "")
        doc_type = doc.get("doc_type", "")
        jurisdiction = doc.get("jurisdiction", "")

        if not text:
            continue

        if doc_id in existing_doc_ids:
            continue

        enriched = f"{title}\n\n{text}" if title and title not in text[:200] else text

        is_code = (
            source in SOURCES_CODES
            or "coordonné" in doc_type.lower()
            or title.lower().startswith(("code ", "nouveau code ", "loi ", "arrêté ", "décret ", "constitution"))
        )
        if is_code:
            c_size, c_overlap, max_chunks = CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE
        else:
            c_size, c_overlap, max_chunks = CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT

        chunks = chunk_text(enriched, chunk_size=c_size, overlap=c_overlap)[:max_chunks]
        if not chunks:
            continue

        for j, chunk in enumerate(chunks):
            chunk_id = f"{json_file.stem}__chunk_{j:03d}"
            batch_texts.append(chunk)
            batch_points.append(PointStruct(
                id=chunk_id_to_uuid(chunk_id),
                vector=[],  # rempli après embedding
                payload={
                    "doc_id":       doc_id,
                    "chunk_id":     chunk_id,
                    "source":       source,
                    "doc_type":     doc_type,
                    "jurisdiction": jurisdiction,
                    "title":        title[:200],
                    "date":         date,
                    "url":          url[:500],
                    "ecli":         ecli,
                    "chunk_idx":    j,
                    "chunk_count": len(chunks),
                    "text":         chunk,
                },
            ))

            if len(batch_texts) >= BATCH_SIZE:
                embs = model.encode(batch_texts, batch_size=128, show_progress_bar=False).tolist()
                for p, e in zip(batch_points, embs):
                    p.vector = e
                client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=False)
                total_chunks += len(batch_points)
                elapsed = time.time() - t0
                rate = total_chunks / elapsed if elapsed > 0 else 0
                log.info(
                    f"  [{i+1}/{hr(len(files))}] +{len(batch_points)} chunks "
                    f"(total: {hr(total_chunks)}) — {rate:.0f} chunks/s"
                )
                batch_texts, batch_points = [], []

    if batch_texts:
        embs = model.encode(batch_texts, batch_size=128, show_progress_bar=False).tolist()
        for p, e in zip(batch_points, embs):
            p.vector = e
        client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=True)
        total_chunks += len(batch_points)

    elapsed = time.time() - t0
    final = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(
        f"\nINDEXATION QDRANT TERMINÉE en {timedelta(seconds=int(elapsed))}\n"
        f"  Nouveaux chunks: {hr(total_chunks)}\n"
        f"  Total Qdrant   : {hr(final)}"
    )


if __name__ == "__main__":
    main()
