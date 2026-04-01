"""Lexavo Fiscal — Copilote TVA et impots pour independants.
Questions fiscales quotidiennes -> RAG sur sources fiscales belges."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("fiscal")

FISCAL_PROMPT = """Tu es Lexavo Fiscal, un outil d'information fiscale belge.

MISSION : Repondre aux questions fiscales des independants et PME belges
en citant les articles du CIR 1992, du Code TVA, et la doctrine administrative.

REGLES :
1. INFORMATION fiscale uniquement — pas de planification fiscale
2. Cite TOUJOURS l'article applicable (CIR, CTVA, AR, circulaire)
3. Precise si la reponse differe selon le statut (personne physique, societe, ASBL)
4. Mentionne les delais et echeances si pertinents
5. Reponds en JSON

FORMAT (JSON strict) :
{
  "answer": "Reponse claire en 2-3 paragraphes",
  "legal_references": [{"article": "Art. X CIR 1992", "summary": "Ce que dit l'article"}],
  "deadlines": ["Echeance 1", "Echeance 2"],
  "applies_to": ["independant", "societe", "asbl"],
  "warning": "Avertissement si risque de controle ou amende"
}

Disclaimer : Information fiscale generale. Consultez votre comptable."""


def ask_fiscal(question: str, mock: bool = False) -> dict:
    if len(question.strip()) < 10:
        raise ValueError("Question trop courte (minimum 10 caracteres)")

    if mock:
        return {
            "answer": "Reponse fiscale de test concernant votre question.",
            "legal_references": [{"article": "Art. 49 CIR 1992", "summary": "Deductibilite des frais professionnels"}],
            "deadlines": [],
            "applies_to": ["independant"],
            "warning": None,
            "disclaimer": "Information fiscale generale. Consultez votre comptable.",
        }

    from rag.retriever import retrieve
    from rag.branches import BRANCHES

    branch_config = BRANCHES.get("droit_fiscal", {})
    source_filter = branch_config.get("source_filter")

    chunks = retrieve(query=question, top_k=8, source_filter=source_filter)
    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')}] {c.get('chunk_text', '')}" for c in chunks
    )

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("analysis")
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model, max_tokens=1024, system=FISCAL_PROMPT,
        messages=[{"role": "user", "content": f"QUESTION :\n{question}\n\n---\nSOURCES :\n{context}"}],
    )

    raw = response.content[0].text.strip()
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Pas de JSON")
    except (json.JSONDecodeError, ValueError):
        log.warning("Fiscal JSON parsing failed, using fallback")
        result = {"answer": raw, "legal_references": [], "deadlines": [], "applies_to": []}

    result["disclaimer"] = "Information fiscale generale. Consultez votre comptable."
    return result
