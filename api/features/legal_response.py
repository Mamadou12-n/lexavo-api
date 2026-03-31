"""Lexavo Reponses — Generateur de reponses juridiques.
L'utilisateur recoit un courrier agressif -> Lexavo genere une reponse appropriee."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("legal_response")

RESPONSE_PROMPT = """Tu es Lexavo Reponses, un generateur de modeles de reponse juridique belge.

MISSION : A partir d'un courrier recu (proprietaire, employeur, huissier, administration),
generer un modele de reponse professionnel avec les articles de loi pertinents.

FORMAT DE REPONSE (JSON strict) :
{
  "response_letter": "Le texte complet de la lettre de reponse",
  "tone": "formal|firm|conciliatory",
  "key_arguments": ["Argument 1 avec base legale", "Argument 2"],
  "legal_references": [
    {"article": "Art. X Loi du DD/MM/YYYY", "relevance": "Pourquoi cet article s'applique"}
  ],
  "sender_type_detected": "proprietaire|employeur|huissier|administration|banque|autre",
  "urgency": "low|medium|high",
  "next_steps": ["Etape suivante 1", "Etape 2"]
}

REGLES :
1. Ce n'est PAS un courrier d'avocat — c'est un modele de lettre type
2. Formule de type : "En application de l'article X, je vous informe que..."
3. Ton professionnel et ferme mais respectueux
4. Toujours terminer par "Je vous prie d'agreer..."
5. Disclaimer : "Ce modele ne constitue pas un acte d'avocat."
6. Cite les textes de loi belges applicables"""


LETTER_TYPES = {
    "proprietaire": "droit_immobilier",
    "employeur": "droit_travail",
    "huissier": "droit_civil",
    "administration": "droit_administratif",
    "banque": "droit_commercial",
}


def generate_response(
    received_text: str,
    user_context: Optional[str] = None,
    mock: bool = False,
) -> dict:
    """Genere une reponse juridique a un courrier recu.

    Args:
        received_text: Le texte du courrier recu
        user_context: Contexte additionnel de l'utilisateur
        mock: Mode test
    """
    if len(received_text.strip()) < 30:
        raise ValueError("Le courrier est trop court (minimum 30 caracteres)")

    if mock:
        return {
            "response_letter": "Madame, Monsieur,\n\nPar la presente, je fais suite a votre courrier du [date]. En application de l'article [X], je vous informe que [reponse].\n\nJe vous prie d'agreer l'expression de mes salutations distinguees.",
            "tone": "firm",
            "key_arguments": ["Argument de test base sur l'article X"],
            "legal_references": [
                {"article": "Art. 1 Code civil", "relevance": "Applicable au litige (test)"}
            ],
            "sender_type_detected": "proprietaire",
            "urgency": "medium",
            "next_steps": ["Envoyer par recommande", "Conserver une copie"],
            "disclaimer": "Ce modele ne constitue pas un acte d'avocat. En cas de litige complexe, consultez un professionnel.",
        }

    # RAG pour le contexte juridique
    from rag.retriever import retrieve
    chunks = retrieve(
        query=f"reponse juridique courrier {received_text[:200]}",
        top_k=6,
    )

    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')}] {c.get('chunk_text', '')}"
        for c in chunks
    )

    user_info = f"\n\nCONTEXTE DE L'UTILISATEUR :\n{user_context}" if user_context else ""

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("analysis")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=RESPONSE_PROMPT,
        messages=[{
            "role": "user",
            "content": f"COURRIER RECU :\n\n{received_text}{user_info}\n\n---\nSOURCES JURIDIQUES :\n{context}"
        }],
    )

    raw = response.content[0].text.strip()
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = {
            "response_letter": raw,
            "tone": "formal",
            "key_arguments": [],
            "legal_references": [],
            "sender_type_detected": "autre",
            "urgency": "medium",
            "next_steps": [],
        }

    result["disclaimer"] = "Ce modele ne constitue pas un acte d'avocat. En cas de litige complexe, consultez un professionnel."
    result["sources"] = [
        {"source": c.get("source", ""), "title": c.get("title", "")}
        for c in chunks[:4]
    ]
    return result
