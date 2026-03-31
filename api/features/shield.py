"""Lexavo Shield — Analyse de contrats avant signature.
Feu tricolore : vert (signe) / orange (attention) / rouge (clause illegale)."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("shield")

CONTRACT_PATTERNS = {
    "bail": r"(?i)\b(bail|bailleur|preneur|loyer|locataire|r[ée]sidence principale)\b",
    "travail": r"(?i)\b(contrat de travail|employeur|travailleur|salaire|licenciement|pr[ée]avis)\b",
    "vente": r"(?i)\b(contrat de vente|vendeur|acheteur|prix de vente|bien vendu)\b",
}


def detect_contract_type(text: str) -> str:
    scores = {}
    for ctype, pattern in CONTRACT_PATTERNS.items():
        matches = re.findall(pattern, text)
        scores[ctype] = len(matches)
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


TYPE_TO_BRANCH = {
    "bail": "droit_immobilier",
    "travail": "droit_travail",
    "vente": "droit_civil",
    "general": None,
}


SHIELD_SYSTEM_PROMPT = """Tu es Lexavo Shield, un outil d'analyse de contrats belges.

MISSION : Analyser chaque clause du contrat et attribuer un feu tricolore :
- VERT : La clause est conforme au droit belge
- ORANGE : La clause merite attention (ambigue, inhabituelle, desavantageuse)
- ROUGE : La clause contient un element contraire a une disposition legale imperative

REGLES STRICTES :
1. Tu fournis de l'INFORMATION JURIDIQUE, pas un conseil juridique
2. Cite TOUJOURS l'article de loi applicable quand tu identifies un probleme
3. Formule : "L'article X prevoit que..." et NON "vous devez..." ou "je vous conseille..."
4. Si tu n'es pas sur, classe en ORANGE avec explication
5. Reponds UNIQUEMENT en JSON valide

FORMAT DE REPONSE (JSON strict) :
{
  "verdict": "green|orange|red",
  "summary": "Resume en 2-3 phrases du contrat",
  "clauses": [
    {
      "clause_text": "Le texte exact de la clause",
      "status": "green|orange|red",
      "explanation": "Explication claire en langage simple",
      "legal_basis": "Article X de la Loi du DD/MM/YYYY"
    }
  ]
}

Le verdict global est : ROUGE si au moins une clause est rouge, ORANGE si au moins une est orange, VERT si toutes sont vertes."""


def analyze_contract_text(
    text: str,
    contract_type: Optional[str] = None,
    mock: bool = False,
) -> dict:
    if len(text.strip()) < 50:
        raise ValueError("Le texte du contrat est trop court (minimum 50 caracteres)")

    detected_type = contract_type or detect_contract_type(text)

    if mock:
        return {
            "verdict": "orange",
            "summary": "Contrat analyse en mode test.",
            "clauses": [
                {
                    "clause_text": "Clause de test",
                    "status": "green",
                    "explanation": "Clause conforme (test)",
                    "legal_basis": None,
                }
            ],
            "contract_type_detected": detected_type,
            "sources": [],
        }

    from rag.retriever import retrieve
    branch = TYPE_TO_BRANCH.get(detected_type)
    source_filter = None
    if branch:
        from rag.branches import BRANCHES
        branch_config = BRANCHES.get(branch, {})
        source_filter = branch_config.get("source_filter")

    chunks = retrieve(
        query=f"clauses illegales contrat {detected_type} droit belge",
        top_k=8,
        source_filter=source_filter,
    )

    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')} — {c.get('title', '')}]\n{c.get('chunk_text', '')}"
        for c in chunks
    )

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("contract", len(text))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SHIELD_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"CONTRAT A ANALYSER (type detecte : {detected_type}) :\n\n"
                    f"{text}\n\n"
                    f"---\n\nSOURCES JURIDIQUES BELGES PERTINENTES :\n\n{context}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = {
            "verdict": "orange",
            "summary": raw[:200],
            "clauses": [],
        }

    result["contract_type_detected"] = detected_type
    result["sources"] = [
        {
            "doc_id": c.get("doc_id", ""),
            "source": c.get("source", ""),
            "title": c.get("title", ""),
            "date": c.get("date", ""),
            "ecli": c.get("ecli", ""),
            "url": c.get("url", ""),
            "similarity": c.get("similarity", 0.0),
        }
        for c in chunks[:5]
    ]

    return result
