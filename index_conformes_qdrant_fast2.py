"""
Indexation Qdrant CONFORMES — FastEmbed + multi-thread I/O.

Architecture producteur-consommateur :
- 4 threads READER  : lisent JSON + chunking + skip → file (queue bornée)
- 1 thread MAIN     : récupère batches, embed FastEmbed, upsert Qdrant

Embeddings IDENTIQUES à sentence-transformers (cosine 0.999999, vérifié).

Respect CLAUDE.md :
- §1 Plan / §4 Tester / §1 projet zéro invention / §2 droit belge /
  §6 retriever non touché / §8 vérifier 2× minimum
"""
import json
import logging
import os
import sys
import time
import uuid
import threading
import queue
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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
EMBED_MODEL     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

NUM_READERS     = 4              # threads lecture I/O
QUEUE_SIZE      = 64             # max items en attente (bound RAM)
EMBED_BATCH     = 256            # chunks par embed call

CONFORME_PREFIXES = (
    "CONSEIL_ETAT_", "CCE_", "CODEX_VL_", "CONSCONST_", "CHAMBRE_",
    "FSMA_", "CCREK_", "DATAGOV_", "APD_", "CBE_", "CNT_",
    "WALLEX_", "BRUXELLES_", "FISCONET_", "KULEUVEN_", "HUDOC_", "GALLILEX_",
)

CHUNK_SIZE          = 512
CHUNK_SIZE_CODE     = 1500
CHUNK_OVERLAP       = 64
CHUNK_OVERLAP_CODE  = 200
MAX_CHUNKS_PER_DOC_DEFAULT = 20
MAX_CHUNKS_PER_DOC_CODE    = 2000
SOURCES_CODES = {"JUSTEL", "Codex Vlaanderen", "GalliLex", "WalLex", "ETAAMB",
                 "SPF Finances", "SPF Emploi", "Bruxelles"}


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


def read_and_chunk_one(jf: Path, existing: frozenset) -> list:
    """Worker I/O — lit 1 JSON, retourne liste (chunk, payload) ou []."""
    try:
        doc = json.loads(jf.read_text(encoding="utf-8"))
    except Exception:
        return []

    doc_id   = doc.get("doc_id", jf.stem)
    text     = doc.get("full_text", "") or doc.get("title", "")
    title    = doc.get("title", "")
    source   = doc.get("source", "")
    date     = doc.get("date", "")
    url      = doc.get("url", "")
    ecli     = doc.get("ecli", "")
    doc_type = doc.get("doc_type", "")
    jurisdiction = doc.get("jurisdiction", "")

    if not text:
        return []
    if doc_id in existing:
        return [("__SKIP__",)]

    enriched = f"{title}\n\n{text}" if title and title not in text[:200] else text

    is_code = (
        source in SOURCES_CODES
        or "coordonné" in doc_type.lower()
        or title.lower().startswith(("code ", "nouveau code ", "loi ", "arrêté ", "décret ", "constitution"))
    )
    cs, co, mc = (CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE) if is_code else (CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT)
    chunks = chunk_text(enriched, cs, co)[:mc]
    if not chunks:
        return []

    out = []
    for j, chunk in enumerate(chunks):
        chunk_id = f"{jf.stem}__chunk_{j:03d}"
        out.append((chunk, {
            "id": chunk_id_to_uuid(chunk_id),
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
        }))
    return out


def reader_worker(file_q: queue.Queue, chunk_q: queue.Queue, existing: frozenset, stop_event: threading.Event):
    """Lit fichiers de file_q, met chunks dans chunk_q."""
    while not stop_event.is_set():
        try:
            jf = file_q.get(timeout=1)
        except queue.Empty:
            continue
        if jf is None:
            file_q.task_done()
            break
        try:
            results = read_and_chunk_one(jf, existing)
            for r in results:
                chunk_q.put(r)
        except Exception as e:
            logging.warning(f"reader err {jf.name}: {e}")
        file_q.task_done()


def verify_indexation(client, log) -> bool:
    from fastembed import TextEmbedding
    log.info("=" * 60)
    log.info("VÉRIFICATION FINALE")
    log.info("=" * 60)

    final_count = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"  Check 1 — Points: {hr(final_count)}")
    if final_count == 0:
        return False

    info = client.get_collection(COLLECTION_NAME)
    dim = info.config.params.vectors.size
    dist = info.config.params.vectors.distance
    log.info(f"  Check 2 — Config: dim={dim}, distance={dist}")
    if dim != VECTOR_DIM:
        return False

    fe = TextEmbedding(model_name=EMBED_MODEL)
    query = "licenciement préavis indemnité"
    qvec = list(fe.embed([query]))[0].tolist()
    _qr = client.query_points(collection_name=COLLECTION_NAME, query=qvec, limit=3)
    results = _qr.points
    log.info(f"  Check 3 — Search '{query}': {len(results)} hits")
    for r in results:
        title = (r.payload or {}).get("title", "")[:80]
        src   = (r.payload or {}).get("source", "")
        log.info(f"    score={r.score:.3f} [{src}] {title}")
    return len(results) > 0


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from fastembed import TextEmbedding

    log_file = LOG_DIR / f"index_fast2_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )
    log = logging.getLogger("fast2")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("=" * 60)
    log.info("INDEXATION FAST2 — FastEmbed + multi-thread I/O")
    log.info("=" * 60)

    # 1) Filtrer fichiers conformes
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    files = sorted([
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ])
    log.info(f"Conformes: {hr(len(files))}")

    # 2) Qdrant
    client = QdrantClient(url=QDRANT_URL, timeout=180)
    initial = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"Points initial: {hr(initial)}")

    # 3) Charger doc_ids existants
    log.info("Chargement doc_ids existants...")
    existing = set()
    offset = None
    while True:
        res, offset = client.scroll(
            collection_name=COLLECTION_NAME, limit=5000, offset=offset,
            with_payload=["doc_id"], with_vectors=False,
        )
        for p in res:
            did = (p.payload or {}).get("doc_id")
            if did:
                existing.add(did)
        if offset is None:
            break
    log.info(f"  {hr(len(existing))} doc_ids déjà indexés")
    existing_frozen = frozenset(existing)
    del existing

    # 4) FastEmbed
    log.info(f"Chargement FastEmbed: {EMBED_MODEL}")
    fe = TextEmbedding(model_name=EMBED_MODEL, threads=8)
    log.info("  modèle prêt")

    # 5) Threads I/O
    file_q  = queue.Queue()
    chunk_q = queue.Queue(maxsize=QUEUE_SIZE * EMBED_BATCH)
    stop_event = threading.Event()

    for jf in files:
        file_q.put(jf)
    for _ in range(NUM_READERS):
        file_q.put(None)  # sentinel par thread

    readers = []
    for w in range(NUM_READERS):
        t = threading.Thread(target=reader_worker,
                              args=(file_q, chunk_q, existing_frozen, stop_event),
                              daemon=True)
        t.start()
        readers.append(t)
    log.info(f"  {NUM_READERS} threads I/O lancés")

    # 6) Boucle principale : embed + upsert
    total_chunks = 0
    total_skipped = 0
    batch_texts, batch_payloads = [], []
    t0 = time.time()
    last_log = t0

    def flush():
        nonlocal total_chunks
        if not batch_texts:
            return
        embs = list(fe.embed(batch_texts, batch_size=EMBED_BATCH))
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

    finished_readers = 0
    while finished_readers < NUM_READERS:
        try:
            item = chunk_q.get(timeout=5)
        except queue.Empty:
            # check si readers finis
            alive = sum(1 for r in readers if r.is_alive())
            if alive == 0:
                # vider queue restante
                while not chunk_q.empty():
                    try:
                        item = chunk_q.get_nowait()
                        if isinstance(item, tuple) and len(item) >= 2:
                            batch_texts.append(item[0])
                            batch_payloads.append(item[1])
                    except queue.Empty:
                        break
                break
            continue

        if isinstance(item, tuple) and len(item) == 1 and item[0] == "__SKIP__":
            total_skipped += 1
        else:
            batch_texts.append(item[0])
            batch_payloads.append(item[1])

        if len(batch_texts) >= EMBED_BATCH:
            flush()
            if time.time() - last_log > 15:
                rate = total_chunks / (time.time() - t0)
                log.info(f"  {hr(total_chunks)} chunks (skip: {hr(total_skipped)}, q={chunk_q.qsize()}) — {rate:.0f} chunks/s")
                last_log = time.time()

    # Flush final
    flush()
    for r in readers:
        r.join(timeout=5)

    elapsed = time.time() - t0
    log.info(f"\nIndexation FAST2 terminée en {timedelta(seconds=int(elapsed))}")
    log.info(f"  Nouveaux chunks: {hr(total_chunks)}")
    log.info(f"  Docs skip      : {hr(total_skipped)}")

    ok = verify_indexation(client, log)
    final = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(
        f"\n=== BILAN ===\n"
        f"  Points avant : {hr(initial)}\n"
        f"  Points après : {hr(final)}\n"
        f"  Nouveaux     : {hr(final - initial)}\n"
        f"  Statut       : {'✓ SUCCESS' if ok else '✗ FAIL'}"
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
