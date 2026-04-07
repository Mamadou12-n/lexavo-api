"""Lexavo Defend — "Je veux agir"
Contestation d'amendes, mises en demeure, recours administratifs.
Detection automatique du type de situation, generation de documents.

REGLE INVIOLABLE : ZERO invention, ZERO fausse source, ZERO hallucination.
Chaque article cite DOIT exister dans la base RAG (43,005 chunks).
"""

import json
import os
import re
import logging
from typing import Optional, List
from datetime import datetime

log = logging.getLogger("defend")

# ─── Categories de situations ────────────────────────────────────────────────

DEFEND_CATEGORIES = [
    {
        "id": "amende",
        "label": "Contester une amende",
        "icon": "🚗",
        "description": "Radar, stationnement, STIB/TEC/De Lijn, SAC communale",
        "keywords": ["amende", "pv", "radar", "stationnement", "stib", "tec", "de lijn", "sac", "infraction", "vitesse", "feu rouge", "parking"],
        "branch": "droit_penal",
    },
    {
        "id": "consommation",
        "label": "Probleme de consommation",
        "icon": "🛒",
        "description": "Refus remboursement, clause abusive, facturation incorrecte",
        "keywords": ["remboursement", "rembourser", "achat", "commande", "e-commerce", "garantie", "defaut", "clause abusive", "facture", "surfacturation"],
        "branch": "droit_commercial",
    },
    {
        "id": "bail",
        "label": "Probleme de logement",
        "icon": "🏠",
        "description": "Caution non rendue, proprietaire, logement insalubre",
        "keywords": ["bail", "caution", "garantie locative", "proprietaire", "loyer", "insalubre", "reparation", "etat des lieux", "expulsion", "indexation"],
        "branch": "droit_immobilier",
    },
    {
        "id": "travail",
        "label": "Conflit au travail",
        "icon": "👷",
        "description": "Licenciement, accident de travail, harcelement",
        "keywords": ["licenciement", "licencie", "preavis", "salaire", "employeur", "harcelement", "accident travail", "heures supplementaires", "conge", "c4"],
        "branch": "droit_travail",
    },
    {
        "id": "huissier",
        "label": "Lettre d'huissier",
        "icon": "📨",
        "description": "Repondre, contester une saisie, opposition",
        "keywords": ["huissier", "saisie", "commandement", "opposition", "dette", "creancier", "sommation", "execution"],
        "branch": "droit_civil",
    },
    {
        "id": "social",
        "label": "Droits sociaux",
        "icon": "🏥",
        "description": "Mutuelle, CPAS, allocations, chomage",
        "keywords": ["mutuelle", "cpas", "allocation", "chomage", "onem", "maladie", "invalidite", "handicap", "aide sociale", "revenu integration"],
        "branch": "droit_securite_sociale",
    },
    {
        "id": "scolaire",
        "label": "Probleme scolaire",
        "icon": "🎓",
        "description": "Exclusion, refus d'inscription, recours",
        "keywords": ["ecole", "exclusion", "inscription", "renvoi", "discipline", "enseignement", "eleve", "parent", "conseil classe"],
        "branch": "droit_administratif",
    },
    {
        "id": "fiscal",
        "label": "Contestation fiscale",
        "icon": "💰",
        "description": "SPF Finances, taxe communale, role d'imposition",
        "keywords": ["impot", "taxe", "spf finances", "enrolement", "degrevement", "reclamation", "precompte", "additionnel", "communale"],
        "branch": "droit_fiscal",
    },
]


def get_defend_categories() -> list:
    """Retourne les categories de situations contestables."""
    return DEFEND_CATEGORIES


def detect_situation_type(description: str) -> dict:
    """Detecte automatiquement le type de situation a partir de la description."""
    text_lower = description.lower()
    scores = {}

    for cat in DEFEND_CATEGORIES:
        score = 0
        for kw in cat["keywords"]:
            if kw in text_lower:
                score += 1
        scores[cat["id"]] = score

    if not scores or max(scores.values()) == 0:
        return {"category": "general", "confidence": 0.0, "branch": None}

    best = max(scores, key=scores.get)
    best_cat = next(c for c in DEFEND_CATEGORIES if c["id"] == best)
    confidence = min(1.0, scores[best] / 3.0)

    return {
        "category": best,
        "category_label": best_cat["label"],
        "confidence": round(confidence, 2),
        "branch": best_cat["branch"],
        "icon": best_cat["icon"],
    }


DEFEND_SYSTEM_PROMPT = """Tu es Lexavo Defend, un assistant juridique belge specialise dans la contestation et les recours.

MISSION : Analyser la situation de l'utilisateur et generer un document de contestation/recours/mise en demeure.

REGLES INVIOLABLES :
1. ZERO INVENTION — ne cite JAMAIS un article de loi, un arret, ou une reference que tu ne trouves pas dans le contexte fourni
2. ZERO HALLUCINATION — si tu ne trouves pas l'information dans les sources, dis clairement "Je ne dispose pas de cette information dans ma base documentaire"
3. Tu fournis de l'INFORMATION JURIDIQUE, pas un conseil juridique
4. Formule : "L'article X prevoit que..." et NON "vous devez..." ou "je vous conseille..."
5. Chaque document genere DOIT citer ses sources verificables

FORMAT DE REPONSE (JSON strict) :
{
  "situation_analysis": "Analyse de la situation en 3-4 phrases",
  "applicable_law": [
    {"article": "Art. X Loi du DD/MM/YYYY", "content": "Ce que prevoit cet article", "source": "Nom de la source"}
  ],
  "contestation_possible": true/false,
  "success_probability": "haute/moyenne/faible",
  "document_type": "contestation|mise_en_demeure|recours|reclamation|opposition",
  "document_text": "Texte complet du document a envoyer (lettre formelle)",
  "recipient": "A qui envoyer : nom + adresse",
  "deadline": "Delai legal pour agir (ex: 30 jours)",
  "next_steps": ["Etape 1", "Etape 2", "Etape 3"],
  "cost_estimate": "Gratuit / estimation si frais"
}"""


def analyze_and_generate(
    description: str,
    category: Optional[str] = None,
    region: Optional[str] = None,
    user_name: str = "",
    user_address: str = "",
    photos_base64: Optional[List[str]] = None,
    mock: bool = False,
) -> dict:
    """Analyse la situation et genere le document de contestation.

    REGLE INVIOLABLE : ZERO invention. Tout est base sur les sources RAG.
    """
    if len(description.strip()) < 20:
        raise ValueError("Decrivez votre situation en au moins 20 caracteres")

    # OCR des photos si fournies
    if photos_base64:
        try:
            from api.utils.ocr import extract_text_from_base64_list
            ocr_text = extract_text_from_base64_list(photos_base64)
            if ocr_text:
                description = f"{description}\n\n[Texte extrait des photos jointes]\n{ocr_text}"
        except Exception as e:
            log.warning(f"OCR photos defend ignoré : {e}")

    # Detecter le type de situation
    if category:
        detection = {"category": category, "confidence": 1.0, "branch": None}
        cat_info = next((c for c in DEFEND_CATEGORIES if c["id"] == category), None)
        if cat_info:
            detection["branch"] = cat_info["branch"]
            detection["category_label"] = cat_info["label"]
    else:
        detection = detect_situation_type(description)

    if mock:
        return {
            "detection": detection,
            "situation_analysis": "Analyse en mode test.",
            "applicable_law": [],
            "contestation_possible": True,
            "success_probability": "moyenne",
            "document_type": "contestation",
            "document_text": "Lettre de contestation (mode test)",
            "recipient": "Destinataire test",
            "deadline": "30 jours",
            "next_steps": ["Etape test"],
            "cost_estimate": "Gratuit",
            "sources": [],
            "disclaimer": "Lexavo est un assistant juridique. Il ne remplace pas un avocat.",
        }

    # RAG : recuperer les sources juridiques pertinentes
    from rag.retriever import retrieve
    branch = detection.get("branch")
    source_filter = None
    if branch:
        from rag.branches import BRANCHES
        branch_config = BRANCHES.get(branch, {})
        source_filter = branch_config.get("source_filter")

    query = f"contestation {detection.get('category', 'general')} droit belge procedure recours"
    chunks = retrieve(query=query, top_k=10, source_filter=source_filter)

    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')} — {c.get('title', '')}]\n{c.get('chunk_text', '')}"
        for c in chunks
    )

    # Region context
    region_info = ""
    if region:
        region_info = f"\nRegion de l'utilisateur : {region}. Applique le droit regional si la matiere est regionalisee."

    # Appel Claude
    from api.utils.model_router import select_model
    import anthropic

    model = select_model("defend", len(description))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non configurée")
    client = anthropic.Anthropic(api_key=api_key)

    user_info = ""
    if user_name:
        user_info += f"\nNom de l'utilisateur : {user_name}"
    if user_address:
        user_info += f"\nAdresse : {user_address}"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            system=DEFEND_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"SITUATION A ANALYSER :\n\n{description}\n\n"
                        f"Type detecte : {detection.get('category', 'general')} ({detection.get('category_label', '')})\n"
                        f"{user_info}{region_info}\n\n"
                        f"---\n\nSOURCES JURIDIQUES BELGES :\n\n{context}"
                    ),
                }
            ],
        )
    except Exception as e:
        log.error(f"Erreur API Claude: {e}")
        raise ValueError(f"Erreur lors de l'analyse: {e}")

    raw = response.content[0].text.strip()

    # Parse JSON robuste
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Pas de JSON")
    except (json.JSONDecodeError, ValueError):
        log.warning("Defend JSON parsing failed, using fallback")
        result = {
            "situation_analysis": raw[:500],
            "applicable_law": [],
            "contestation_possible": True,
            "success_probability": "indeterminee",
            "document_type": "contestation",
            "document_text": "",
            "recipient": "",
            "deadline": "Verifiez les delais legaux",
            "next_steps": [],
            "cost_estimate": "",
        }

    # Humanizer : post-processing pour un ton naturel
    from rag.humanizer import humanize
    if result.get("situation_analysis"):
        result["situation_analysis"] = humanize(result["situation_analysis"])
    if result.get("document_text"):
        # Le document formel ne doit PAS etre humanise (ton juridique requis)
        pass

    result["detection"] = detection
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
    result["disclaimer"] = "Lexavo est un assistant juridique. Il ne remplace pas un avocat. Verifiez toujours les informations avec un professionnel."
    result["generated_at"] = datetime.utcnow().isoformat()

    return result
