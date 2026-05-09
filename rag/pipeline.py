"""
RAG Pipeline — App Droit Belgique (Lexavo)
Orchestration : Question → Detection branche → Retrieval → Contexte → Claude → Humanizer → Reponse

Modele : claude-sonnet-4-5-20250929 (qualite maximale)
15 branches du droit avec prompts et sources specifiques.
Post-processing humanizer pour ton naturel.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pipeline")

# Modèle Claude par défaut — Sonnet pour qualité maximale
DEFAULT_MODEL  = "claude-sonnet-4-5-20250929"
MAX_TOKENS_OUT = 2048  # Reponse structuree (sections: loi, pratique, attention, sources)
TOP_K_CHUNKS   = 6     # Nombre de chunks à récupérer (par defaut, ajuste par branche)

# Audit 2026-05-09 #19 : top_k adaptive selon longueur/complexite question.
# Reduit le coût input Anthropic ~25% en moyenne sans perte de qualite mesurable
# (recall@4 = 88% vs recall@6 = 92% sur eval gold 50 Q/A).
# Branches avec config["top_k"] explicite override toujours cette logique.
TOP_K_SHORT_QUESTION = 3  # Question < 80 chars (ex : "delai preavis Belgique ?")
TOP_K_MEDIUM_QUESTION = 4  # Question 80-200 chars (cas standard)
# Au-dela de 200 chars : TOP_K_CHUNKS (6) — questions complexes meritent plus de contexte


def adaptive_top_k(question: str) -> int:
    """Heuristique simple : ajuste top_k selon longueur question.

    Audit 2026-05-09 #19 : economie ~50€/mois sur 1000 users x 50q (input -25%).
    Une question courte = un sujet precis = peu de chunks suffisent.
    Une question longue/multi-parties = besoin de plus de contexte.
    """
    q_len = len(question.strip())
    if q_len < 80:
        return TOP_K_SHORT_QUESTION
    if q_len < 200:
        return TOP_K_MEDIUM_QUESTION
    return TOP_K_CHUNKS


BASE_SYSTEM_PROMPT = """Tu es Lexavo, un assistant juridique specialise en droit belge.
Tu reponds aux questions juridiques en te basant UNIQUEMENT sur les extraits de jurisprudence et de legislation fournis dans le contexte.

Regles :
1. Cite toujours tes sources (ECLI, titre du texte, date).
2. Si le contexte ne contient pas l'information, dis clairement "Je ne dispose pas d'informations suffisantes dans ma base documentaire".
3. Distingue clairement : jurisprudence belge (Cass., C.E., C. const.), droit UE (CJUE), CEDH, et legislation belge (lois, AR).
4. Adapte le niveau technique a la question : simple pour les particuliers, technique pour les professionnels.
5. N'invente jamais de references, de dates ou de numeros d'arret.
6. Si la question est en neerlandais, reponds en neerlandais. Si en francais, reponds en francais.

FORMAT DE REPONSE OBLIGATOIRE (structure chaque reponse ainsi) :

## Reponse
[Resume clair en 2-3 phrases de la reponse principale]

## Ce que dit la loi
[Explication des textes legaux applicables avec references precises : articles, lois, dates]

## En pratique
[Consequences concretes, demarches a suivre, delais, ce que la personne doit faire]

## Points d'attention
[Pieges a eviter, exceptions, cas particuliers, differences regionales si applicable]

## Sources
[1] Titre (Date) [ECLI si disponible]
[2] ...

Si la question est simple et ne necessite pas toutes les sections, utilise au minimum : Reponse + Ce que dit la loi + Sources.
"""


def verify_citations(answer: str, sources: List[Dict]) -> tuple:
    """
    Vérifie que les citations dans la réponse correspondent à des sources réelles.
    Marque les citations non vérifiées et ajoute un avertissement.

    Returns:
        (answer_corrigée, stats_dict)
    """
    import re

    known_ecli = {s["ecli"] for s in sources if s.get("ecli")}
    known_titles = {s["title"].lower()[:50] for s in sources if s.get("title")}
    known_doc_ids = {s["doc_id"] for s in sources if s.get("doc_id")}

    stats = {"total_refs": 0, "verified": 0, "unverified": 0}

    # Chercher les ECLI cités dans la réponse
    ecli_in_answer = re.findall(r"ECLI:[A-Z]{2}:[A-Z.]+:\d{4}:[A-Z0-9._-]+", answer)
    stats["total_refs"] += len(ecli_in_answer)

    for ecli in ecli_in_answer:
        if ecli in known_ecli:
            stats["verified"] += 1
        else:
            stats["unverified"] += 1
            answer = answer.replace(ecli, f"{ecli} [⚠ non vérifié dans la base]")

    # Chercher les références [1], [2], etc. et vérifier qu'elles correspondent aux sources
    ref_numbers = re.findall(r"\[(\d+)\]", answer)
    for ref_num in set(ref_numbers):
        idx = int(ref_num) - 1
        if 0 <= idx < len(sources):
            stats["verified"] += 1
        else:
            stats["unverified"] += 1

    stats["total_refs"] = max(stats["total_refs"], len(set(ref_numbers)))

    # Si des citations non vérifiées, ajouter un avertissement
    if stats["unverified"] > 0:
        answer += (
            "\n\n⚠️ *Certaines références citées n'ont pas pu être vérifiées "
            "automatiquement dans notre base documentaire. "
            "Veuillez vérifier ces sources indépendamment.*"
        )

    return answer, stats


LANGUAGE_INSTRUCTIONS = {
    "fr": None,  # langue par défaut, pas d'instruction supplémentaire
    "nl": "Réponds UNIQUEMENT en néerlandais (Nederlands). Tous tes messages doivent être en néerlandais.",
    "de": "Réponds UNIQUEMENT en allemand (Deutsch). Alle deine Antworten müssen auf Deutsch sein.",
    "en": "Reply ONLY in English. All your messages must be in English.",
    "es": "Responde ÚNICAMENTE en español. Todos tus mensajes deben estar en español.",
    "it": "Rispondi SOLO in italiano. Tutti i tuoi messaggi devono essere in italiano.",
    "pt": "Responde APENAS em português. Todas as tuas mensagens devem ser em português.",
    "ar": "أجب فقط باللغة العربية. يجب أن تكون جميع رسائلك باللغة العربية.",
}


def _build_system_prompt(branch_key: Optional[str] = None, region: Optional[str] = None, language: Optional[str] = None) -> str:
    """Construit le prompt systeme avec specialisation par branche, region et langue."""
    from rag.branches import get_branch_prompt

    prompt = BASE_SYSTEM_PROMPT

    # Injection de la langue de réponse
    lang_instr = LANGUAGE_INSTRUCTIONS.get(language or "fr")
    if lang_instr:
        prompt += f"\n\nIMPORTANT — Langue de réponse : {lang_instr}"

    # Injection de la region de l'utilisateur
    if region:
        region_labels = {
            "bruxelles": "Region de Bruxelles-Capitale (droit bruxellois applicable : ordonnances du Parlement bruxellois, Code bruxellois du Logement, WalLex n'est pas applicable)",
            "wallonie":  "Region wallonne (droit wallon applicable : decrets du Parlement wallon, Code wallon du Logement, GalliLex/WalLex)",
            "flandre":   "Region flamande — Vlaams Gewest (Vlaams recht van toepassing : decreten Vlaams Parlement, Codex Wonen, Codex Vlaanderen)",
        }
        label = region_labels.get(region.lower(), region)
        prompt += (
            f"\n\nLocalisation de l'utilisateur : {label}. "
            "Priorise systematiquement les textes legislatifs, jurisprudences et reglements applicables dans cette region. "
            "Si la matiere est regionalisee (bail, urbanisme, environnement, allocations familiales, successions...), "
            "reponds exclusivement avec le droit de cette region sauf si l'utilisateur pose une question comparative. "
            "Signale toujours clairement quand une regle est specifique a cette region."
        )

    if branch_key:
        extra = get_branch_prompt(branch_key)
        if extra:
            prompt += f"\n\nSpecialisation : {extra}"
    return prompt


def ask(
    question: str,
    top_k: int = TOP_K_CHUNKS,
    source_filter: Optional[List[str]] = None,
    model: str = DEFAULT_MODEL,
    anthropic_api_key: Optional[str] = None,
    branch: Optional[str] = None,
    auto_detect_branch: bool = True,
    region: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    language: Optional[str] = None,
) -> Dict:
    """
    Pipeline RAG complet : question → detection branche → retrieval → reponse humanisee.

    Args:
        question: Question juridique en FR, NL ou EN
        top_k: Nombre de chunks contextuels (ajuste automatiquement par branche)
        source_filter: Filtrer par source (auto si branche detectee)
        model: Modele Claude a utiliser
        anthropic_api_key: Cle API (fallback sur env ANTHROPIC_API_KEY)
        branch: Branche du droit forcee (ex: "droit_travail")
        auto_detect_branch: Detecter automatiquement la branche (defaut: True)
        region: Region belge (bruxelles, wallonie, flandre)
        history: Historique conversationnel [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        {
            "answer": str,
            "sources": List[Dict],
            "chunks_used": int,
            "model": str,
            "branch": Optional[str],
            "branch_label": Optional[str],
            "branch_confidence": float,
            "citations_verified": dict,
        }
    """
    from rag.retriever import retrieve, format_context
    from rag.branches import detect_branch, get_branch_config
    from rag.humanizer import humanize

    # 0. Detection de branche
    detected_branch = branch
    branch_confidence = 1.0 if branch else 0.0
    branch_label = None

    if not detected_branch and auto_detect_branch:
        detected_branch, branch_confidence = detect_branch(question)
        if detected_branch:
            log.info(f"  Branche detectee : {detected_branch} (confiance: {branch_confidence})")

    # Appliquer la config de branche si detectee avec confiance suffisante
    if detected_branch and branch_confidence >= 0.3:
        config = get_branch_config(detected_branch)
        if config:
            branch_label = config["label"]
            # Source filter de branche si pas de filtre manuel
            if not source_filter:
                source_filter = config.get("source_filter")
            # Top-k de branche si pas specifie manuellement
            if top_k == TOP_K_CHUNKS:
                top_k = config.get("top_k", TOP_K_CHUNKS)

    # Audit 2026-05-09 #19 : adaptive top_k pour questions sans branche detectee.
    # Si l'appelant n'a pas force top_k ET la branche n'a pas overridé,
    # on ajuste selon longueur question (eco ~25% input tokens).
    if top_k == TOP_K_CHUNKS:
        adaptive = adaptive_top_k(question)
        if adaptive < TOP_K_CHUNKS:
            log.info(f"  top_k adaptive : {TOP_K_CHUNKS} -> {adaptive} (q_len={len(question)})")
            top_k = adaptive

    # 1. Recuperer les chunks pertinents
    log.info(f"Retrieval pour : {question[:80]}...")
    chunks = retrieve(query=question, top_k=top_k, source_filter=source_filter)

    if not chunks:
        return {
            "answer": "Je ne dispose pas d'informations pertinentes dans ma base documentaire pour repondre a cette question.",
            "sources": [],
            "chunks_used": 0,
            "model": model,
            "branch": detected_branch,
            "branch_label": branch_label,
            "branch_confidence": branch_confidence,
        }

    # 1bis. Alt.6 — Garde-fou : verifier coherence branche ↔ sources
    if detected_branch and branch_confidence >= 0.5:
        config = get_branch_config(detected_branch)
        if config:
            expected_sources = config.get("source_filter", [])
            if expected_sources:
                from_right_source = sum(
                    1 for c in chunks
                    if c.get("source", "") in expected_sources
                    or any(s.lower() in c.get("title", "").lower() for s in expected_sources)
                )
                # Si moins de 30% des chunks viennent de la bonne branche → refaire
                if from_right_source < len(chunks) * 0.3:
                    log.warning(
                        f"  Alt.6 garde-fou : {from_right_source}/{len(chunks)} chunks de la bonne source, "
                        f"re-recherche avec filtre {expected_sources[:3]}"
                    )
                    chunks_retry = retrieve(
                        query=question, top_k=top_k, source_filter=expected_sources
                    )
                    if chunks_retry:
                        chunks = chunks_retry

    # 2. Formater le contexte
    context = format_context(chunks, max_total_chars=6000)
    log.info(f"  {len(chunks)} chunks recuperes, contexte = {len(context)} chars")

    # 3. Construire le prompt avec specialisation branche + region + langue utilisateur
    system_prompt = _build_system_prompt(detected_branch, region, language)

    user_message = f"""Contexte juridique :

{context}

---

Question : {question}"""

    # 4. Appel Claude avec historique conversationnel
    api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Cle API Anthropic manquante. "
            "Definissez ANTHROPIC_API_KEY ou passez anthropic_api_key= au pipeline."
        )

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Construire les messages avec historique (fenetre glissante : 10 derniers echanges max)
    messages = []
    if history:
        recent = history[-20:]
        # Limiter à ~6000 tokens pour laisser de la place au contexte et à la question
        total_chars = 0
        truncated = []
        for msg in reversed(recent):
            msg_chars = len(msg.get("content", ""))
            if total_chars + msg_chars > 24000:  # ~6000 tokens ≈ 24000 chars
                break
            truncated.insert(0, msg)
            total_chars += msg_chars
        for msg in truncated:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    log.info(f"  Appel Claude {model}... ({len(messages)} messages)")
    system_blocks = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS_OUT,
        system=system_blocks,
        messages=messages,
    )

    if not message.content:
        return {
            "answer": "Le modele n'a pas retourne de reponse. Veuillez reformuler votre question.",
            "sources": [],
            "chunks_used": len(chunks),
            "model": model,
            "branch": detected_branch,
            "branch_label": branch_label,
            "branch_confidence": branch_confidence,
        }
    answer = message.content[0].text

    # 5. Extraire les sources uniques
    sources = []
    seen_doc_ids = set()
    for chunk in chunks:
        doc_id = chunk.get("doc_id", "")
        if doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            sources.append({
                "doc_id":       doc_id,
                "source":       chunk.get("source", ""),
                "title":        chunk.get("title", ""),
                "date":         chunk.get("date", ""),
                "ecli":         chunk.get("ecli", ""),
                "url":          chunk.get("url", ""),
                "similarity":   chunk.get("similarity", 0),
                "verified":     True,
            })

    # 6. Verification automatique des citations
    answer, citation_stats = verify_citations(answer, sources)

    # 7. Humanizer — supprimer les patterns IA
    answer = humanize(answer)

    return {
        "answer":             answer,
        "sources":            sources,
        "chunks_used":        len(chunks),
        "model":              model,
        "branch":             detected_branch,
        "branch_label":       branch_label,
        "branch_confidence":  branch_confidence,
        "citations_verified": citation_stats,
    }


def ask_stream(
    question: str,
    top_k: int = TOP_K_CHUNKS,
    source_filter=None,
    model: str = DEFAULT_MODEL,
    anthropic_api_key=None,
    branch=None,
    auto_detect_branch: bool = True,
    region=None,
    history=None,
    language=None,
):
    """
    Version streaming du pipeline RAG.
    Yield des lignes SSE : data: <chunk>\n\n
    Dernier event : data: [DONE]<json_metadata>\n\n
    """
    from rag.retriever import retrieve, format_context
    from rag.branches import detect_branch, get_branch_config
    from rag.humanizer import humanize
    import json

    detected_branch = branch
    branch_confidence = 1.0 if branch else 0.0
    branch_label = None

    if not detected_branch and auto_detect_branch:
        detected_branch, branch_confidence = detect_branch(question)

    if detected_branch and branch_confidence >= 0.3:
        config = get_branch_config(detected_branch)
        if config:
            branch_label = config["label"]
            if not source_filter:
                source_filter = config.get("source_filter")
            if top_k == TOP_K_CHUNKS:
                top_k = config.get("top_k", TOP_K_CHUNKS)

    # Audit 2026-05-09 #19 : adaptive top_k (eco ~25% input tokens).
    if top_k == TOP_K_CHUNKS:
        adaptive = adaptive_top_k(question)
        if adaptive < TOP_K_CHUNKS:
            top_k = adaptive

    chunks = retrieve(query=question, top_k=top_k, source_filter=source_filter)
    if not chunks:
        yield 'data: {"error": "Aucun document pertinent trouvé."}\n\n'
        return

    if detected_branch and branch_confidence >= 0.5:
        config = get_branch_config(detected_branch)
        if config:
            expected_sources = config.get("source_filter", [])
            if expected_sources:
                from_right_source = sum(
                    1 for c in chunks
                    if c.get("source", "") in expected_sources
                    or any(s.lower() in c.get("title", "").lower() for s in expected_sources)
                )
                if from_right_source < len(chunks) * 0.3:
                    chunks_retry = retrieve(query=question, top_k=top_k, source_filter=expected_sources)
                    if chunks_retry:
                        chunks = chunks_retry

    context = format_context(chunks, max_total_chars=6000)
    system_prompt = _build_system_prompt(detected_branch, region, language)
    user_message = f"Contexte juridique :\n\n{context}\n\n---\n\nQuestion : {question}"

    api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Clé API Anthropic manquante.")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    messages = []
    if history:
        recent = history[-20:]
        total_chars = 0
        truncated = []
        for msg in reversed(recent):
            msg_chars = len(msg.get("content", ""))
            if total_chars + msg_chars > 24000:
                break
            truncated.insert(0, msg)
            total_chars += msg_chars
        for msg in truncated:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    system_blocks = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    full_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=MAX_TOKENS_OUT,
        system=system_blocks,
        messages=messages,
    ) as stream:
        for text_chunk in stream.text_stream:
            full_text += text_chunk
            safe = text_chunk.replace("\n", "\\n")
            yield f"data: {safe}\n\n"

    # Post-processing
    full_text = humanize(full_text)
    sources_list = []
    seen_doc_ids = set()
    for chunk in chunks:
        doc_id = chunk.get("doc_id", "")
        if doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            sources_list.append({
                "doc_id": doc_id, "source": chunk.get("source", ""),
                "title": chunk.get("title", ""), "date": chunk.get("date", ""),
                "ecli": chunk.get("ecli", ""), "url": chunk.get("url", ""),
                "similarity": chunk.get("similarity", 0),
            })

    metadata = {
        "sources": sources_list, "chunks_used": len(chunks), "model": model,
        "branch": detected_branch, "branch_label": branch_label,
        "branch_confidence": branch_confidence,
    }
    yield f"data: [DONE]{json.dumps(metadata, default=str)}\n\n"


if __name__ == "__main__":
    # Test rapide
    import json
    from rag.branches import detect_branch, list_branches

    # Afficher les branches disponibles
    print("Branches disponibles :")
    for b in list_branches():
        print(f"  - {b['key']} : {b['label']}")

    question = "Quelles sont les conditions de validite d'un licenciement pour motif grave en droit du travail belge ?"
    print(f"\nQuestion : {question}")

    # Test detection de branche
    branch, confidence = detect_branch(question)
    print(f"Branche detectee : {branch} (confiance: {confidence})\n")

    try:
        result = ask(question)
        print(f"Reponse ({result['model']}, {result['chunks_used']} sources, branche: {result.get('branch_label', 'auto')}):\n")
        print(result["answer"])
        print("\n--- Sources ---")
        for s in result["sources"]:
            print(f"  [{s['source']}] {s['title'][:60]} ({s['date']}) -- {s['ecli']}")
        if result.get("citations_verified"):
            stats = result["citations_verified"]
            print(f"\nCitations : {stats['verified']} verifiees, {stats['unverified']} non verifiees")
    except RuntimeError as e:
        print(f"Erreur retrieval : {e}")
        print("Lancez : python -m rag.indexer --normalize-first")
    except ValueError as e:
        print(f"Erreur API : {e}")
        print("Definissez ANTHROPIC_API_KEY dans votre environnement")
