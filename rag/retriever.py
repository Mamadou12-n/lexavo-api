"""
RAG Retriever — Lexavo (9 alternatives de recherche) — Backend Qdrant
======================================================================

Architecture 9 alternatives qui se corrigent mutuellement :
  Alt.1 : Recherche vecteurs (sémantique)
  Alt.2 : Mots-clés articles (Art. X)
  Alt.3 : Termes juridiques (MatchText multi-termes)
  Alt.4 : Chunks voisins (contexte ±1)
  Alt.5 : Vote majoritaire (fusion 1+2+3)
  Alt.6 : Détection source dans la question
  Alt.7 : Re-ranking Claude Haiku
  Alt.8 : Index articles séparé (collection legal_articles_be)
  Alt.9 : Reformulation automatique

Garantie : si une alternative se trompe, les autres la corrigent.
Si l'info n'est pas dans la base → dire "je ne sais pas", jamais inventer.

Backend : Qdrant (collection `legal_docs_be`, 384 dims, Cosine).
"""

from __future__ import annotations

import logging
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("retriever")


# ─── Configuration Qdrant ────────────────────────────────────────────────────
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "legal_docs_be")
ARTICLES_COLLECTION_NAME = os.getenv("QDRANT_ARTICLES_COLLECTION", "legal_articles_be")
EMBED_MODEL = os.getenv(
    "EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# UUID5 namespace — IDs Qdrant sont calculés à partir des chunk_ids texte
NAMESPACE = uuid.NAMESPACE_OID


def chunk_id_to_uuid(chunk_id: str) -> str:
    """Convertit un chunk_id texte (`{doc_id}__chunk_{idx:03d}`) en UUID5."""
    return str(uuid.uuid5(NAMESPACE, chunk_id))


# ─── Priorités par source ────────────────────────────────────────────────────
SOURCE_PRIORITY = {
    "Juridat": 5, "Cour constitutionnelle": 5, "Conseil d'État": 5,
    "HUDOC": 4, "EUR-Lex": 4, "Moniteur belge": 4, "JUSTEL": 4,
    "SPF Finances": 4, "SPF Emploi": 4,
    "CCE": 3, "CNT": 3, "APD": 3, "FSMA": 3,
    "GalliLex": 3, "WalLex": 3, "Chambre": 3, "Cour des comptes": 2,
    "Codex Vlaanderen": 3, "Bruxelles": 3,
}

# ─── Alt.6 : Détection source dans la question ──────────────────────────────
SOURCE_DETECT = {
    # Droit pénal — matcher "code pénal", "droit pénal", mais PAS "pénal social"
    r"(?:code|droit)\s*p[ée]nal(?!\s*social)": "Code pénal",
    r"p[ée]nal\s*social":            "Code pénal social",
    r"vol\b|soustraction.*fraudul|meurtre|homicide|infraction.*p[ée]nal": "Code pénal",
    # Droit civil
    r"code\s*civil":                 "Code civil",
    r"code\s*judiciaire":            "Code judiciaire",
    r"constitution":                 "Constitution belge",
    r"\bCSA\b|soci[ée]t[ée]s?\s*(?:et\s*)?associations?": "Code des sociétés et associations",
    r"\bCDE\b|droit\s*[ée]conomique": "Code de droit économique",
    r"\bTVA\b|taxe.*valeur":         "Code de la TVA",
    r"\bCIR\b|imp[ôo]ts?\s*sur\s*les?\s*revenus?": "Code des impôts",
    # Droit des étrangers
    r"[ée]trangers?|s[ée]jour.*(?:belg|territoire)|asile|r[ée]fugi": "Loi sur les etrangers",
    # Droit du travail — matcher avec OU sans "de"
    r"contrats?\s*(?:de\s+)?travail|licenciement|motif\s*grave|pr[ée]avis": "Loi sur les contrats de travail",
    r"droits?\s*du?\s*patient":      "Loi relative aux droits du patient",
    r"march[ée]s?\s*publics?":       "Loi du 17 juin 2016",
    r"bien[- ]?[êe]tre.*travail":    "Loi relative au bien-être",
    r"accidents?\s*d[ue]\s*travail": "Loi sur les accidents du travail",
    r"nationalit[ée]":               "Code de la nationalite",
    r"instruction\s*criminelle":     "Code d'instruction criminelle",
    r"assurance":                    "Loi sur les assurances",
}

# Stopwords pour Alt.3
STOPWORDS_FR = {
    "quel", "quelle", "quels", "quelles", "dans", "pour", "avec", "sont",
    "comment", "quoi", "belgique", "belge", "droit", "code", "article",
    "quand", "peut", "cette", "faire", "avoir", "etre", "plus", "comme",
    "tout", "tous", "toute", "toutes", "bien", "tres", "aussi", "encore",
}


# ─── Singletons ─────────────────────────────────────────────────────────────
_client = None
_articles_available: Optional[bool] = None  # cache : la collection existe-t-elle ?
_model = None


def _get_client():
    """Client Qdrant unique (timeout 30s, compatible VPS et local)."""
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )


def get_client():
    global _client
    if _client is None:
        _client = _get_client()
        log.info(f"Client Qdrant initialisé: {QDRANT_URL} | collection={COLLECTION_NAME}")
    return _client


def _articles_collection_exists() -> bool:
    """Vérifie une seule fois si la collection articles séparée existe (Alt.8)."""
    global _articles_available
    if _articles_available is not None:
        return _articles_available
    try:
        client = get_client()
        client.get_collection(ARTICLES_COLLECTION_NAME)
        _articles_available = True
        log.info(f"Alt.8 disponible: collection {ARTICLES_COLLECTION_NAME} trouvée")
    except Exception:
        _articles_available = False
        log.debug(f"Alt.8 indisponible: pas de collection {ARTICLES_COLLECTION_NAME}")
    return _articles_available


def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def get_model():
    global _model
    if _model is None:
        _model = _get_model()
        log.info(f"Modèle d'embedding chargé : {EMBED_MODEL}")
    return _model


# ─── Helpers Qdrant ─────────────────────────────────────────────────────────

def _build_qdrant_filter(
    source_filter: Optional[List[str]] = None,
    jurisdiction_filter: Optional[str] = None,
    extra_must: Optional[list] = None,
):
    """Construit un Filter Qdrant à partir des filtres de l'API."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

    must: list = []
    if source_filter:
        if len(source_filter) == 1:
            must.append(FieldCondition(key="source", match=MatchValue(value=source_filter[0])))
        else:
            must.append(FieldCondition(key="source", match=MatchAny(any=list(source_filter))))
    if jurisdiction_filter:
        must.append(FieldCondition(key="jurisdiction", match=MatchValue(value=jurisdiction_filter)))
    if extra_must:
        must.extend(extra_must)

    if not must:
        return None
    return Filter(must=must)


def _payload_to_meta(payload: dict) -> Tuple[str, dict]:
    """Extrait (text, meta) depuis un payload Qdrant."""
    payload = payload or {}
    text = payload.get("text", "") or ""
    meta = {
        "doc_id":       payload.get("doc_id", ""),
        "source":       payload.get("source", ""),
        "title":        payload.get("title", ""),
        "date":         payload.get("date", ""),
        "url":          payload.get("url", ""),
        "ecli":         payload.get("ecli", ""),
        "doc_type":     payload.get("doc_type", ""),
        "jurisdiction": payload.get("jurisdiction", ""),
        "chunk_idx":    payload.get("chunk_idx", 0),
    }
    return text, meta


def _scroll_match_text(
    client,
    collection_name: str,
    text_pattern: str,
    limit: int,
    base_filter=None,
) -> List[Tuple[str, dict]]:
    """
    Scroll avec MatchText sur le champ `text`. Dégradation gracieuse si
    l'index full-text n'existe pas ou si la requête timeout.
    """
    from qdrant_client.models import (
        Filter,
        FieldCondition,
        MatchText,
    )

    must = [FieldCondition(key="text", match=MatchText(text=text_pattern))]
    if base_filter is not None and base_filter.must:
        must = list(base_filter.must) + must
    flt = Filter(must=must)

    try:
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=flt,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [_payload_to_meta(p.payload) for p in points]
    except Exception as e:
        log.debug(f"MatchText scroll échoué ({text_pattern[:30]}): {e}")
        return []


# ─── Alt.4 : Chunks voisins ─────────────────────────────────────────────────

def _get_neighbor_chunks(client, doc_id: str, chunk_idx: int) -> List[Tuple[str, dict]]:
    """Récupère les chunks adjacents (idx-1 et idx+1) du même document via UUID5."""
    if not doc_id:
        return []
    neighbors: List[Tuple[str, dict]] = []
    neighbor_ids: List[str] = []
    for offset in [-1, 1]:
        neighbor_idx = chunk_idx + offset
        if neighbor_idx < 0:
            continue
        chunk_id_text = f"{doc_id}__chunk_{neighbor_idx:03d}"
        neighbor_ids.append(chunk_id_to_uuid(chunk_id_text))

    if not neighbor_ids:
        return []

    try:
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=neighbor_ids,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            text, meta = _payload_to_meta(p.payload)
            neighbors.append((text, meta))
    except Exception as e:
        log.debug(f"Voisins (Alt.4) échoué pour {doc_id}/{chunk_idx}: {e}")

    return neighbors


# ─── Alt.7 : Re-ranking Haiku ───────────────────────────────────────────────

def _rerank_with_llm(question: str, chunks: List[Dict], top_n: int = 6) -> List[Dict]:
    """Claude Haiku re-classe les chunks par pertinence réelle."""
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or len(chunks) < 3:
            return chunks[:top_n]

        client = anthropic.Anthropic(api_key=api_key)
        chunks_text = "\n".join(
            f"[{i}] {c['title'][:40]}: {c['chunk_text'][:200]}"
            for i, c in enumerate(chunks[:12])
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    f"Question: {question}\n\nChunks:\n{chunks_text}\n\n"
                    f"Retourne les numéros des {top_n} chunks les plus pertinents, "
                    f"séparés par des virgules (ex: 2,0,5,1). Numéros uniquement."
                )
            }]
        )

        try:
            nums = [int(x.strip()) for x in response.content[0].text.strip().split(",")]
        except (ValueError, IndexError):
            log.warning("Rerank LLM parsing échoué — ordre original conservé")
            return chunks[:top_n]
        reranked = [chunks[i] for i in nums if 0 <= i < len(chunks)]
        # Compléter avec les restants si pas assez
        seen = set(nums)
        for i, c in enumerate(chunks):
            if i not in seen and len(reranked) < top_n:
                reranked.append(c)
        return reranked[:top_n]
    except Exception as e:
        log.debug(f"Re-ranking Haiku échoué: {e}")
        return chunks[:top_n]


# ─── Alt.9 : Reformulation automatique ──────────────────────────────────────

def _reformulate_query(question: str) -> Optional[str]:
    """Reformule la question en termes juridiques techniques via Haiku."""
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": (
                    f"Reformule en termes juridiques belges précis "
                    f"(cite le code/loi et article si connu): {question}\n"
                    f"1 phrase uniquement."
                )
            }]
        )
        reformulated = response.content[0].text.strip()
        if len(reformulated) > 10 and reformulated != question:
            return reformulated
        return None
    except Exception:
        return None


# ─── Fonction principale : retrieve() avec 9 alternatives ───────────────────

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
    Recherche les chunks les plus pertinents — 9 alternatives qui se corrigent.

    Returns:
        Liste de dicts avec chunk, métadonnées, score — triés par pertinence.
    """
    model = get_model()
    client = get_client()

    base_filter = _build_qdrant_filter(
        source_filter=source_filter,
        jurisdiction_filter=jurisdiction_filter,
    )

    # ═══ PASS 1 : Collecte par 4 méthodes parallèles ═══════════════════════

    # --- Alt.1 : Recherche vecteurs (sémantique) ---
    query_embedding = model.encode([query])[0].tolist()
    n_results = top_k * 5

    try:
        _qr = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            query_filter=base_filter,
            limit=n_results,
            with_payload=True,
        )
        vector_points = _qr.points
    except Exception as e:
        log.error(f"Alt.1 search Qdrant échoué: {e}")
        vector_points = []

    # --- Alt.6 : Détection source dans la question (AVANT les recherches par article) ---
    detected_source = None
    for pattern, source_title in SOURCE_DETECT.items():
        if re.search(pattern, query, re.IGNORECASE):
            detected_source = source_title
            break

    # --- Alt.2 : Mots-clés articles (Art. X) ---
    keyword_chunks: List[Tuple[str, dict]] = []
    art_match = re.search(r"art(?:icle)?\.?\s*(\d+[\w./:,-]*)", query, re.IGNORECASE)
    if art_match:
        art_num = art_match.group(1)

        # Alt.8 : Index articles séparé (si disponible dans Qdrant)
        if _articles_collection_exists():
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            try:
                art_flt = Filter(
                    must=[FieldCondition(key="article_num", match=MatchValue(value=art_num))]
                )
                art_points, _ = client.scroll(
                    collection_name=ARTICLES_COLLECTION_NAME,
                    scroll_filter=art_flt,
                    limit=5,
                    with_payload=True,
                    with_vectors=False,
                )
                for p in art_points:
                    text, meta = _payload_to_meta(p.payload)
                    keyword_chunks.append((text, meta))
            except Exception as e:
                log.debug(f"Alt.8 article lookup échoué: {e}")

        # Recherche MatchText classique dans la collection principale
        # Si une source est détectée dans la question, prioriser les chunks de cette source
        if not keyword_chunks:
            for pattern in [f"Art. {art_num}", f"Art.{art_num}", f"article {art_num}"]:
                hits = _scroll_match_text(
                    client, COLLECTION_NAME, pattern, limit=10, base_filter=base_filter
                )
                for doc_text, meta in hits:
                    if detected_source:
                        title = meta.get("title", "")
                        if detected_source.lower() in title.lower():
                            keyword_chunks.insert(0, (doc_text, meta))  # en tête
                        else:
                            keyword_chunks.append((doc_text, meta))
                    else:
                        keyword_chunks.append((doc_text, meta))
                if keyword_chunks:
                    break

    # --- Alt.3 : Termes juridiques significatifs ---
    legal_terms = [
        w for w in re.findall(r'\b[a-zéèêàùâîôûçü]{4,}\b', query.lower())
        if w not in STOPWORDS_FR
    ]

    if len(legal_terms) >= 2 and not keyword_chunks:
        for term in legal_terms[:3]:
            hits = _scroll_match_text(
                client, COLLECTION_NAME, term, limit=5, base_filter=base_filter
            )
            for doc_text, meta in hits:
                chunk_lower = (doc_text or "").lower()
                matches = sum(1 for t in legal_terms if t in chunk_lower)
                if matches >= 2:
                    keyword_chunks.append((doc_text, meta))
            if len(keyword_chunks) >= 5:
                break

    # ═══ FUSION : Construire la liste unifiée (Alt.5 vote majoritaire) ══════

    chunks: List[Dict] = []
    seen_chunk_ids = set()
    seen_doc_ids: Dict[str, int] = {}

    def _add_chunk(doc_text, meta, similarity, score, source_name=""):
        doc_id = meta.get("doc_id", "")
        chunk_idx = meta.get("chunk_idx", 0)
        chunk_id = f"{doc_id}__{chunk_idx}"
        if chunk_id in seen_chunk_ids:
            return
        seen_chunk_ids.add(chunk_id)

        count = seen_doc_ids.get(doc_id, 0)
        if count >= max_per_doc:
            return
        seen_doc_ids[doc_id] = count + 1

        source = meta.get("source", "")
        title = meta.get("title", "")
        date = meta.get("date", "")

        if date_from and date and date < date_from:
            return
        if date_to and date and date > date_to:
            return

        # Alt.6 : Bonus si source détectée correspond
        source_bonus = 0.0
        if detected_source and detected_source.lower() in title.lower():
            source_bonus = 0.3

        priority_bonus = SOURCE_PRIORITY.get(source, 2) * 0.01

        chunks.append({
            "chunk_text":   doc_text,
            "doc_id":       doc_id,
            "source":       source,
            "doc_type":     meta.get("doc_type", ""),
            "jurisdiction": meta.get("jurisdiction", ""),
            "title":        title,
            "date":         date,
            "url":          meta.get("url", ""),
            "ecli":         meta.get("ecli", ""),
            "similarity":   round(similarity, 4),
            "score":        round(score + priority_bonus + source_bonus, 4),
            "chunk_idx":    chunk_idx,
        })

    # Injecter mots-clés en premier (Alt.2 + Alt.3 + Alt.8)
    for doc_text, meta in keyword_chunks:
        _add_chunk(doc_text, meta, 0.95, 0.95, "keyword")

    # Injecter vecteurs (Alt.1) — Qdrant.score est déjà cosine similarity (pas distance)
    for sp in vector_points:
        text, meta = _payload_to_meta(sp.payload)
        similarity = float(sp.score)  # cosine similarity directe
        _add_chunk(text, meta, similarity, similarity, "vector")

    # ═══ Alt.5 : Tri par score (les doublons ont été éliminés) ══════════════
    chunks.sort(key=lambda x: x["score"], reverse=True)

    # ═══ Alt.4 : Enrichir les top chunks avec les voisins ═══════════════════
    enriched: List[Dict] = []
    for chunk in chunks[:5]:
        neighbors = _get_neighbor_chunks(
            client, chunk["doc_id"], chunk["chunk_idx"]
        )
        prev_text = neighbors[0][0] if len(neighbors) > 0 and chunk["chunk_idx"] > 0 else ""
        next_text = neighbors[-1][0] if len(neighbors) > 0 else ""

        if prev_text or next_text:
            combined = ""
            if prev_text:
                combined += prev_text[-500:] + "\n\n"
            combined += chunk["chunk_text"]
            if next_text:
                combined += "\n\n" + next_text[:500]
            chunk["chunk_text"] = combined

        enriched.append(chunk)

    # Ajouter les chunks restants (sans enrichissement)
    for chunk in chunks[5:]:
        enriched.append(chunk)

    chunks = enriched

    # ═══ Alt.9 : Reformulation si score faible ══════════════════════════════
    if chunks and chunks[0]["score"] < 0.65:
        reformulated = _reformulate_query(query)
        if reformulated:
            log.info(f"  Alt.9 reformulation: '{query[:40]}' → '{reformulated[:40]}'")
            try:
                ref_embedding = model.encode([reformulated])[0].tolist()
                _ref_qr = client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=ref_embedding,
                    query_filter=base_filter,
                    limit=top_k * 3,
                    with_payload=True,
                )
                for sp in _ref_qr.points:
                    text, meta = _payload_to_meta(sp.payload)
                    similarity = float(sp.score)
                    _add_chunk(text, meta, similarity, similarity + 0.05, "reformulated")

                # Re-trier
                chunks.sort(key=lambda x: x["score"], reverse=True)
            except Exception as e:
                log.debug(f"Alt.9 search reformulé échoué: {e}")

    # ═══ Alt.7 : Re-ranking Haiku si score intermédiaire ════════════════════
    if chunks and 0.5 < chunks[0]["score"] < 0.8:
        chunks = _rerank_with_llm(query, chunks, top_n=min(top_k, len(chunks)))

    return chunks[:top_k]


def format_context(chunks: List[Dict], max_total_chars: int = 6000) -> str:
    """Formate les chunks en contexte pour le LLM."""
    context_parts = []
    total_chars = 0

    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "")
        title = chunk.get("title", "")
        date = chunk.get("date", "")
        ecli = chunk.get("ecli", "")
        text = chunk.get("chunk_text", "")

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
            remaining = max_total_chars - total_chars - len(header) - 10
            if remaining > 100:
                chunk_text = f"{header}\n{text[:remaining]}..."
                context_parts.append(chunk_text)
            break

        context_parts.append(chunk_text)
        total_chars += len(chunk_text)

    return "\n\n---\n\n".join(context_parts)


if __name__ == "__main__":
    query = "Quelles sont les conditions de validité d'un licenciement en droit belge ?"
    print(f"Requête : {query}\n")

    try:
        results = retrieve(query, top_k=5)
        print(f"{len(results)} chunks trouvés\n")
        for r in results:
            print(f"  [{r['source']}] {r['title'][:60]} | score={r['score']:.3f}")
            print(f"  {r['chunk_text'][:200]}...\n")
    except RuntimeError as e:
        print(f"Erreur : {e}")
