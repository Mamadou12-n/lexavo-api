"""Lexavo Shield — Analyse de contrats avant signature.
Feu tricolore : vert (signe) / orange (attention) / rouge (clause illegale).
Score de confiance /100, regionalisation, 10 types de contrats."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("shield")

# ─── 10 types de contrats detectables ────────────────────────────────────────

CONTRACT_PATTERNS = {
    "bail": r"(?i)\b(bail|bailleur|preneur|loyer|locataire|r[ée]sidence principale|garantie locative)\b",
    "travail": r"(?i)\b(contrat de travail|employeur|travailleur|salaire|licenciement|pr[ée]avis|CCT|commission paritaire)\b",
    "vente": r"(?i)\b(contrat de vente|vendeur|acheteur|prix de vente|bien vendu|compromis)\b",
    "prestation": r"(?i)\b(prestation de services?|prestataire|client|honoraires|mission|livrable)\b",
    "nda": r"(?i)\b(confidentialit[ée]|non[- ]divulgation|NDA|secret|information confidentielle)\b",
    "cgv": r"(?i)\b(conditions g[ée]n[ée]rales|CGV|CGU|vente [àa] distance|e-commerce|consommateur)\b",
    "licence": r"(?i)\b(licence|conc[ée]dant|licenci[ée]|droit d'utilisation|logiciel|propri[ée]t[ée] intellectuelle)\b",
    "association": r"(?i)\b(ASBL|association|membre|assembl[ée]e g[ée]n[ée]rale|conseil d'administration|statuts)\b",
    "mandat": r"(?i)\b(mandat|mandant|mandataire|procuration|repr[ée]sentation)\b",
    "pret": r"(?i)\b(pr[eê]t|emprunteur|cr[ée]ancier|int[ée]r[eê]ts|remboursement|capital emprunt[ée])\b",
}


def detect_contract_type(text: str) -> str:
    """Detecte le type de contrat par analyse des termes juridiques."""
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
    "prestation": "droit_commercial",
    "nda": "droit_commercial",
    "cgv": "droit_commercial",
    "licence": "droit_propriete_intellectuelle",
    "association": "droit_commercial",
    "mandat": "droit_civil",
    "pret": "droit_civil",
    "general": None,
}

# ─── Contexte regional ──────────────────────────────────────────────────────

REGION_CONTEXT = {
    "bruxelles": """Region de Bruxelles-Capitale :
- Bail de residence principale : Ordonnance du 27/07/2017 (Code bruxellois du logement)
- Preavis de sortie : 3 mois pour bail de 9 ans, 1 mois pour bail de courte duree
- Garantie locative : max 2 mois de loyer, deposee sur compte bloque ou via assurance""",
    "wallonie": """Region wallonne :
- Bail de residence principale : Decret du 15/03/2018 relatif au bail d'habitation
- Preavis de sortie : 3 mois (bail 9 ans), 3 mois (courte duree apres 1 an)
- Garantie locative : max 2 mois, compte bloque ou garantie bancaire
- PEB obligatoire""",
    "flandre": """Region flamande :
- Bail de residence principale : Vlaams Woninghuurdecreet du 09/11/2018
- Preavis de sortie : 3 mois (bail 9 ans)
- Garantie locative : max 3 mois de loyer
- Conformiteattest verplicht""",
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
6. Attribue un score de confiance global de 0 a 100 (100 = toutes clauses vertes)

FORMAT DE REPONSE (JSON strict) :
{
  "verdict": "green|orange|red",
  "score": 75,
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

Le verdict global est : ROUGE si au moins une clause est rouge, ORANGE si au moins une est orange, VERT si toutes sont vertes.
Le score est calcule en pondérant : vert=100%, orange=50%, rouge=0%, rapporte au nombre de clauses."""


def analyze_contract_text(
    text: str,
    contract_type: Optional[str] = None,
    region: Optional[str] = None,
    mock: bool = False,
) -> dict:
    """Analyse un contrat et retourne le verdict feu tricolore.

    Args:
        text: Texte du contrat (min 50 caracteres)
        contract_type: Type force (bail, travail, vente, etc.) ou auto-detect
        region: Region belge (bruxelles, wallonie, flandre) pour le droit regional
        mock: Mode test sans appel API
    """
    if len(text.strip()) < 50:
        raise ValueError("Le texte du contrat est trop court (minimum 50 caracteres)")

    # Limite de taille pour controler les couts
    if len(text) > 50000:
        text = text[:50000]
        log.warning("Contrat tronque a 50000 caracteres")

    detected_type = contract_type or detect_contract_type(text)

    if mock:
        return {
            "verdict": "orange",
            "score": 65,
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

    # RAG : recuperer les sources juridiques pertinentes
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

    # Ajouter le contexte regional si disponible
    region_info = ""
    if region and region.lower() in REGION_CONTEXT:
        region_info = f"\n\nCONTEXTE REGIONAL :\n{REGION_CONTEXT[region.lower()]}"

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("contract", len(text))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        system=SHIELD_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"CONTRAT A ANALYSER (type detecte : {detected_type}) :\n\n"
                    f"{text}\n\n"
                    f"---\n\nSOURCES JURIDIQUES BELGES PERTINENTES :\n\n{context}"
                    f"{region_info}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Parse JSON avec gestion d'erreur robuste
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Pas de JSON dans la reponse")
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"JSON parsing echoue, fallback : {e}")
        result = {
            "verdict": "orange",
            "score": 50,
            "summary": raw[:300] if raw else "Analyse non disponible",
            "clauses": [],
        }

    # Calculer le score si absent
    if "score" not in result or not isinstance(result.get("score"), (int, float)):
        clauses = result.get("clauses", [])
        if clauses:
            score_map = {"green": 100, "orange": 50, "red": 0}
            total = sum(score_map.get(c.get("status", "orange"), 50) for c in clauses)
            result["score"] = round(total / len(clauses))
        else:
            result["score"] = 50

    result["contract_type_detected"] = detected_type
    result["region"] = region
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
