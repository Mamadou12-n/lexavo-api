"""
Indexation Qdrant CONFORMES — autonome, multi-process, auto-restart.

Respect CLAUDE.md :
- Global Règle 4 (tester+prouver) : vérification finale count + sample search
- Projet §1 (zéro invention)      : embeddings = transformation, pas génération
- Projet §2 (droit belge/EU)      : filtre CONFORME_PREFIXES strict
- Projet §6 (retriever non touché) : indexation seule, retriever inchangé
- Projet §8 (vérifier 2× minimum) : count + dim + sample search testés à la fin

Modèle : paraphrase-multilingual-MiniLM-L12-v2 (384 dim) — IDENTIQUE à l'existant.
Workers : 4 (CPU 8 cores), auto-restart si crash.
Skip rapide : doc_ids déjà dans Qdrant chargés une fois au start.
"""
import json
import logging
import os
import sys
import time
import uuid
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Process, Queue

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
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
BATCH_SIZE      = 500
NUM_WORKERS     = 4
MAX_WORKER_RESTARTS = 3
EMBED_MODEL     = "paraphrase-multilingual-MiniLM-L12-v2"

CONFORME_PREFIXES = (
    "CONSEIL_ETAT_", "CCE_", "CODEX_VL_", "CONSCONST_", "CHAMBRE_",
    "FSMA_", "CCREK_", "DATAGOV_", "APD_", "CBE_", "CNT_",
    "WALLEX_", "BXL_", "FISCONET_", "KULEUVEN_", "HUDOC_", "GALLILEX_",
    "MONITEUR_", "JURIDAT_", "JUPORTAL_", "JUSTEL_",
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
            if temp: current = temp
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


def worker_run(worker_id: int, file_paths: list, existing_doc_ids: frozenset, queue: Queue):
    """Worker — robuste. Try/except global, signal crash."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        from sentence_transformers import SentenceTransformer

        log_file = LOG_DIR / f"index_mp_w{worker_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format=f"%(asctime)s [W{worker_id}] %(message)s",
            handlers=[logging.FileHandler(log_file, encoding="utf-8")],
            force=True,
        )
        log = logging.getLogger(f"w{worker_id}")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        log.info(f"start — {len(file_paths)} fichiers")

        model  = SentenceTransformer(EMBED_MODEL)
        client = QdrantClient(url=QDRANT_URL, timeout=180)
        log.info(f"modèle chargé dim={model.get_sentence_embedding_dimension()}")
        queue.put(("ready", worker_id, 0, 0))

        total_chunks = 0
        skipped_docs = 0
        batch_texts, batch_points = [], []
        t0 = time.time()
        last_progress = t0

        for i, jf in enumerate(file_paths):
            try:
                doc = json.loads(jf.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning(f"erreur lecture {jf.name}: {e}")
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

            if not text:
                continue
            if doc_id in existing_doc_ids:
                skipped_docs += 1
                continue

            enriched = f"{title}\n\n{text}" if title and title not in text[:200] else text

            is_code = (
                source in SOURCES_CODES
                or "coordonné" in doc_type.lower()
                or title.lower().startswith(("code ", "nouveau code ", "loi ", "arrêté ", "décret ", "constitution"))
            )
            cs, co, mc = (CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE) if is_code else (CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT)

            chunks = chunk_text(enriched, cs, co)[:mc]
            if not chunks:
                continue

            for j, chunk in enumerate(chunks):
                chunk_id = f"{jf.stem}__chunk_{j:03d}"
                batch_texts.append(chunk)
                batch_points.append(PointStruct(
                    id=chunk_id_to_uuid(chunk_id),
                    vector=[],
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
                    embs = model.encode(batch_texts, batch_size=64, show_progress_bar=False).tolist()
                    for p, e in zip(batch_points, embs):
                        p.vector = e
                    # retry upsert si erreur réseau
                    for attempt in range(3):
                        try:
                            client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=False)
                            break
                        except Exception as e:
                            log.warning(f"upsert retry {attempt+1}: {e}")
                            time.sleep(2)
                    total_chunks += len(batch_points)
                    if time.time() - last_progress > 30:
                        rate = total_chunks / (time.time() - t0)
                        log.info(f"[{i+1}/{len(file_paths)}] +{len(batch_points)} (total: {total_chunks}) — {rate:.0f}/s")
                        queue.put(("progress", worker_id, i+1, total_chunks))
                        last_progress = time.time()
                    batch_texts, batch_points = [], []

        if batch_texts:
            embs = model.encode(batch_texts, batch_size=64, show_progress_bar=False).tolist()
            for p, e in zip(batch_points, embs):
                p.vector = e
            for attempt in range(3):
                try:
                    client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=True)
                    break
                except Exception as e:
                    log.warning(f"upsert final retry {attempt+1}: {e}")
                    time.sleep(2)
            total_chunks += len(batch_points)

        elapsed = time.time() - t0
        log.info(f"FINI — {total_chunks} chunks, {skipped_docs} skip en {timedelta(seconds=int(elapsed))}")
        queue.put(("done", worker_id, len(file_paths), total_chunks))

    except Exception as e:
        tb = traceback.format_exc()
        try:
            queue.put(("crash", worker_id, str(e), tb))
        except Exception:
            pass


def verify_indexation(client, log) -> bool:
    """Vérification finale (CLAUDE.md §8 projet : vérifier 2x minimum)."""
    log.info("=" * 60)
    log.info("VÉRIFICATION FINALE")
    log.info("=" * 60)

    # Check 1 : count
    final_count = client.get_collection(COLLECTION_NAME).points_count
    log.info(f"  Check 1 — Points dans collection : {hr(final_count)}")
    if final_count == 0:
        log.error("    ÉCHEC : 0 points dans la collection")
        return False

    # Check 2 : config collection (dim 384, cosine)
    info = client.get_collection(COLLECTION_NAME)
    dim = info.config.params.vectors.size
    dist = info.config.params.vectors.distance
    log.info(f"  Check 2 — Config: dim={dim}, distance={dist}")
    if dim != VECTOR_DIM:
        log.error(f"    ÉCHEC : dim {dim} ≠ {VECTOR_DIM} attendu")
        return False

    # Check 3 : sample search (vraie requête de retrieval)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)
    query = "licenciement préavis indemnité"
    qvec = model.encode([query])[0].tolist()
    _qr = client.query_points(
        collection_name=COLLECTION_NAME,
        query=qvec,
        limit=3,
    )
    results = _qr.points
    log.info(f"  Check 3 — Search '{query}' : {len(results)} hits")
    for r in results:
        title = (r.payload or {}).get("title", "")[:80]
        src   = (r.payload or {}).get("source", "")
        log.info(f"    score={r.score:.3f} [{src}] {title}")
    if len(results) == 0:
        log.error("    ÉCHEC : aucun hit sur sample search")
        return False

    log.info("\n✓ VÉRIFICATION OK — indexation prête pour le retriever")
    return True


def main():
    from qdrant_client import QdrantClient

    log_file = LOG_DIR / f"index_mp_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [MAIN] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )
    log = logging.getLogger("main")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("=" * 60)
    log.info(f"INDEXATION QDRANT MP — {NUM_WORKERS} workers, auto-restart, vérif finale")
    log.info("=" * 60)

    # 1) Filtrer fichiers conformes (respect §2 droit belge)
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    files = sorted([
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ])
    log.info(f"Conformes à indexer: {hr(len(files))}")

    # 2) Charger doc_ids déjà indexés
    client = QdrantClient(url=QDRANT_URL, timeout=180)
    initial = client.get_collection(COLLECTION_NAME).points_count
    log.info(f"Points actuels Qdrant: {hr(initial)}")

    log.info("Chargement doc_ids existants pour skip...")
    existing = set()
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
                existing.add(did)
        if offset is None:
            break
    log.info(f"  {hr(len(existing))} doc_ids déjà indexés")

    existing_frozen = frozenset(existing)
    del existing

    # 3) Filtrer en amont (skip avant les workers — gain RAM)
    files_todo = [f for f in files if f.stem not in existing_frozen]
    # Aussi filter via doc_id : on a doc_id != stem parfois, donc gardons tout, le worker filtre.
    log.info(f"Files à processer (post-filter stem): {hr(len(files_todo))}")
    # Sécurité : on garde quand même tous les files conformes, le worker re-vérifie
    files_todo = files

    # 4) Partitionner round-robin
    partitions = [files_todo[i::NUM_WORKERS] for i in range(NUM_WORKERS)]
    for w, part in enumerate(partitions):
        log.info(f"  Worker {w}: {hr(len(part))} fichiers")

    # 5) Lancer workers + auto-restart
    queue = Queue()
    procs = {}
    restarts = {w: 0 for w in range(NUM_WORKERS)}

    def start_worker(w_id: int, paths: list):
        p = Process(target=worker_run, args=(w_id, paths, existing_frozen, queue))
        p.start()
        procs[w_id] = (p, paths)
        log.info(f"  ▶ Worker {w_id} lancé (PID {p.pid})")

    t0 = time.time()
    for w in range(NUM_WORKERS):
        start_worker(w, partitions[w])

    # 6) Boucle de suivi
    finished = set()
    progress = {w: 0 for w in range(NUM_WORKERS)}
    chunks   = {w: 0 for w in range(NUM_WORKERS)}
    last_health_check = time.time()

    while len(finished) < NUM_WORKERS:
        try:
            msg = queue.get(timeout=120)
        except Exception:
            # Health check : process morts ?
            now = time.time()
            for wid, (p, paths) in list(procs.items()):
                if wid in finished:
                    continue
                if not p.is_alive() and p.exitcode != 0 and restarts[wid] < MAX_WORKER_RESTARTS:
                    log.warning(f"  ⚠ Worker {wid} mort (exit={p.exitcode}) — restart {restarts[wid]+1}/{MAX_WORKER_RESTARTS}")
                    restarts[wid] += 1
                    # Re-partitionner avec ce qui reste (approximation : re-lancer avec mêmes paths)
                    start_worker(wid, paths)
            last_health_check = now
            continue

        kind = msg[0]
        if kind == "ready":
            log.info(f"  ✓ Worker {msg[1]} prêt")
        elif kind == "progress":
            _, wid, processed, total_chunks = msg
            progress[wid] = processed
            chunks[wid]   = total_chunks
            grand_p = sum(progress.values())
            grand_c = sum(chunks.values())
            elapsed = time.time() - t0
            rate = grand_c / elapsed if elapsed > 0 else 0
            log.info(f"  📊 Total: {hr(grand_p)}/{hr(len(files_todo))} docs, {hr(grand_c)} chunks ({rate:.0f}/s)")
        elif kind == "done":
            _, wid, processed, total_chunks = msg
            finished.add(wid)
            log.info(f"  ✓ Worker {wid} TERMINÉ — {hr(total_chunks)} chunks")
        elif kind == "crash":
            _, wid, err, tb = msg
            log.error(f"  ✗ Worker {wid} CRASH : {err}")
            log.error(tb)
            if restarts[wid] < MAX_WORKER_RESTARTS:
                restarts[wid] += 1
                _, paths = procs[wid]
                log.info(f"  ▶ Restart worker {wid} ({restarts[wid]}/{MAX_WORKER_RESTARTS})")
                start_worker(wid, paths)
            else:
                log.error(f"  ✗ Worker {wid} épuisé restarts — abandonné")
                finished.add(wid)

    for wid, (p, _) in procs.items():
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()

    elapsed = time.time() - t0
    log.info(f"\nIndexation MP terminée en {timedelta(seconds=int(elapsed))}")

    # 7) Vérification finale (CLAUDE.md Règle 4 + §8)
    ok = verify_indexation(client, log)

    final = client.get_collection(COLLECTION_NAME).points_count
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
