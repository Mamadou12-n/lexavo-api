"""Migration Qdrant local -> VPS, version 3 (CONSERVATIVE).

Apprentissages des essais 1 et 2 :
- 1 worker = trop lent (40 pts/s, 24h)
- 10 workers = sature VPS (Server disconnected, ConnectTimeout)

V3 : 3 workers, batch 200, connection pooling, backoff jitter, sleep entre batches.
Cible : 200-300 pts/s soutenu sans saturer le VPS.

Idempotent : reprend automatiquement.
"""
from __future__ import annotations

import os
import random
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
    print("USAGE: python migrate_local_to_vps_v3.py <api_key>")
    sys.exit(1)

COLLECTIONS = ["legal_docs_be", "legal_articles_be"]
BATCH_SIZE = 200
NUM_WRITERS = 3
QUEUE_MAX = 20
UPSERT_TIMEOUT = 180
SCROLL_TIMEOUT = 60
SLEEP_BETWEEN_BATCH = 0.05
MAX_RETRIES_PER_BATCH = 5
MAX_TOTAL_ABANDONS = 100

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
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()


def worker_writer(worker_id: int, vps_url: str, api_key: str, collection: str) -> None:
    client = QdrantClient(url=vps_url, api_key=api_key, timeout=UPSERT_TIMEOUT)

    while not stop_event.is_set():
        try:
            batch = work_queue.get(timeout=10)
        except queue.Empty:
            if stop_event.is_set():
                break
            continue

        if batch is SENTINEL:
            work_queue.put(SENTINEL)
            break

        success = False
        for attempt in range(MAX_RETRIES_PER_BATCH):
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
                if attempt < MAX_RETRIES_PER_BATCH - 1:
                    sleep_s = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_s)
                    if attempt >= 2:
                        try:
                            client.close()
                        except Exception:
                            pass
                        client = QdrantClient(url=vps_url, api_key=api_key, timeout=UPSERT_TIMEOUT)

        if not success:
            with stats_lock:
                stats["abandoned_batches"] += 1
                if stats["abandoned_batches"] >= MAX_TOTAL_ABANDONS:
                    log(f"  [W{worker_id}] BAIL OUT : {MAX_TOTAL_ABANDONS} batches abandonnes")
                    stop_event.set()

        time.sleep(SLEEP_BETWEEN_BATCH)
        work_queue.task_done()


def reader_scroll(local: QdrantClient, collection: str) -> None:
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
            log(f"  [READER] erreur scroll: {e} (retry 3s)")
            time.sleep(3)
            continue

        if not points:
            break

        with stats_lock:
            stats["scrolled"] += len(points)

        work_queue.put(points)

        if next_offset is None:
            break
        offset = next_offset

    for _ in range(NUM_WRITERS):
        work_queue.put(SENTINEL)


def progress_monitor(total: int, start_count: int) -> None:
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

        if cur >= target or stop_event.is_set():
            break


def migrate_collection(local: QdrantClient, vps: QdrantClient, name: str) -> bool:
    log(f"\n=== Migration {name} ===")

    local_info = local.get_collection(name)
    total = local.count(name).count
    vector_size = local_info.config.params.vectors.size
    distance = local_info.config.params.vectors.distance
    log(f"  source: {total:,} points, dim={vector_size}, distance={distance}")

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

    with stats_lock:
        stats["scrolled"] = 0
        stats["upserted"] = 0
        stats["errors"] = 0
        stats["retries"] = 0
        stats["abandoned_batches"] = 0

    workers = []
    for i in range(NUM_WRITERS):
        t = threading.Thread(
            target=worker_writer,
            args=(i, VPS_URL, VPS_API_KEY, name),
            daemon=True,
        )
        t.start()
        workers.append(t)

    monitor = threading.Thread(
        target=progress_monitor,
        args=(total, start_count),
        daemon=True,
    )
    monitor.start()

    start = time.time()
    reader_scroll(local, name)

    for t in workers:
        t.join(timeout=600)

    elapsed = time.time() - start
    log(f"  TERMINE {name}: {stats['upserted']:,} points en {elapsed/60:.1f} min")

    final_count = vps.count(name).count
    log(f"  VPS final: {final_count:,}")
    if final_count == total:
        log(f"  CHECKSUM OK : local=vps={total:,}")
        return True
    else:
        log(f"  MISMATCH : local={total:,} vps={final_count:,} (delta={total-final_count:,}, abandons={stats['abandoned_batches']})")
        return False


# === MAIN ===
log(f"Migration v3 conservative Qdrant local -> {VPS_URL}")
log(f"Workers: {NUM_WRITERS}, batch_size: {BATCH_SIZE}, sleep_between: {SLEEP_BETWEEN_BATCH}s")
log("")

log("Connexion local...")
local = QdrantClient(url=LOCAL_URL, timeout=SCROLL_TIMEOUT)
log(f"  OK: {len(local.get_collections().collections)} collections")

log(f"Test VPS sante {VPS_URL}/healthz...")
import urllib.request
try:
    with urllib.request.urlopen(f"{VPS_URL}/healthz", timeout=10) as r:
        log(f"  OK: HTTP {r.status}")
except Exception as e:
    log(f"  FAIL : {e}")
    log("  ABORT : VPS Qdrant ne repond pas. Lance 'curl http://46.202.168.185:6333/healthz' pour confirmer.")
    sys.exit(1)

log(f"Connexion VPS...")
vps = QdrantClient(url=VPS_URL, api_key=VPS_API_KEY, timeout=UPSERT_TIMEOUT)
log(f"  OK: {len(vps.get_collections().collections)} collections existantes")

results = {}
for col in COLLECTIONS:
    if stop_event.is_set():
        log(f"  SKIP {col} apres bail out")
        results[col] = False
        continue
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
    try:
        cnt = vps.count(col).count
    except Exception:
        cnt = -1
    status = "OK" if ok else "FAIL"
    log(f"  [{status}] {col}: {cnt:,} points sur VPS")
    if not ok:
        all_ok = False

if all_ok:
    log("\nMIGRATION COMPLETE - tout est sur VPS")
    sys.exit(0)
else:
    log("\nMIGRATION INCOMPLETE - relancer pour rattraper les manquants (idempotent)")
    sys.exit(1)
