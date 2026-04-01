"""Lexavo Diagnostic — Questionnaire juridique personnalise.
6 questions -> rapport avec droits, risques et actions prioritaires."""

import json
import os
import re
import logging
from typing import Optional, List

log = logging.getLogger("diagnostic")

DIAGNOSTIC_QUESTIONS = [
    {
        "id": 1,
        "question": "Quel est le domaine de votre situation ?",
        "options": ["Travail/Emploi", "Logement/Bail", "Famille", "Fiscal/Impots", "Entreprise/Commercial", "Autre"],
    },
    {
        "id": 2,
        "question": "Quelle est la nature du probleme ?",
        "options": ["Litige en cours", "Prevention/Information", "Document a verifier", "Droits a connaitre", "Procedure a engager"],
    },
    {
        "id": 3,
        "question": "Depuis combien de temps dure cette situation ?",
        "options": ["Moins d'un mois", "1 a 6 mois", "6 mois a 1 an", "Plus d'un an", "Pas encore commence"],
    },
    {
        "id": 4,
        "question": "Avez-vous deja consulte un professionnel ?",
        "options": ["Non, jamais", "Oui, un avocat", "Oui, un syndicat/association", "Oui, un notaire", "Oui, un comptable"],
    },
    {
        "id": 5,
        "question": "Quel est l'enjeu financier estime ?",
        "options": ["Moins de 1.000 EUR", "1.000 - 5.000 EUR", "5.000 - 25.000 EUR", "Plus de 25.000 EUR", "Non financier"],
    },
    {
        "id": 6,
        "question": "Quelle est votre priorite ?",
        "options": ["Comprendre mes droits", "Resoudre rapidement", "Minimiser les couts", "Preparer un dossier", "Trouver un avocat"],
    },
]

DOMAIN_TO_BRANCH = {
    "Travail/Emploi": "droit_travail",
    "Logement/Bail": "droit_immobilier",
    "Famille": "droit_familial",
    "Fiscal/Impots": "droit_fiscal",
    "Entreprise/Commercial": "droit_commercial",
}

DIAGNOSTIC_PROMPT = """Tu es Lexavo Diagnostic, un outil de bilan juridique personnalise pour le droit belge.

A partir des reponses au questionnaire et du contexte juridique belge fourni, genere un rapport de diagnostic.

FORMAT DE REPONSE (JSON strict) :
{
  "title": "Diagnostic juridique — [domaine]",
  "situation_summary": "Resume de la situation en 2-3 phrases",
  "applicable_rights": [
    {"right": "Description du droit", "legal_basis": "Article ou loi applicable"}
  ],
  "risks": [
    {"risk": "Description du risque", "severity": "low|medium|high", "explanation": "Pourquoi"}
  ],
  "priority_actions": [
    {"action": "Action concrete a entreprendre", "deadline": "Delai si applicable", "priority": 1}
  ],
  "recommended_professional": "Type de professionnel recommande (avocat specialise en X, notaire, etc.)",
  "estimated_complexity": "simple|moderate|complex"
}

REGLES :
1. INFORMATION juridique uniquement, pas de conseil
2. Cite les articles de loi belges applicables
3. Sois concret et actionnable dans les priorites
4. Adapte le langage au niveau du citoyen"""


def get_questions() -> list:
    """Retourne la liste des questions du diagnostic."""
    return DIAGNOSTIC_QUESTIONS


def generate_diagnostic(answers: List[dict], mock: bool = False) -> dict:
    """Genere un rapport diagnostic a partir des reponses.

    Args:
        answers: Liste de {"question_id": int, "answer": str}
        mock: Mode test
    """
    if len(answers) < 3:
        raise ValueError("Minimum 3 reponses requises pour un diagnostic")

    # Extraire le domaine
    domain_answer = next((a["answer"] for a in answers if a["question_id"] == 1), "Autre")
    branch = DOMAIN_TO_BRANCH.get(domain_answer)

    if mock:
        return {
            "title": f"Diagnostic juridique — {domain_answer}",
            "situation_summary": "Situation analysee en mode test.",
            "applicable_rights": [
                {"right": "Droit de test", "legal_basis": "Art. 1 Code civil"}
            ],
            "risks": [
                {"risk": "Risque de test", "severity": "low", "explanation": "Test"}
            ],
            "priority_actions": [
                {"action": "Action de test", "deadline": "N/A", "priority": 1}
            ],
            "recommended_professional": "Avocat specialise",
            "estimated_complexity": "simple",
            "branch_detected": branch,
        }

    # Construire le contexte des reponses
    answers_text = "\n".join(
        f"Q{a['question_id']}: {next((q['question'] for q in DIAGNOSTIC_QUESTIONS if q['id'] == a['question_id']), '?')} -> {a['answer']}"
        for a in answers
    )

    # RAG pour le contexte juridique
    from rag.retriever import retrieve
    source_filter = None
    if branch:
        from rag.branches import BRANCHES
        branch_config = BRANCHES.get(branch, {})
        source_filter = branch_config.get("source_filter")

    query = f"droits et obligations {domain_answer} droit belge"
    chunks = retrieve(query=query, top_k=6, source_filter=source_filter)

    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')}] {c.get('chunk_text', '')}"
        for c in chunks
    )

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("diagnostic")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=DIAGNOSTIC_PROMPT,
        messages=[{
            "role": "user",
            "content": f"REPONSES AU QUESTIONNAIRE :\n{answers_text}\n\n---\nSOURCES JURIDIQUES :\n{context}"
        }],
    )

    raw = response.content[0].text.strip()
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Pas de JSON")
    except (json.JSONDecodeError, ValueError):
        log.warning("Diagnostic JSON parsing failed, using fallback")
        result = {"title": "Diagnostic", "situation_summary": raw[:300], "applicable_rights": [], "risks": [], "priority_actions": []}

    result["branch_detected"] = branch
    result["sources"] = [
        {"source": c.get("source", ""), "title": c.get("title", ""), "similarity": c.get("similarity", 0.0)}
        for c in chunks[:4]
    ]
    return result
