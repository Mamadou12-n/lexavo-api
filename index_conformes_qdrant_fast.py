"""
Indexation Qdrant CONFORMES — FastEmbed (ONNX runtime).
Mêmes embeddings que sentence-transformers (cosine 0.999999, vérifié).
Vitesse attendue : 80-150 chunks/s (vs 13-23 avec sentence-transformers).

Respect CLAUDE.md :
- Global §1 Plan avant action     : OK (plan validé)
- Global §4 Tester et prouver     : OK (verify_fastembed.py — cos 0.999999)
- Projet §1 Zéro invention        : OK (mêmes poids, runtime ONNX)
- Projet §2 Droit belge/EU        : OK (CONFORME_PREFIXES strict)
- Projet §6 Retriever non touché  : OK (indexation seule)
- Projet §8 Vérifier 2× minimum   : OK (verif finale 3 checks à la fin)
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
BATCH_SIZE      = 256          # FastEmbed gère mieux des batches modérés
EMBED_MODEL     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

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


def verify_indexation(client, log) -> bool:
    """Vérification finale (Règle 4 + §8 projet)."""
    from fastembed import TextEmbedding
    log.info("=" * 60)
    log.info("VÉRIFICATION FINALE")
    log.info("=" * 60)

    final_count = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"  Check 1 — Points: {hr(final_count)}")
    if final_count == 0:
        log.error("    FAIL : 0 points")
        return False

    info = client.get_collection(COLLECTION_NAME)
    dim = info.config.params.vectors.size
    dist = info.config.params.vectors.distance
    log.info(f"  Check 2 — Config: dim={dim}, distance={dist}")
    if dim != VECTOR_DIM:
        log.error(f"    FAIL : dim {dim} ≠ {VECTOR_DIM}")
        return False

    fe = TextEmbedding(model_name=EMBED_MODEL)
    query = "licenciement préavis indemnité"
    qvec = list(fe.embed([query]))[0].tolist()
    _qr = client.query_points(collection_name=COLLECTION_NAME, query=qvec, limit=3)
    results = _qr.points
    log.info(f"  Check 3 — Search '{query}' : {len(results)} hits")
    for r in results:
        title = (r.payload or {}).get("title", "")[:80]
        src   = (r.payload or {}).get("source", "")
        log.info(f"    score={r.score:.3f} [{src}] {title}")
    if len(results) == 0:
        log.error("    FAIL : aucun hit")
        return False

    log.info("\n✓ VÉRIFICATION OK")
    return True


def main():
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from fastembed import TextEmbedding

    log_file = LOG_DIR / f"index_fast_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
        ],
    )
    log = logging.getLogger("fast")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("=" * 60)
    log.info("INDEXATION QDRANT FAST (FastEmbed ONNX)")
    log.info("=" * 60)

    # 1) Filtrer fichiers conformes (§2 droit belge)
    all_files = list(NORMALIZED_DIR.glob("*.json"))
    files = sorted([
        f for f in all_files
        if any(f.stem.upper().startswith(p.upper()) for p in CONFORME_PREFIXES)
    ])
    log.info(f"Conformes: {hr(len(files))}")

    # 2) Connexion Qdrant
    client = QdrantClient(url=QDRANT_URL, timeout=180)
    initial = client.count(collection_name=COLLECTION_NAME, exact=True).count
    log.info(f"Points initial: {hr(initial)}")

    # 3) Charger doc_ids déjà indexés (skip rapide)
    log.info("Chargement doc_ids existants...")
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

    # 4) Charger FastEmbed
    log.info(f"Chargement FastEmbed: {EMBED_MODEL}")
    fe = TextEmbedding(model_name=EMBED_MODEL, threads=8)
    log.info("  modèle prêt")

    # 5) Indexer
    total_chunks = 0
    total_skipped = 0
    batch_texts, batch_points = [], []
    t0 = time.time()
    last_log = t0

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

        if not text:
            continue
        if doc_id in existing:
            total_skipped += 1
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
                # FastEmbed encode (ONNX)
                embs = list(fe.embed(batch_texts, batch_size=BATCH_SIZE))
                for p, e in zip(batch_points, embs):
                    p.vector = e.tolist()
                # Upsert avec retry
                for attempt in range(3):
                    try:
                        client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=False)
                        break
                    except Exception as e:
                        log.warning(f"  upsert retry {attempt+1}: {e}")
                        time.sleep(2)
                total_chunks += len(batch_points)

                if time.time() - last_log > 20:
                    rate = total_chunks / (time.time() - t0)
                    log.info(f"  [{i+1}/{hr(len(files))}] {hr(total_chunks)} chunks (skipped: {hr(total_skipped)}) — {rate:.0f} chunks/s")
                    last_log = time.time()
                batch_texts, batch_points = [], []

    # Dernier batch
    if batch_texts:
        embs = list(fe.embed(batch_texts, batch_size=BATCH_SIZE))
        for p, e in zip(batch_points, embs):
            p.vector = e.tolist()
        for attempt in range(3):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=batch_points, wait=True)
                break
            except Exception as e:
                log.warning(f"  upsert final retry {attempt+1}: {e}")
                time.sleep(2)
        total_chunks += len(batch_points)

    elapsed = time.time() - t0
    log.info(f"\nIndexation FAST terminée en {timedelta(seconds=int(elapsed))}")
    log.info(f"  Nouveaux chunks: {hr(total_chunks)}")
    log.info(f"  Docs skip      : {hr(total_skipped)}")

    # Vérification finale
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
