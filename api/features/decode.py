"""Lexavo Decode — Traducteur de documents d'Etat en langage clair."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("decode")

DECODE_PROMPT = """Tu es Lexavo Decode, un traducteur de documents administratifs belges.

MISSION : Traduire un document officiel (SPF, ONSS, commune, CPAS, etc.)
en langage simple qu'un citoyen belge sans formation juridique peut comprendre.

FORMAT DE REPONSE (JSON strict) :
{
  "plain_language": "Explication claire du document en 3-5 paragraphes",
  "key_points": ["Point cle 1", "Point cle 2", "Point cle 3"],
  "actions_required": ["Action a faire 1 avec deadline", "Action 2"],
  "deadlines": ["Date limite 1", "Date limite 2"],
  "document_type": "avis_imposition|decision_spf|courrier_onss|notification_commune|autre"
}

REGLES :
1. Explique CHAQUE terme technique entre parentheses
2. Mentionne les deadlines en gras
3. Liste les actions que le citoyen doit entreprendre
4. Ne donne aucun conseil juridique — informe uniquement"""


def decode_document(text: str, mock: bool = False) -> dict:
    if len(text.strip()) < 20:
        raise ValueError("Le document est trop court")

    if mock:
        return {
            "plain_language": "Ce document est un avis d'imposition (test).",
            "key_points": ["Revenu imposable determine", "Quotite exemptee appliquee"],
            "actions_required": [],
            "deadlines": [],
            "document_type": "avis_imposition",
        }

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("translation", len(text))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non configurée")
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=DECODE_PROMPT,
            messages=[{"role": "user", "content": f"DOCUMENT A TRADUIRE :\n\n{text}"}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude: {e}")
        raise ValueError(f"Erreur lors de l'analyse: {e}")

    raw = response.content[0].text.strip()
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Pas de JSON")
    except (json.JSONDecodeError, ValueError):
        log.warning("Decode JSON parsing failed, using fallback")
        result = {"plain_language": raw, "key_points": [], "actions_required": [], "deadlines": []}

    # Humanizer — ton naturel
    from rag.humanizer import humanize
    if result.get("plain_language"):
        result["plain_language"] = humanize(result["plain_language"])

    return result
