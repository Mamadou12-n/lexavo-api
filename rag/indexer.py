"""
RAG Indexer — Phase 2 App Droit Belgique
Charge les documents juridiques normalisés → chunks → embeddings → ChromaDB

Modèle : paraphrase-multilingual-MiniLM-L12-v2
  - Multilingue : FR, NL, DE, EN (requis pour droit belge)
  - Léger : 118M params, fonctionne en local
  - Dimension : 384

ChromaDB : base vectorielle locale (pas de serveur requis)
  - Stockage : output/chroma_db/
  - Collection : legal_docs_be
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("indexer")

# ─── Configuration ────────────────────────────────────────────────────────────
NORMALIZED_DIR = OUTPUT_DIR / "normalized"
CHROMA_DIR     = OUTPUT_DIR / "chroma_db"
COLLECTION_NAME = "legal_docs_be"
EMBED_MODEL     = "paraphrase-multilingual-MiniLM-L12-v2"

# Paramètres de chunking
CHUNK_SIZE          = 512    # chars par chunk pour jurisprudence
CHUNK_SIZE_CODE     = 1500   # chars par chunk pour codes légaux (garde l'article entier dans son contexte)
CHUNK_OVERLAP       = 64     # chars de recouvrement jurisprudence
CHUNK_OVERLAP_CODE  = 200    # chars de recouvrement codes (plus de contexte entre articles)
MAX_CHUNKS_PER_DOC_DEFAULT = 20    # arrêts jurisprudence (courts)
MAX_CHUNKS_PER_DOC_CODE    = 2000  # codes légaux (textes complets, jamais tronqués)

# Sources dont les textes doivent être indexés en entier
SOURCES_CODES = {"JUSTEL", "Codex Vlaanderen", "GalliLex", "WalLex", "ETAAMB",
                 "SPF Finances", "SPF Emploi", "Bruxelles"}


# ─── Chunking ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Découpe un texte en chunks de taille fixe avec chevauchement.
    Essaie de couper aux limites de phrase/paragraphe.
    """
    if not text:
        return []

    # Couper d'abord aux paragraphes si possible
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # Si le paragraphe seul dépasse chunk_size, le sous-diviser
        if len(para) > chunk_size:
            # Sauvegarder le chunk en cours
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Découper le paragraphe long par mots
            words = para.split()
            temp = ""
            for word in words:
                if len(temp) + len(word) + 1 > chunk_size:
                    if temp:
                        chunks.append(temp.strip())
                    temp = current_chunk[-overlap:] + word + " " if current_chunk else word + " "
                    current_chunk = ""
                else:
                    temp += word + " "
            if temp:
                current_chunk = temp
        else:
            # Ajouter le paragraphe au chunk en cours
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Recouvrement : garder les derniers chars
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Filtrer les chunks trop courts
    chunks = [c for c in chunks if len(c) >= 50]
    return chunks  # La limite par doc est appliquée dans build_index() selon le type


# ─── Indexation ───────────────────────────────────────────────────────────────

def build_index(
    normalized_dir: Path = NORMALIZED_DIR,
    chroma_dir: Path = CHROMA_DIR,
    batch_size: int = 100,
    max_docs: Optional[int] = None,
    reset: bool = False,
) -> int:
    """
    Construit l'index vectoriel depuis les documents normalisés.

    Args:
        normalized_dir: Répertoire des JSON normalisés (output/normalized/)
        chroma_dir: Répertoire de stockage ChromaDB
        batch_size: Taille des batches d'indexation
        max_docs: Limite de documents (None = tous)
        reset: Supprimer l'index existant avant d'indexer

    Returns:
        Nombre total de chunks indexés
    """
    import chromadb
    from sentence_transformers import SentenceTransformer

    chroma_dir.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    log.info(f"=== Démarrage indexation RAG ===")
    log.info(f"  Modèle embeddings : {EMBED_MODEL}")
    log.info(f"  Répertoire docs   : {normalized_dir}")
    log.info(f"  Base ChromaDB     : {chroma_dir}")

    # Charger le modèle d'embedding
    log.info("Chargement modèle d'embedding...")
    model = SentenceTransformer(EMBED_MODEL)
    log.info(f"  Modèle chargé (dim={model.get_sentence_embedding_dimension()})")

    # Connexion ChromaDB
    client = chromadb.PersistentClient(path=str(chroma_dir))

    if reset and COLLECTION_NAME in [c.name for c in client.list_collections()]:
        log.info("  Reset : suppression collection existante")
        client.delete_collection(COLLECTION_NAME)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Charger les documents normalisés
    files = sorted(normalized_dir.glob("*.json"))
    if max_docs:
        files = files[:max_docs]

    log.info(f"  {len(files)} documents à indexer")

    # IDs déjà indexés pour éviter les doublons
    try:
        existing_count = collection.count()
        log.info(f"  Chunks déjà indexés : {existing_count}")
    except Exception:
        existing_count = 0

    # Indexer en batches
    total_chunks = 0
    batch_docs, batch_embeds, batch_ids, batch_metas = [], [], [], []

    for i, json_file in enumerate(files):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            log.warning(f"  Erreur lecture {json_file.name}: {e}")
            continue

        doc_id   = doc.get("doc_id", json_file.stem)
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

        # Construire le texte enrichi (titre + texte) pour meilleurs embeddings
        enriched_text = f"{title}\n\n{text}" if title and title not in text[:200] else text

        # Codes légaux : gros chunks (1500 chars) pour garder chaque article entier
        # Jurisprudence : petits chunks (512 chars) pour précision
        is_code = (
            source in SOURCES_CODES
            or "coordonné" in doc_type.lower()
            or title.lower().startswith("code ")
            or title.lower().startswith("nouveau code ")
            or title.lower().startswith("loi ")
            or title.lower().startswith("arrêté ")
            or title.lower().startswith("décret ")
            or title.lower().startswith("constitution")
        )
        if is_code:
            c_size, c_overlap, max_chunks = CHUNK_SIZE_CODE, CHUNK_OVERLAP_CODE, MAX_CHUNKS_PER_DOC_CODE
        else:
            c_size, c_overlap, max_chunks = CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_DOC_DEFAULT

        chunks = chunk_text(enriched_text, chunk_size=c_size, overlap=c_overlap)[:max_chunks]
        if not chunks:
            continue

        for j, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}__chunk_{j:03d}"

            # Vérifier si déjà indexé (mode incrémental)
            try:
                existing = collection.get(ids=[chunk_id])
                if existing["ids"]:
                    total_chunks += 1
                    continue
            except Exception:
                pass

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

            # Indexer par batch
            if len(batch_docs) >= batch_size:
                embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
                collection.add(
                    documents=batch_docs,
                    embeddings=embeddings,
                    ids=batch_ids,
                    metadatas=batch_metas,
                )
                total_chunks += len(batch_docs)
                log.info(f"  [{i+1}/{len(files)}] +{len(batch_docs)} chunks (total: {total_chunks})")
                batch_docs, batch_embeds, batch_ids, batch_metas = [], [], [], []

    # Dernier batch
    if batch_docs:
        embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
        collection.add(
            documents=batch_docs,
            embeddings=embeddings,
            ids=batch_ids,
            metadatas=batch_metas,
        )
        total_chunks += len(batch_docs)

    log.info(f"=== Indexation terminée : {total_chunks} chunks dans ChromaDB ===")

    # ─── Alt.8 : Index articles séparé ───────────────────────────────────
    log.info("  Construction index articles séparé (Alt.8)...")
    articles_count = _build_articles_index(client, normalized_dir)
    log.info(f"  → {articles_count} articles indexés dans legal_articles_be")

    return total_chunks


ARTICLES_COLLECTION = "legal_articles_be"


def _build_articles_index(client, normalized_dir: Path) -> int:
    """
    Alt.8 — Indexe chaque article de loi individuellement dans une collection séparée.
    Permet la recherche directe par numéro d'article (100% précis).
    """
    import re

    # Créer ou reset la collection articles
    try:
        client.delete_collection(ARTICLES_COLLECTION)
    except Exception:
        pass
    art_collection = client.get_or_create_collection(
        name=ARTICLES_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    files = sorted(normalized_dir.glob("*.json"))
    total_articles = 0
    batch_docs, batch_ids, batch_metas = [], [], []

    for json_file in files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue

        text = doc.get("full_text", "")
        title = doc.get("title", "")
        numac = doc.get("numac", doc.get("doc_id", json_file.stem))
        source = doc.get("source", "")

        if not text or len(text) < 100:
            continue

        # Découper par articles : "Art. X." suivi du texte jusqu'au prochain "Art."
        parts = re.split(r'(?=\bArt(?:icle)?\.?\s*\d)', text)

        for part in parts:
            art_match = re.match(r'Art(?:icle)?\.?\s*(\d+[\w.:/-]*)', part)
            if not art_match:
                continue

            art_num = art_match.group(1).strip().rstrip(".")
            art_text = part[:3000].strip()

            if len(art_text) < 20:
                continue

            art_id = f"{numac}__art_{art_num}"

            batch_docs.append(art_text)
            batch_ids.append(art_id)
            batch_metas.append({
                "article_num": art_num,
                "title": title[:200],
                "numac": numac,
                "source": source,
            })

            if len(batch_docs) >= 200:
                try:
                    art_collection.add(
                        documents=batch_docs,
                        ids=batch_ids,
                        metadatas=batch_metas,
                    )
                    total_articles += len(batch_docs)
                except Exception as e:
                    log.warning(f"  Erreur batch articles: {e}")
                batch_docs, batch_ids, batch_metas = [], [], []

    # Dernier batch
    if batch_docs:
        try:
            art_collection.add(
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_metas,
            )
            total_articles += len(batch_docs)
        except Exception as e:
            log.warning(f"  Erreur dernier batch articles: {e}")

    return total_articles


def get_index_stats(chroma_dir: Path = CHROMA_DIR) -> Dict:
    """Retourne les statistiques de l'index ChromaDB (chunks, documents, sources)."""
    import chromadb

    if not chroma_dir.exists():
        return {"status": "non_existant", "total_chunks": 0, "total_documents": 0, "sources": {}}

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()

        # Récupérer les métadonnées pour calculer stats par source et nb de docs
        sources: Dict[str, int] = {}
        doc_ids: set = set()

        if count > 0:
            # Fetch metadata par batches (ChromaDB limite à 10_000 / requête)
            batch = 5_000
            offset = 0
            while True:
                res = collection.get(
                    limit=batch,
                    offset=offset,
                    include=["metadatas"],
                )
                metas = res.get("metadatas") or []
                if not metas:
                    break
                for m in metas:
                    src = m.get("source", "Inconnu")
                    sources[src] = sources.get(src, 0) + 1
                    doc_ids.add(m.get("doc_id", ""))
                offset += batch
                if len(metas) < batch:
                    break

        return {
            "status": "ok",
            "collection": COLLECTION_NAME,
            "total_chunks": count,
            "total_documents": len(doc_ids),
            "sources": sources,
            "chroma_dir": str(chroma_dir),
        }
    except Exception as e:
        return {"status": "erreur", "error": str(e), "total_chunks": 0, "total_documents": 0, "sources": {}}


if __name__ == "__main__":
    # Normaliser d'abord si nécessaire
    import argparse
    parser = argparse.ArgumentParser(description="Indexer RAG — App Droit Belgique")
    parser.add_argument("--normalize-first", action="store_true", help="Normaliser les docs avant indexation")
    parser.add_argument("--reset", action="store_true", help="Réinitialiser l'index")
    parser.add_argument("--max", type=int, default=None, help="Limite de docs")
    args = parser.parse_args()

    if args.normalize_first:
        log.info("Normalisation des documents bruts...")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from processors.cleaner import process_all_sources
        stats = process_all_sources()
        total_valid = sum(s["valid"] for s in stats.values())
        log.info(f"Normalisation : {total_valid} docs valides")

    # Lancer l'indexation
    count = build_index(reset=args.reset, max_docs=args.max)
    print(f"\nIndex construit : {count} chunks")

    stats = get_index_stats()
    print(f"Stats ChromaDB : {stats}")
