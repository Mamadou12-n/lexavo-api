"""
Indexation Qdrant des 477 fichiers JUSTEL (codes belges fédéraux).
Cible : remplacer ChromaDB cassé (RAM crash) par Qdrant unifié.

Single-process suffit (477 docs seulement, pas besoin MP).
Skip existing_doc_ids ÉVITÉ : aucun JUSTEL_ n'est encore dans Qdrant.

Respect CLAUDE.md :
- §1 zéro invention   : full_text JUSTEL = sources officielles ejustice.just.fgov.be
- §2 droit belge      : JUSTEL = SPF Justice fédéral
- §6 retriever        : non touché ici
- §8 vérifier 2×      : count + sample search final
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
os.environ["TOKENIZERS_PARALLELISM"] = "false"

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
from config import OUTPUT_DIR

NORMALIZED_DIR = OUTPUT_DIR / "normalized"
LOG_DIR        = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

QDRANT_URL      = "http://localhost:6333"
COLLECTION_NAME = "legal_docs_be"
VECTOR_DIM      = 384
BATCH_SIZE      = 256
EMBED_MODEL     = "paraphrase-multilingual-MiniLM-L12-v2"

# Codes JUSTEL = textes coordonnés longs → grands chunks
CHUNK_SIZE         = 1500
CHUNK_OVERLAP      = 200
MAX_CHUNKS_PER_DOC = 5000  # codes très longs (Code judiciaire ~1.5M chars)


def hr(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current.strip()); current = ""
            words = para.split(); temp = ""
            for word in words:
                if len(temp) + len(word) + 1 > chunk_size:
                    if temp:
                        chunks.append(temp.strip())
                    temp = current[-overlap:] + word + " " if current else word + " "
                    current = ""
                else:
                    temp += word + " "
            if temp:
                current = temp
        else:
            if len(current) + len(para) + 2 > chunk_size:
                if current:
                    chunks.append(current.strip())
                    current = current[-overlap:] + "\n\n" + para
                else:
                    current = para
            else:
                current += ("\n\n" if current else "") + para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) >= 50]


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from sentence_transformers import SentenceTransformer

    log_file = LOG_DIR / f"index_justel_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )
    log = logging.getLogger("justel")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("=" * 60)
    log.info("INDEXATION JUSTEL — codes belges fédéraux")
    log.info("=" * 60)

    # 1) Files
    files = sorted(NORMALIZED_DIR.glob("JUSTEL_*.json"))
    log.info(f"JUSTEL files: {hr(len(files))}")

    # 2) Qdrant
    client = QdrantClient(url=QDRANT_URL, timeout=180)
    initial = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"Points initial Qdrant: {hr(initial)}")

    # 2bis) Skip rapide : test existence du 1er chunk de chaque doc (point lookup)
    from qdrant_client.models import PointIdsList
    log.info("Skip rapide : test existence par chunk_id (point lookup)...")
    existing_justel = set()
    skip_check_files = sorted(NORMALIZED_DIR.glob("JUSTEL_*.json"))
    test_ids = []
    file_to_doc = {}
    for jf in skip_check_files:
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
            doc_id = d.get("doc_id", jf.stem)
            if not doc_id.upper().startswith("JUSTEL_"):
                doc_id = f"JUSTEL_{doc_id}"
            first_chunk_uuid = chunk_id_to_uuid(f"{doc_id}__chunk_0000")
            test_ids.append(first_chunk_uuid)
            file_to_doc[first_chunk_uuid] = doc_id
        except Exception:
            continue
    # Lookup en batch (rapide, indexé par UUID)
    BATCH_LOOKUP = 100
    for i in range(0, len(test_ids), BATCH_LOOKUP):
        batch = test_ids[i:i+BATCH_LOOKUP]
        try:
            res = client.retrieve(collection_name=COLLECTION_NAME, ids=batch, with_payload=False, with_vectors=False)
            for p in res:
                did = file_to_doc.get(str(p.id))
                if did:
                    existing_justel.add(did)
        except Exception as e:
            log.warning(f"  Skip lookup batch {i} erreur: {e}")
    log.info(f"  {hr(len(existing_justel))} doc_ids JUSTEL_ déjà indexés (skip)")

    # 3) Modèle
    log.info(f"Chargement modèle: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    log.info("  modèle prêt")

    # 4) Indexation
    total_chunks = 0
    total_docs = 0
    batch_texts, batch_payloads = [], []
    t0 = time.time()
    last_log = t0

    def flush():
        nonlocal total_chunks
        if not batch_texts:
            return
        embs = model.encode(batch_texts, batch_size=64, show_progress_bar=False)
        points = [
            PointStruct(id=p["id"], vector=e.tolist(), payload={k: v for k, v in p.items() if k != "id"})
            for p, e in zip(batch_payloads, embs)
        ]
        for attempt in range(3):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points, wait=False)
                break
            except Exception as e:
                log.warning(f"upsert retry {attempt+1}: {e}")
                time.sleep(2)
        total_chunks += len(points)
        batch_texts.clear()
        batch_payloads.clear()

    for i, jf in enumerate(files):
        try:
            doc = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"  Erreur {jf.name}: {e}")
            continue

        doc_id   = doc.get("doc_id", jf.stem)
        text     = doc.get("full_text", "") or doc.get("title", "")
        title    = doc.get("title", "")
        source   = doc.get("source", "JUSTEL") or "JUSTEL"
        date     = doc.get("date", "")
        url      = doc.get("url", "")
        doc_type = doc.get("doc_type", "")
        jurisdiction = doc.get("jurisdiction", "Fédéral") or "Fédéral"

        if not text:
            continue

        # Force préfixe JUSTEL_
        if not doc_id.upper().startswith("JUSTEL_"):
            doc_id = f"JUSTEL_{doc_id}"

        # Skip si déjà indexé
        if doc_id in existing_justel:
            continue

        enriched = f"{title}\n\n{text}" if title and title not in text[:200] else text
        chunks = chunk_text(enriched, CHUNK_SIZE, CHUNK_OVERLAP)[:MAX_CHUNKS_PER_DOC]
        if not chunks:
            continue

        total_docs += 1
        for j, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}__chunk_{j:04d}"
            batch_texts.append(chunk)
            batch_payloads.append({
                "id":           chunk_id_to_uuid(chunk_id),
                "doc_id":       doc_id,
                "chunk_id":     chunk_id,
                "source":       source,
                "doc_type":     doc_type,
                "jurisdiction": jurisdiction,
                "title":        title[:200],
                "date":         date,
                "url":          url[:500],
                "ecli":         "",
                "chunk_idx":    j,
                "chunk_count":  len(chunks),
                "text":         chunk,
            })

            if len(batch_texts) >= BATCH_SIZE:
                flush()
                if time.time() - last_log > 15:
                    rate = total_chunks / (time.time() - t0)
                    log.info(f"  [{i+1}/{len(files)}] {hr(total_chunks)} chunks ({rate:.0f}/s)")
                    last_log = time.time()

    flush()

    elapsed = time.time() - t0
    final = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info("")
    log.info("=" * 60)
    log.info(f"INDEXATION JUSTEL TERMINÉE en {timedelta(seconds=int(elapsed))}")
    log.info("=" * 60)
    log.info(f"  Docs traités       : {hr(total_docs)} / {hr(len(files))}")
    log.info(f"  Chunks indexés     : {hr(total_chunks)}")
    log.info(f"  Points avant       : {hr(initial)}")
    log.info(f"  Points après       : {hr(final)}")
    log.info(f"  Delta              : {hr(final - initial)}")

    # Vérification : sample search code civil
    log.info("")
    log.info("VÉRIFICATION (sample search 'article 1382 code civil')")
    qvec = model.encode(["article 1382 code civil responsabilité civile"])[0].tolist()
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=qvec,
        limit=3,
    ).points
    log.info(f"  {len(results)} hits")
    for r in results:
        pl = r.payload or {}
        log.info(f"    score={r.score:.3f} [{pl.get('source', '')}] {pl.get('title', '')[:60]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
