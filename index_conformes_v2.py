"""
Indexation conformes dans une NOUVELLE collection ChromaDB (legal_docs_be_v2).
Évite le crash RAM en démarrant à 0 chunks (pas besoin de charger HNSW existant).

L'ancienne collection `legal_docs_be` (262 500 chunks codes belges) reste intacte.
Le retriever pourra interroger les deux collections ou seulement v2.
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
CHROMA_DIR     = OUTPUT_DIR / "chroma_db"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

NEW_COLLECTION = "legal_docs_be_v2"

CONFORME_PREFIXES = (
    "CONSEIL_ETAT_", "CCE_", "CODEX_VL_", "CONSCONST_", "CHAMBRE_",
    "FSMA_", "CCREK_", "DATAGOV_", "APD_", "CBE_", "CNT_",
    "WALLEX_", "BRUXELLES_", "FISCONET_", "KULEUVEN_", "HUDOC_", "GALLILEX_",
)

stamp = datetime.now().strftime("%Y%m%d_%H%M")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"index_v2_{stamp}.log", encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
    ],
)
log = logging.getLogger("index_v2")


def hr(n: int) -> str:
    return f"{n:,}".replace(",", "\u00a0")


def main():
    import chromadb
    from sentence_transformers import SentenceTransformer
    from rag.indexer import (
        chunk_text,
        CHUNK_SIZE, CHUNK_SIZE_CODE,
        CHUNK_OVERLAP, CHUNK_OVERLAP_CODE,
        MAX_CHUNKS_PER_DOC_DEFAULT, MAX_CHUNKS_PER_DOC_CODE,
        SOURCES_CODES, EMBED_MODEL,
    )
    import json

    log.info("=" * 60)
    log.info(f"INDEXATION CONFORMES → {NEW_COLLECTION}")
    log.info("=" * 60)

    # 1) Filtrer fichiers conformes
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    files = sorted([
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ])
    log.info(f"Conformes à indexer: {hr(len(files))}")

    # 2) Connexion ChromaDB + nouvelle collection
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing_cols = [c.name for c in client.list_collections()]
    log.info(f"Collections existantes: {existing_cols}")

    collection = client.get_or_create_collection(
        name=NEW_COLLECTION,
        metadata={
            "hnsw:space": "cosine",
            "hnsw:M": 8,
            "hnsw:construction_ef": 64,
            "hnsw:search_ef": 32,
            "hnsw:batch_size": 1000,
        },
    )
    initial = collection.count()
    log.info(f"Chunks dans {NEW_COLLECTION}: {hr(initial)}")

    # Skip rapide par doc_id
    existing_doc_ids = set()
    if initial > 0:
        log.info("Chargement doc_ids déjà indexés (skip rapide)...")
        offset = 0
        while True:
            res = collection.get(limit=5000, offset=offset, include=["metadatas"])
            metas = res.get("metadatas") or []
            if not metas:
                break
            for m in metas:
                existing_doc_ids.add(m.get("doc_id", ""))
            offset += len(metas)
            if len(metas) < 5000:
                break
        log.info(f"  {hr(len(existing_doc_ids))} doc_ids existants")

    # 3) Embedding model
    log.info(f"Chargement modèle: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    # 4) Indexer en batch
    BATCH = 1000
    total_chunks = 0
    batch_docs, batch_ids, batch_metas = [], [], []
    t0 = time.time()

    for i, jf in enumerate(files):
        try:
            doc = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"  Erreur {jf.name}: {e}")
            continue

        doc_id   = doc.get("doc_id", jf.stem)
        text     = doc.get("full_text", "") or doc.get("title", "")
        title    = doc.get("title", "")
        source   = doc.get("source", "")
        date     = doc.get("date", "")
        url      = doc.get("url", "")
        ecli     = doc.get("ecli", "")
        doc_type = doc.get("doc_type", "")
        jurisdiction = doc.get("jurisdiction", "")

        if not text or doc_id in existing_doc_ids:
            continue

        enriched = f"{title}\n\n{text}" if title and title not in text[:200] else text

        is_code = (
            source in SOURCES_CODES
            or "coordonné" in doc_type.lower()
            or title.lower().startswith(("code ", "nouveau code ", "loi ", "arrêté ", "décret ", "constitution"))
        )
        if is_code:
            cs, co, mc = CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE
        else:
            cs, co, mc = CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT

        chunks = chunk_text(enriched, chunk_size=cs, overlap=co)[:mc]
        if not chunks:
            continue

        for j, chunk in enumerate(chunks):
            chunk_id = f"{jf.stem}__chunk_{j:03d}"
            batch_docs.append(chunk)
            batch_ids.append(chunk_id)
            batch_metas.append({
                "doc_id":     doc_id,
                "source":     source,
                "doc_type":   doc_type,
                "jurisdiction": jurisdiction,
                "title":      title[:200],
                "date":       date,
                "url":        url[:500],
                "ecli":       ecli,
                "chunk_idx":  j,
                "chunk_count": len(chunks),
            })

            if len(batch_docs) >= BATCH:
                embs = model.encode(batch_docs, batch_size=128, show_progress_bar=False).tolist()
                collection.add(documents=batch_docs, embeddings=embs, ids=batch_ids, metadatas=batch_metas)
                total_chunks += len(batch_docs)
                rate = total_chunks / (time.time() - t0)
                log.info(f"  [{i+1}/{hr(len(files))}] +{len(batch_docs)} chunks (total: {hr(total_chunks)}) — {rate:.0f}/s")
                batch_docs, batch_ids, batch_metas = [], [], []

    if batch_docs:
        embs = model.encode(batch_docs, batch_size=128, show_progress_bar=False).tolist()
        collection.add(documents=batch_docs, embeddings=embs, ids=batch_ids, metadatas=batch_metas)
        total_chunks += len(batch_docs)

    elapsed = time.time() - t0
    final = collection.count()
    log.info(
        f"\nINDEXATION TERMINÉE en {timedelta(seconds=int(elapsed))}\n"
        f"  Nouveaux chunks : {hr(total_chunks)}\n"
        f"  Total {NEW_COLLECTION}: {hr(final)}"
    )


if __name__ == "__main__":
    main()
