"""Migration Qdrant local -> VPS via scroll + upsert.

Pas besoin de SSH, scp, rsync. Communique en HTTP REST entre 2 Qdrant.
Idempotent : reprend sans dupliquer (IDs preserves).
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

# === CONFIG ===
LOCAL_URL = "http://localhost:6333"
VPS_URL = "http://46.202.168.185:6333"
VPS_API_KEY = os.environ.get("LEXAVO_VPS_QDRANT_KEY") or sys.argv[1] if len(sys.argv) > 1 else None

if not VPS_API_KEY:
    print("USAGE: LEXAVO_VPS_QDRANT_KEY=xxx python migrate_local_to_vps.py")
    print("   ou: python migrate_local_to_vps.py <api_key>")
    sys.exit(1)

COLLECTIONS = ["legal_docs_be", "legal_articles_be"]
BATCH_SIZE = 1000

# === CONNECTIONS ===
print("Connexion Qdrant local...")
local = QdrantClient(url=LOCAL_URL, timeout=60)
print(f"  OK : {len(local.get_collections().collections)} collections trouvees\n")

print(f"Connexion Qdrant VPS ({VPS_URL})...")
vps = QdrantClient(url=VPS_URL, api_key=VPS_API_KEY, timeout=60)
print(f"  OK : {len(vps.get_collections().collections)} collections existantes\n")


def migrate_collection(name: str) -> None:
    """Migre une collection complete local -> VPS."""
    print(f"=== Migration {name} ===")

    # 1. Recupere config local pour creer la meme sur VPS
    local_info = local.get_collection(name)
    total = local.count(name).count
    vector_size = local_info.config.params.vectors.size
    distance = local_info.config.params.vectors.distance
    print(f"  source: {total:,} points, dim={vector_size}, distance={distance}")

    # 2. Cree la collection sur VPS (recreate = idempotent)
    vps_collections = [c.name for c in vps.get_collections().collections]
    if name in vps_collections:
        existing = vps.count(name).count
        print(f"  collection deja sur VPS avec {existing:,} points")
        if existing >= total:
            print(f"  SKIP : VPS a deja {existing:,} >= {total:,} points")
            return
        print(f"  reprise : {total - existing:,} points manquants")
    else:
        vps.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        print(f"  collection creee sur VPS")

    # 3. Scroll local + upsert VPS par batches
    offset = None
    migrated = 0
    start = time.time()
    errors = 0

    while True:
        try:
            points, next_offset = local.scroll(
                collection_name=name,
                limit=BATCH_SIZE,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
        except Exception as e:
            print(f"\n  ERREUR scroll: {e}")
            errors += 1
            if errors > 5:
                print("  abandon apres 5 erreurs scroll")
                return
            time.sleep(2)
            continue

        if not points:
            break

        # Upsert vers VPS
        vps_points = [
            PointStruct(id=p.id, vector=p.vector, payload=p.payload)
            for p in points
        ]
        try:
            vps.upsert(collection_name=name, points=vps_points, wait=False)
        except Exception as e:
            print(f"\n  ERREUR upsert batch (offset={offset}): {e}")
            errors += 1
            if errors > 10:
                print("  abandon apres 10 erreurs upsert")
                return
            time.sleep(3)
            continue

        migrated += len(points)
        elapsed = time.time() - start
        rate = migrated / elapsed if elapsed > 0 else 0
        eta_sec = (total - migrated) / rate if rate > 0 else 0
        eta_min = eta_sec / 60

        # Progress 1 line ecrasee
        pct = 100 * migrated / total
        bar_len = 30
        filled = int(bar_len * migrated / total)
        bar = "#" * filled + "-" * (bar_len - filled)
        sys.stdout.write(
            f"\r  [{bar}] {pct:5.1f}%  {migrated:>9,}/{total:,}  "
            f"{rate:>5.0f} pts/s  ETA {eta_min:5.1f} min  err={errors}"
        )
        sys.stdout.flush()

        if next_offset is None:
            break
        offset = next_offset

    elapsed = time.time() - start
    print(f"\n  TERMINE : {migrated:,} points en {elapsed/60:.1f} min")

    # Verification finale
    final_count = vps.count(name).count
    print(f"  VPS count final: {final_count:,}")
    if final_count == total:
        print(f"  OK CHECKSUM : local={total:,} == vps={final_count:,}")
    else:
        print(f"  WARN : local={total:,} != vps={final_count:,} (delta={total-final_count:,})")


# === MAIN ===
for col in COLLECTIONS:
    migrate_collection(col)
    print()

print("=== Migration TERMINEE ===")
print(f"VPS Qdrant : {VPS_URL}")
print("Collections migrees :")
for col in COLLECTIONS:
    cnt = vps.count(col).count
    print(f"  {col}: {cnt:,} points")
