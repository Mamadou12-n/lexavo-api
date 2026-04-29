"""
Index articles séparé pour Alt.8 du retriever
==============================================

Crée la collection Qdrant `legal_articles_be` avec un point par article.
- Source : JUSTEL_*.json + CONSCONST_*.json normalisés
- Extraction articles via regex sur full_text
- Payload : article_num, text, title, source, doc_id, code_name

CLAUDE.md compliance :
- §1 zéro invention : extraction texte intégral des sources officielles
- §6 retriever 9 alternatives : Alt.8 (collection séparée articles)
- Règle 4 : test final sur "article 1134 code civil"
"""

import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import json
import logging
import re
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("idx-articles")

# ─── Configuration ───────────────────────────────────────────────────────
NORMALIZED_DIR = Path("output/normalized")
COLLECTION_ARTICLES = os.getenv("QDRANT_ARTICLES_COLLECTION", "legal_articles_be")
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

# Sources avec articles structurés (codes belges)
ARTICLE_SOURCES = ("JUSTEL_", "CONSCONST_")

# Regex extraction : Art. <num> [point|deux-points] <texte> jusqu'à prochain Art.
# Numéros : "1", "1bis", "1234", "23/2", "L.123", "1.2"
ART_PATTERN = re.compile(
    r"Art(?:icle)?\.?\s+([0-9]+(?:[a-zA-Z]+)?(?:[\.\-/][0-9a-zA-Z]+)*)\s*[\.\:\-]?\s*",
    re.IGNORECASE,
)

# Limite par article (pour éviter de chunker — 1 article = 1 point)
MAX_ARTICLE_CHARS = 3000
MIN_ARTICLE_CHARS = 50


def extract_articles(full_text: str) -> List[Tuple[str, str]]:
    """Extrait (article_num, article_text) depuis full_text."""
    matches = list(ART_PATTERN.finditer(full_text))
    articles = []
    for i, m in enumerate(matches):
        art_num = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        if MIN_ARTICLE_CHARS <= len(text) <= MAX_ARTICLE_CHARS * 2:
            articles.append((art_num, text[:MAX_ARTICLE_CHARS]))
    return articles


def chunk_id_to_uuid(chunk_id: str) -> str:
    """UUID5 stable pour idempotence."""
    return str(uuid.uuid5(uuid.NAMESPACE_OID, chunk_id))


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, PayloadSchemaType,
    )
    from sentence_transformers import SentenceTransformer

    log.info("=" * 60)
    log.info("INDEX ARTICLES — Alt.8 du retriever")
    log.info("=" * 60)

    # 1) Connexion Qdrant
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)

    # 2) Créer / vider la collection articles
    if client.collection_exists(COLLECTION_ARTICLES):
        log.info(f"Collection '{COLLECTION_ARTICLES}' existe déjà, info :")
        info = client.get_collection(COLLECTION_ARTICLES)
        log.info(f"  Points actuels : {info.points_count}")
        log.info("Mode : append (skip via UUID5)")
    else:
        log.info(f"Création collection '{COLLECTION_ARTICLES}'...")
        client.create_collection(
            collection_name=COLLECTION_ARTICLES,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        # Index payload sur article_num pour les filtres rapides
        client.create_payload_index(
            collection_name=COLLECTION_ARTICLES,
            field_name="article_num",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=COLLECTION_ARTICLES,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        log.info(f"  Collection créée + indexes payload (article_num, doc_id)")

    # 3) Charger l'embedder
    log.info(f"Chargement embedder {EMBED_MODEL}...")
    model = SentenceTransformer(EMBED_MODEL)

    # 4) Lister les fichiers sources
    files = []
    for prefix in ARTICLE_SOURCES:
        files.extend(NORMALIZED_DIR.glob(f"{prefix}*.json"))
    log.info(f"Fichiers à traiter : {len(files):,}")

    # 5) Charger UUIDs déjà indexés (skip)
    existing_uuids = set()
    if client.get_collection(COLLECTION_ARTICLES).points_count > 0:
        offset = None
        while True:
            pts, offset = client.scroll(
                COLLECTION_ARTICLES, limit=10000, offset=offset,
                with_payload=False, with_vectors=False,
            )
            for p in pts:
                existing_uuids.add(str(p.id))
            if not offset:
                break
        log.info(f"  {len(existing_uuids):,} articles déjà indexés (skip)")

    # 6) Extraction + indexation
    total_articles = 0
    skipped = 0
    docs_with_articles = 0
    batch = []
    BATCH_SIZE = 200

    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Erreur lecture {f.name}: {e}")
            continue

        full_text = doc.get("full_text", "") or ""
        if len(full_text) < 200:
            continue

        articles = extract_articles(full_text)
        if not articles:
            continue

        docs_with_articles += 1
        doc_id = doc.get("doc_id", f.stem)
        title = doc.get("title", "") or ""
        source = doc.get("source", "") or ""
        date = doc.get("date", "") or ""
        url = doc.get("url", "") or ""
        jurisdiction = doc.get("jurisdiction", "Belgium") or "Belgium"
        doc_type = doc.get("doc_type", "code") or "code"

        for art_num, art_text in articles:
            chunk_id = f"{doc_id}__art_{art_num}"
            uid = chunk_id_to_uuid(chunk_id)

            if uid in existing_uuids:
                skipped += 1
                continue

            payload = {
                "article_num": art_num,
                "doc_id": doc_id,
                "source": source,
                "title": title[:200],
                "date": date,
                "url": url,
                "jurisdiction": jurisdiction,
                "doc_type": doc_type,
                "text": art_text,
                "chunk_idx": 0,
                "code_name": title[:100],
            }

            # Embedding
            vec = model.encode([art_text])[0].tolist()

            batch.append(PointStruct(id=uid, vector=vec, payload=payload))
            total_articles += 1

            # Flush batch
            if len(batch) >= BATCH_SIZE:
                client.upsert(collection_name=COLLECTION_ARTICLES, points=batch, wait=False)
                if total_articles % 1000 == 0:
                    log.info(f"  → {total_articles:,} articles indexés ({docs_with_articles} docs)")
                batch = []

    # Flush final
    if batch:
        client.upsert(collection_name=COLLECTION_ARTICLES, points=batch, wait=True)

    log.info("")
    log.info(f"=== TERMINÉ ===")
    log.info(f"  Documents avec articles : {docs_with_articles:,}")
    log.info(f"  Articles indexés        : {total_articles:,}")
    log.info(f"  Articles skippés        : {skipped:,}")

    # 7) Vérification finale
    info = client.get_collection(COLLECTION_ARTICLES)
    log.info(f"  Total points collection : {info.points_count:,}")

    # Test recherche article 1134
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    art_pts, _ = client.scroll(
        COLLECTION_ARTICLES,
        scroll_filter=Filter(must=[FieldCondition(key="article_num", match=MatchValue(value="1134"))]),
        limit=3, with_payload=True, with_vectors=False,
    )
    log.info(f"\nTest 'article 1134' : {len(art_pts)} hits")
    for p in art_pts:
        title = (p.payload or {}).get("title", "")[:60]
        text = (p.payload or {}).get("text", "")[:100]
        log.info(f"  [{title}] {text}...")


if __name__ == "__main__":
    main()
