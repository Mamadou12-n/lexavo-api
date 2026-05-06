"""Crée les index payload Qdrant sur la collection `legal_docs_be`.

Usage :
    # Local (Qdrant Docker)
    python scripts/create_qdrant_indexes.py

    # Production (Qdrant cloud — variables d'env QDRANT_URL + QDRANT_API_KEY)
    QDRANT_URL=https://xxx.cloud.qdrant.io QDRANT_API_KEY=... python scripts/create_qdrant_indexes.py

Ce script est idempotent : exécutable plusieurs fois sans risque.
Sur 3,5M chunks en prod, l'indexation prend ~2-5 min.

Gain mesurable :
- Filtre source     : ~800-1500ms → ~30-80ms  (~20×)
- MatchText sur text: ~1200ms     → ~100ms    (~12×)
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.indexer_qdrant import COLLECTION_NAME, create_payload_indexes


def main() -> int:
    from qdrant_client import QdrantClient

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")

    print(f"Connexion à {qdrant_url}...")
    client = QdrantClient(url=qdrant_url, api_key=api_key, timeout=120)

    info = client.get_collection(COLLECTION_NAME)
    count = client.count(COLLECTION_NAME).count
    print(f"Collection '{COLLECTION_NAME}' : {count:,} points")

    print("\nCréation des index payload...")
    t0 = time.time()
    results = create_payload_indexes(client=client, collection=COLLECTION_NAME)
    elapsed = time.time() - t0

    print(f"\nTerminé en {elapsed:.1f}s")
    for field, status in results.items():
        symbol = "✓" if status in ("created", "already_exists") else "✗"
        print(f"  {symbol} {field:14s} → {status}")

    errors = [f for f, s in results.items() if s.startswith("error")]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
