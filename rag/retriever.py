"""
RAG Retriever — Recherche vectorielle dans ChromaDB
Prend une question → embed → top-k chunks pertinents

Optimisations :
- Re-ranking simple par source (HUDOC/JUPORTAL prioritaires pour droit belge)
- Déduplication par doc_id (évite plusieurs chunks du même doc)
- Filtre optionnel par source, date, juridiction
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR
from rag.indexer import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("retriever")


# ─── Priorités par source (pour droit belge) ──────────────────────────────────
SOURCE_PRIORITY = {
    # Jurisprudence belge nationale → top priorité
    "Juridat":                5,
    "Cour constitutionnelle": 5,
    "Conseil d'État":         5,
    # Sources CEDH / UE → haute priorité
    "HUDOC":                  4,
    "EUR-Lex":                4,
    # Législation belge → haute priorité
    "Moniteur belge":         4,
    "JUSTEL":                 4,
    # Sources spécialisées
    "CCE":                    3,
    "CNT":                    3,
    "APD":                    3,
    "FSMA":                   3,
    # Législation régionale/communautaire
    "GalliLex":               3,
    "WalLex":                 3,
    "Chambre":                3,
    "Cour des comptes":       2,
    # Législation régionale complète
    "Codex Vlaanderen":       3,
    "Bruxelles":              3,
    "SPF Finances":           4,
}


def _get_collection():
    """Retourne la collection ChromaDB (lazy init)."""
    import chromadb
    chroma_dir = CHROMA_DIR

    if not chroma_dir.exists():
        raise RuntimeError(
            f"Index ChromaDB non trouvé à {chroma_dir}. "
            "Lancez d'abord : python -m rag.indexer"
        )

    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_collection(COLLECTION_NAME)


def _get_model():
    """Retourne le modèle d'embedding (lazy init)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


# Singletons pour éviter de recharger à chaque requête
_collection = None
_model = None


def get_collection():
    global _collection
    if _collection is None:
        _collection = _get_collection()
    return _collection


def get_model():
    global _model
    if _model is None:
        _model = _get_model()
        log.info(f"Modèle d'embedding chargé : {EMBED_MODEL}")
    return _model


def retrieve(
    query: str,
    top_k: int = 10,
    max_per_doc: int = 3,
    source_filter: Optional[List[str]] = None,
    jurisdiction_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict]:
    """
    Recherche les chunks les plus pertinents pour une question juridique.

    Args:
        query: Question en langage naturel (FR, NL, EN)
        top_k: Nombre de chunks à retourner
        max_per_doc: Max chunks par document (déduplication)
        source_filter: ['HUDOC', 'EUR-Lex', 'Juridat', 'Moniteur belge']
        jurisdiction_filter: 'CASS_BE', 'ECHR', 'CJEU', etc.
        date_from: Filtrer à partir de cette date (YYYY-MM-DD)
        date_to: Filtrer jusqu'à cette date (YYYY-MM-DD)

    Returns:
        Liste de dicts avec chunk, métadonnées, score
    """
    model      = get_model()
    collection = get_collection()

    # Embed la question
    query_embedding = model.encode([query])[0].tolist()

    # Construire les filtres ChromaDB
    where = {}
    if source_filter and len(source_filter) == 1:
        where["source"] = {"$eq": source_filter[0]}
    elif source_filter and len(source_filter) > 1:
        where["source"] = {"$in": source_filter}

    if jurisdiction_filter:
        where["jurisdiction"] = {"$eq": jurisdiction_filter}

    # Récupérer plus de résultats bruts pour pouvoir re-ranker
    n_results = min(top_k * 5, collection.count())

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    if not results["documents"] or not results["documents"][0]:
        return []

    # ─── Recherche hybride : mots-clés en complément des vecteurs ────────
    # Si la requête mentionne un numéro d'article ou un terme juridique précis,
    # on cherche aussi par mots-clés pour ne pas rater l'article exact
    import re
    keyword_chunks = []
    art_match = re.search(r"art(?:icle)?\.?\s*(\d+[\w./]*)", query, re.IGNORECASE)
    if art_match:
        art_num = art_match.group(1)
        # Chercher "Art. X" dans les documents ChromaDB
        for pattern in [f"Art. {art_num}", f"Art.{art_num}", f"article {art_num}"]:
            try:
                kw_results = collection.get(
                    where_document={"$contains": pattern},
                    limit=5,
                    include=["documents", "metadatas"],
                )
                for doc_text, meta in zip(kw_results["documents"], kw_results["metadatas"]):
                    keyword_chunks.append((doc_text, meta))
            except Exception:
                pass
            if keyword_chunks:
                break

    # Construire la liste des résultats
    chunks = []
    seen_doc_ids = {}
    seen_chunk_ids = set()

    # Injecter les résultats mots-clés EN PREMIER (priorité maximale)
    for doc_text, meta in keyword_chunks:
        doc_id = meta.get("doc_id", "")
        chunk_id = f"{doc_id}__{meta.get('chunk_idx', 0)}"
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)

        count = seen_doc_ids.get(doc_id, 0)
        if count >= max_per_doc:
            continue
        seen_doc_ids[doc_id] = count + 1

        source = meta.get("source", "")
        chunks.append({
            "chunk_text":   doc_text,
            "doc_id":       doc_id,
            "source":       source,
            "doc_type":     meta.get("doc_type", ""),
            "jurisdiction": meta.get("jurisdiction", ""),
            "title":        meta.get("title", ""),
            "date":         meta.get("date", ""),
            "url":          meta.get("url", ""),
            "ecli":         meta.get("ecli", ""),
            "similarity":   0.95,  # score élevé car match exact par mot-clé
            "score":        0.99,
            "chunk_idx":    meta.get("chunk_idx", 0),
        })

    for doc_text, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        doc_id  = meta.get("doc_id", "")
        source  = meta.get("source", "")
        date    = meta.get("date", "")

        # Skip si déjà ajouté par la recherche mots-clés
        chunk_id = f"{doc_id}__{meta.get('chunk_idx', 0)}"
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)

        # Filtre par date (post-processing car ChromaDB ne supporte pas les comparaisons de chaînes)
        if date_from and date and date < date_from:
            continue
        if date_to and date and date > date_to:
            continue

        # Limiter par document (déduplication)
        count = seen_doc_ids.get(doc_id, 0)
        if count >= max_per_doc:
            continue
        seen_doc_ids[doc_id] = count + 1

        # Score = 1 - distance cosinus (ChromaDB retourne des distances)
        similarity = 1.0 - distance

        # Bonus de priorité source
        priority_bonus = SOURCE_PRIORITY.get(source, 2) * 0.01

        chunks.append({
            "chunk_text":   doc_text,
            "doc_id":       doc_id,
            "source":       source,
            "doc_type":     meta.get("doc_type", ""),
            "jurisdiction": meta.get("jurisdiction", ""),
            "title":        meta.get("title", ""),
            "date":         date,
            "url":          meta.get("url", ""),
            "ecli":         meta.get("ecli", ""),
            "similarity":   round(similarity, 4),
            "score":        round(similarity + priority_bonus, 4),
            "chunk_idx":    meta.get("chunk_idx", 0),
        })

    # Trier par score décroissant
    chunks.sort(key=lambda x: x["score"], reverse=True)

    return chunks[:top_k]


def format_context(chunks: List[Dict], max_total_chars: int = 4000) -> str:
    """
    Formate les chunks en contexte pour le LLM.
    Respecte une limite de tokens approximative.
    """
    context_parts = []
    total_chars = 0

    for i, chunk in enumerate(chunks, 1):
        source   = chunk.get("source", "")
        title    = chunk.get("title", "")
        date     = chunk.get("date", "")
        ecli     = chunk.get("ecli", "")
        url      = chunk.get("url", "")
        text     = chunk.get("chunk_text", "")

        # En-tête du chunk
        header_parts = [f"[{i}] {source}"]
        if title:
            header_parts.append(f"— {title[:80]}")
        if date:
            header_parts.append(f"({date})")
        if ecli:
            header_parts.append(f"| ECLI: {ecli}")

        header = " ".join(header_parts)
        chunk_text = f"{header}\n{text}"

        if total_chars + len(chunk_text) > max_total_chars:
            # Tronquer le chunk pour rentrer dans la limite
            remaining = max_total_chars - total_chars - len(header) - 10
            if remaining > 100:
                chunk_text = f"{header}\n{text[:remaining]}..."
                context_parts.append(chunk_text)
            break

        context_parts.append(chunk_text)
        total_chars += len(chunk_text)

    return "\n\n---\n\n".join(context_parts)


if __name__ == "__main__":
    # Test rapide
    query = "Quelles sont les conditions de validité d'un licenciement en droit belge ?"
    print(f"Requête : {query}\n")

    try:
        results = retrieve(query, top_k=3)
        print(f"{len(results)} chunks trouvés\n")
        for r in results:
            print(f"  [{r['source']}] {r['title'][:60]} | score={r['score']:.3f}")
            print(f"  {r['chunk_text'][:200]}...\n")

        print("\n--- Contexte formaté ---")
        print(format_context(results))
    except RuntimeError as e:
        print(f"Erreur : {e}")
        print("Lancez d'abord : python -m rag.indexer --normalize-first")
