"""Migration Qdrant local -> VPS, version PARALLELE.

10 workers concurrent : 1 lecteur (scroll local) qui produit dans une queue,
N writers (upsert VPS) qui consomment.

Idempotent : reprend sur les chunks deja sur VPS, ne dupplique pas.
Auto-retry sur erreurs reseau (3 tentatives par batch).
"""
from __future__ import annotations

import os
import sys
import time
import threading
import queue
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# === CONFIG ===
LOCAL_URL = "http://localhost:6333"
VPS_URL = "http://46.202.168.185:6333"
VPS_API_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LEXAVO_VPS_QDRANT_KEY")

if not VPS_API_KEY:
    print("USAGE: python migrate_local_to_vps_parallel.py <api_key>")
    sys.exit(1)

COLLECTIONS = ["legal_docs_be", "legal_articles_be"]
BATCH_SIZE = 500          # plus petit = retries moins couteux
NUM_WRITERS = 10          # 10 workers parallel sur upsert VPS
QUEUE_MAX = 50            # backpressure : max 50 batches en attente
UPSERT_TIMEOUT = 120      # 2 min par upsert (HNSW peut etre lent)
SCROLL_TIMEOUT = 60       # 1 min par scroll local

# === ETAT GLOBAL ===
stats_lock = threading.Lock()
stats = {
    "scrolled": 0,
    "upserted": 0,
    "errors": 0,
    "retries": 0,
    "abandoned_batches": 0,
}
work_queue: queue.Queue[Any] = queue.Queue(maxsize=QUEUE_MAX)
SENTINEL = object()
stop_event = threading.Event()


def log(msg: str) -> None:
    """Print thread-safe avec flush immediat."""
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()


def worker_writer(worker_id: int, vps_url: str, api_key: str, collection: str) -> None:
    """Worker qui consomme la queue et upsert vers VPS."""
    client = QdrantClient(url=vps_url, api_key=api_key, timeout=UPSERT_TIMEOUT)

    while not stop_event.is_set():
        try:
            batch = work_queue.get(timeout=10)
        except queue.Empty:
            if stop_event.is_set():
                break
            continue

        if batch is SENTINEL:
            work_queue.put(SENTINEL)  # autres workers
            break

        # Upsert avec 3 tentatives
        success = False
        for attempt in range(3):
            try:
                points = [
                    PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                    for p in batch
                ]
                client.upsert(collection_name=collection, points=points, wait=False)
                with stats_lock:
                    stats["upserted"] += len(batch)
                    if attempt > 0:
                        stats["retries"] += 1
                success = True
                break
            except Exception as e:
                with stats_lock:
                    stats["errors"] += 1
                if attempt < 2:
                    time.sleep(2 ** attempt)  # backoff 1s, 2s
                else:
                    log(f"  [W{worker_id}] ABANDON batch ({len(batch)} pts) apres 3 essais: {e}")
                    with stats_lock:
                        stats["abandoned_batches"] += 1

        work_queue.task_done()


def reader_scroll(local: QdrantClient, collection: str, total: int, start_count: int) -> None:
    """Lit le local par batches et alimente la queue."""
    offset = None
    while not stop_event.is_set():
        try:
            points, next_offset = local.scroll(
                collection_name=collection,
                limit=BATCH_SIZE,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
        except Exception as e:
            log(f"  [READER] erreur scroll: {e} (retry dans 3s)")
            time.sleep(3)
            continue

        if not points:
            break

        with stats_lock:
            stats["scrolled"] += len(points)

        # Met dans la queue (block si pleine = backpressure)
        work_queue.put(points)

        if next_offset is None:
            break
        offset = next_offset

    # Signal de fin pour les workers
    for _ in range(NUM_WRITERS):
        work_queue.put(SENTINEL)


def progress_monitor(total: int, start_count: int) -> None:
    """Affiche le progres toutes les 5 sec."""
    start = time.time()
    last_upserted = 0
    last_t = start
    target = total - start_count

    while not stop_event.is_set():
        time.sleep(5)
        with stats_lock:
            cur = stats["upserted"]
            err = stats["errors"]
            ret = stats["retries"]
            ab = stats["abandoned_batches"]

        now = time.time()
        elapsed = now - start
        pct = 100 * cur / target if target > 0 else 100
        instant_rate = (cur - last_upserted) / max(now - last_t, 0.001)
        avg_rate = cur / elapsed if elapsed > 0 else 0
        eta_min = (target - cur) / max(avg_rate, 1) / 60

        bar_len = 30
        filled = int(bar_len * cur / target) if target > 0 else bar_len
        bar = "#" * filled + "-" * (bar_len - filled)

        log(f"  [{bar}] {pct:5.1f}%  {cur:>9,}/{target:,}  inst={instant_rate:.0f} pts/s  avg={avg_rate:.0f} pts/s  ETA {eta_min:5.1f} min  err={err} retry={ret} abandon={ab}")

        last_upserted = cur
        last_t = now

        if cur >= target:
            break


def migrate_collection(local: QdrantClient, vps: QdrantClient, name: str) -> bool:
    """Migre une collection complete avec workers parallel. Retourne True si OK."""
    log(f"\n=== Migration {name} ===")

    # Stats source
    local_info = local.get_collection(name)
    total = local.count(name).count
    vector_size = local_info.config.params.vectors.size
    distance = local_info.config.params.vectors.distance
    log(f"  source: {total:,} points, dim={vector_size}, distance={distance}")

    # Cree collection si absente
    vps_collections = [c.name for c in vps.get_collections().collections]
    if name in vps_collections:
        existing = vps.count(name).count
        log(f"  VPS deja: {existing:,} points")
        if existing >= total:
            log(f"  SKIP : VPS a {existing:,} >= {total:,}")
            return True
        start_count = existing
    else:
        vps.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        log(f"  collection creee sur VPS")
        start_count = 0

    # Reset stats pour cette collection
    with stats_lock:
        stats["scrolled"] = 0
        stats["upserted"] = 0
        stats["errors"] = 0
        stats["retries"] = 0
        stats["abandoned_batches"] = 0

    # Lance workers writers
    workers = []
    for i in range(NUM_WRITERS):
        t = threading.Thread(
            target=worker_writer,
            args=(i, VPS_URL, VPS_API_KEY, name),
            daemon=True,
        )
        t.start()
        workers.append(t)

    # Lance progress monitor
    monitor = threading.Thread(
        target=progress_monitor,
        args=(total, start_count),
        daemon=True,
    )
    monitor.start()

    # Reader (bloquant dans le main thread)
    start = time.time()
    reader_scroll(local, name, total, start_count)

    # Attend que tous les workers finissent
    for t in workers:
        t.join(timeout=300)

    elapsed = time.time() - start
    log(f"  TERMINE {name}: {stats['upserted']:,} points en {elapsed/60:.1f} min")

    # Verification finale
    final_count = vps.count(name).count
    log(f"  VPS final: {final_count:,}")
    if final_count == total:
        log(f"  ✅ CHECKSUM OK : local=vps={total:,}")
        return True
    else:
        log(f"  ⚠ MISMATCH : local={total:,} vps={final_count:,} (delta={total-final_count:,}, abandons={stats['abandoned_batches']})")
        return False


# === MAIN ===
log(f"Migration parallele Qdrant local -> {VPS_URL}")
log(f"Workers: {NUM_WRITERS}, batch_size: {BATCH_SIZE}")
log("")

log("Connexion local...")
local = QdrantClient(url=LOCAL_URL, timeout=SCROLL_TIMEOUT)
log(f"  OK: {len(local.get_collections().collections)} collections")

log(f"Connexion VPS {VPS_URL}...")
vps = QdrantClient(url=VPS_URL, api_key=VPS_API_KEY, timeout=UPSERT_TIMEOUT)
log(f"  OK: {len(vps.get_collections().collections)} collections existantes")

results = {}
for col in COLLECTIONS:
    try:
        results[col] = migrate_collection(local, vps, col)
    except Exception as e:
        log(f"\n  CRASH migration {col}: {e}")
        import traceback
        traceback.print_exc()
        results[col] = False

log("\n=== RAPPORT FINAL ===")
all_ok = True
for col, ok in results.items():
    cnt = vps.count(col).count
    status = "✅" if ok else "❌"
    log(f"  {status} {col}: {cnt:,} points sur VPS")
    if not ok:
        all_ok = False

if all_ok:
    log("\n✅ MIGRATION COMPLETE - tout est sur VPS")
    sys.exit(0)
else:
    log("\n⚠ MIGRATION INCOMPLETE - relancer pour rattraper les manquants (idempotent)")
    sys.exit(1)
