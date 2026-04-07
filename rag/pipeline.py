"""
RAG Pipeline — App Droit Belgique (Lexavo)
Orchestration : Question → Detection branche → Retrieval → Contexte → Claude → Humanizer → Reponse

Modele : claude-sonnet-4-6 (qualite maximale)
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
DEFAULT_MODEL  = "claude-sonnet-4-6"
MAX_TOKENS_OUT = 2048  # Reponse structuree (sections: loi, pratique, attention, sources)
TOP_K_CHUNKS   = 6     # Nombre de chunks à récupérer (par defaut, ajuste par branche)


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


def _build_system_prompt(branch_key: Optional[str] = None, region: Optional[str] = None) -> str:
    """Construit le prompt systeme avec specialisation par branche et region si detectees."""
    from rag.branches import get_branch_prompt

    prompt = BASE_SYSTEM_PROMPT

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

    # 3. Construire le prompt avec specialisation branche + region utilisateur
    system_prompt = _build_system_prompt(detected_branch, region)

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
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS_OUT,
        system=system_prompt,
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
