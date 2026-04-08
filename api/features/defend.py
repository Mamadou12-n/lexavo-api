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

# ─── Tons de lettre disponibles ──────────────────────────────────────────────

TONE_INSTRUCTIONS = {
    "formel": (
        "Ton juridique et formel. Langage soutenu, vocabulaire juridique précis. "
        "Phrases longues et structurées. Style d'un juriste professionnel."
    ),
    "ferme": (
        "Ton ferme et déterminé, sans agressivité mais clairement affirmé. "
        "Insiste sur les droits et les obligations légales de l'autre partie. "
        "Formules comme 'Je me vois dans l'obligation de...', 'Je vous mets en demeure de...'."
    ),
    "amical": (
        "Ton courtois et respectueux, langage accessible et non-conflictuel. "
        "Formulé comme une demande aimable plutôt qu'une exigence. "
        "Formules comme 'Je me permets de vous contacter...', 'Je reste disponible pour en discuter...'."
    ),
    "conciliant": (
        "Ton conciliant et ouvert au dialogue. Cherche une solution à l'amiable avant tout. "
        "Propose des alternatives et montre une volonté de résoudre à l'amiable. "
        "Formules comme 'Je souhaite trouver une solution satisfaisante pour les deux parties...'."
    ),
    "assertif": (
        "Ton assertif et direct. Phrases courtes et percutantes. Va droit au but. "
        "Pas de fioritures. Expose clairement les faits, les arguments et la demande. "
        "Formules comme 'Je conteste.', 'Je demande le remboursement immédiat.', 'Ma demande est ferme.'."
    ),
}

DEFAULT_TONE = "formel"


def generate_letter(description: str, vices_str: str, legal_context: str, tone: str = "formel") -> str:
    """Génère une lettre de contestation avec le ton demandé."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return f"[Lettre non générée — clé API manquante]\n\nVices détectés :\n{vices_str}"

    tone_instr = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS[DEFAULT_TONE])
    tone_label = {
        "formel": "Formelle", "ferme": "Ferme", "amical": "Amicale",
        "conciliant": "Conciliante", "assertif": "Assertive",
    }.get(tone, "Formelle")

    prompt = f"""Tu es Lexavo Defend, expert juridique belge en contestation.

Génère une lettre de contestation basée sur les éléments suivants.

CONTEXTE :
{description}

VICES DE FORME DÉTECTÉS :
{vices_str}

CONTEXTE LÉGAL :
{legal_context}

TON DEMANDÉ — {tone_label} :
{tone_instr}

RÈGLES :
- Respecte STRICTEMENT le ton demandé
- Cite chaque vice de forme avec sa base légale si disponible
- Structure : Objet, Faits, Arguments juridiques, Demande, Formule de politesse adaptée au ton
- Date du jour : {datetime.utcnow().strftime('%d/%m/%Y')}
- Maximum 450 mots
- En français

Réponds UNIQUEMENT avec le texte de la lettre, sans JSON ni balises."""

    client_ai = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client_ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1400,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        log.error(f"Erreur génération lettre : {e}")
        return f"Lettre de contestation\n\nJe conteste la décision en invoquant :\n{vices_str}"


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
    # ── Nouvelles catégories Auto & Admin ─────────────────────────────────────
    {
        "id": "parking_prive",
        "label": "Parking privé",
        "icon": "🅿️",
        "description": "Indigo, Q-Park, Apcoa, Interparking — souvent contestables",
        "keywords": ["parking", "indigo", "q-park", "apcoa", "interparking", "stationnement prive", "lettre parking", "vehicule stationne", "reclamation parking"],
        "branch": "droit_civil",
        "checklist": True,
    },
    {
        "id": "garage_auto",
        "label": "Garage / SAV auto",
        "icon": "🔧",
        "description": "Réparation non conforme, devis dépassé, vice caché",
        "keywords": ["garage", "reparation", "mecanique", "concessionnaire", "devis", "facture garage", "vice cache voiture", "carrosserie"],
        "branch": "droit_commercial",
        "checklist": True,
    },
    {
        "id": "assurance_auto",
        "label": "Assurance auto",
        "icon": "🛡️",
        "description": "Refus remboursement, résiliation abusive, sinistre",
        "keywords": ["assurance auto", "sinistre", "remboursement assurance", "refus assurance", "resiliation", "franchise", "expertise auto"],
        "branch": "droit_civil",
        "checklist": True,
    },
    {
        "id": "controle_technique",
        "label": "Contrôle technique",
        "icon": "✅",
        "description": "Refus injustifié, contre-visite, frais abusifs",
        "keywords": ["controle technique", "contre-visite", "keuringsstation", "ct auto", "visite technique", "refus technique"],
        "branch": "droit_administratif",
        "checklist": True,
    },
    {
        "id": "amende_admin",
        "label": "Amende administrative",
        "icon": "🏛️",
        "description": "Commune, SPF, ONSS, amende administrative communale (AAC)",
        "keywords": ["amende administrative", "aac", "commune", "spf", "onss", "administration", "sanction administrative", "fonctionnaire sanctionnateur"],
        "branch": "droit_administratif",
        "checklist": True,
    },
    {
        "id": "sncb_stib",
        "label": "SNCB / STIB / TEC",
        "icon": "🚆",
        "description": "PV sans titre, contestation transport en commun",
        "keywords": ["sncb", "stib", "tec", "de lijn", "train", "metro", "tram", "bus", "titre transport", "controle transport", "pv sncb"],
        "branch": "droit_administratif",
        "checklist": True,
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


# ─── CHECKLIST VICES DE FORME ────────────────────────────────────────────────

CHECKLIST_QUESTIONS = {
    "amende": [
        {"id": "signalisation", "question": "La signalisation de limitation de vitesse était-elle clairement visible ?", "favorable_if": False, "vice": "Signalisation non conforme (AR 1/12/1975 art. 1.4)"},
        {"id": "delai", "question": "Avez-vous reçu l'avis/PV dans le délai légal ? (14 jours pour perception immédiate)", "favorable_if": False, "vice": "Délai de notification dépassé — prescription possible"},
        {"id": "donnees_correctes", "question": "Les données du PV sont-elles correctes ? (plaque, heure, lieu, type de véhicule)", "favorable_if": False, "vice": "Erreur matérielle dans le PV — contestation sur fond"},
        {"id": "conducteur", "question": "Étiez-vous le conducteur au moment des faits ?", "favorable_if": False, "vice": "Désignation de conducteur possible — le titulaire peut ne pas être responsable"},
        {"id": "vitesse_plausible", "question": "La vitesse indiquée vous semble-t-elle correcte ?", "favorable_if": False, "vice": "Contestation de la mesure radar — homologation à vérifier"},
    ],
    "parking_prive": [
        {"id": "signalisation_visible", "question": "La signalisation des conditions de stationnement était-elle visible à l'entrée ?", "favorable_if": False, "vice": "Absence de contrat — pas d'acceptation des conditions sans signalisation visible"},
        {"id": "lettre_officielle", "question": "Avez-vous reçu une vraie amende officielle (police/commune) ou une lettre d'une société privée ?", "favorable_if": True, "vice": "Lettre privée = réclamation contractuelle, pas amende — souvent non exécutoire"},
        {"id": "base_legale", "question": "La lettre mentionne-t-elle une base légale précise (article de loi) ?", "favorable_if": False, "vice": "Absence de fondement juridique clair — contestation aisée"},
        {"id": "titulaire", "question": "Êtes-vous le titulaire du véhicule (pas forcément le conducteur) ?", "favorable_if": True, "vice": "Transfert de données DIV contestable si pas de base contractuelle explicite"},
        {"id": "double_paiement", "question": "Aviez-vous déjà payé le stationnement ce jour-là dans ce parking ?", "favorable_if": True, "vice": "Double facturation — remboursement exigible + intérêts légaux"},
    ],
    "garage_auto": [
        {"id": "devis_signe", "question": "Aviez-vous signé un devis avant les réparations ?", "favorable_if": False, "vice": "Absence de devis signé — le garagiste ne peut exiger plus que l'estimation verbale"},
        {"id": "depassement", "question": "La facture dépasse-t-elle le devis de plus de 10% ?", "favorable_if": True, "vice": "Dépassement non autorisé — Loi du 15 mai 2014, art. 57 : accord préalable obligatoire"},
        {"id": "garantie", "question": "La panne est-elle réapparue moins de 6 mois après la réparation ?", "favorable_if": True, "vice": "Présomption de vice antérieur — garantie légale 2 ans (art. 1641 Code civil)"},
        {"id": "facture_detaillee", "question": "La facture est-elle détaillée (pièces + main d'œuvre séparées) ?", "favorable_if": False, "vice": "Facture non transparente — droit à la ventilation (art. 57 CDE)"},
        {"id": "consentement_supp", "question": "A-t-on vous contacté avant d'effectuer des travaux supplémentaires ?", "favorable_if": False, "vice": "Travaux sans accord — non opposables, refus de paiement possible"},
    ],
    "assurance_auto": [
        {"id": "delai_declaration", "question": "Avez-vous déclaré le sinistre dans le délai contractuel (généralement 8 jours) ?", "favorable_if": True, "vice": "Déclaration tardive — vérifier si le délai est impératif ou de rigueur"},
        {"id": "refus_motive", "question": "L'assureur a-t-il motivé son refus par écrit ?", "favorable_if": False, "vice": "Refus non motivé — art. 87 Loi assurances 2014 : motivation obligatoire"},
        {"id": "delai_reponse", "question": "L'assureur a-t-il répondu dans les 30 jours ?", "favorable_if": False, "vice": "Dépassement du délai légal de traitement — plainte auprès de l'Ombudsman assurances"},
        {"id": "exclusion_contrat", "question": "Le refus est-il basé sur une clause d'exclusion clairement mentionnée dans votre contrat ?", "favorable_if": False, "vice": "Exclusion non transparente — clause potentiellement abusive (art. 74 LPMC)"},
        {"id": "expertise_contradictoire", "question": "A-t-on proposé une expertise contradictoire en cas de désaccord ?", "favorable_if": False, "vice": "Droit à expertise contradictoire non respecté — art. 84 Loi assurances 2014"},
    ],
    "amende_admin": [
        {"id": "notification_delai", "question": "Avez-vous reçu la notification dans les 3 mois de l'infraction ?", "favorable_if": False, "vice": "Prescription — délai de notification dépassé"},
        {"id": "droit_defense", "question": "A-t-on vous offert la possibilité de présenter vos observations avant la décision ?", "favorable_if": False, "vice": "Violation droits de la défense — procédure irrégulière (art. 41 Charte droits fondamentaux UE)"},
        {"id": "base_reglementaire", "question": "L'amende est-elle basée sur un règlement communal publié au BS ou portail belge ?", "favorable_if": False, "vice": "Défaut de base réglementaire — sanction illégale"},
        {"id": "proportionnalite", "question": "Le montant vous semble-t-il disproportionné par rapport à l'infraction ?", "favorable_if": True, "vice": "Principe de proportionnalité violé — réduction possible"},
        {"id": "recidive", "question": "Est-ce votre première infraction de ce type ?", "favorable_if": True, "vice": "Circonstances atténuantes — première infraction, demande de réduction"},
    ],
    "sncb_stib": [
        {"id": "titre_valide", "question": "Aviez-vous un titre de transport valide mais non présenté (oublié, app bug) ?", "favorable_if": True, "vice": "Régularisation possible — production du titre a posteriori"},
        {"id": "delai_regularisation", "question": "L'agent vous a-t-il informé du délai pour régulariser ?", "favorable_if": False, "vice": "Information insuffisante — recours au service médiation transport"},
        {"id": "pv_regulier", "question": "Le PV mentionne-t-il correctement la ligne, l'heure, le lieu ?", "favorable_if": False, "vice": "Erreur matérielle dans le PV — contestation sur la forme"},
        {"id": "tarif_applique", "question": "Le montant demandé correspond-il au tarif affiché dans les conditions générales ?", "favorable_if": False, "vice": "Tarif non conforme aux CGV — contestation du montant"},
        {"id": "situation_speciale", "question": "Étiez-vous dans une situation exceptionnelle ? (panne app, grève, évacuation urgente)", "favorable_if": True, "vice": "Force majeure / cas de nécessité — recours en grâce possible"},
    ],
    "controle_technique": [
        {"id": "motif_ecrit", "question": "Le refus est-il accompagné d'un rapport écrit détaillant chaque défaut ?", "favorable_if": False, "vice": "Obligation de rapport motivé (AR 23/12/1994 art. 23) — procédure irrégulière"},
        {"id": "defaut_grave", "question": "Le défaut mentionné vous semble-t-il réellement grave (dangereux pour la sécurité) ?", "favorable_if": False, "vice": "Refus disproportionné — contre-expertise possible"},
        {"id": "contre_expertise", "question": "A-t-on vous informé de votre droit à une contre-expertise dans un autre centre ?", "favorable_if": False, "vice": "Droit à contre-expertise non mentionné — recours auprès du SPW/Wallonie ou VW Vlaanderen"},
        {"id": "delai_contre_visite", "question": "Disposiez-vous d'au moins 15 jours pour effectuer les réparations et la contre-visite ?", "favorable_if": False, "vice": "Délai insuffisant accordé — contestation de la procédure"},
    ],
}

CHECKLIST_LEGAL_CONTEXT = {
    "parking_prive": "En droit belge, les sociétés de parking privé (Indigo, Q-Park, Apcoa, Interparking) ne peuvent imposer d'amende au sens strict. Leurs 'redevances' sont des réclamations contractuelles civiles. Le titulaire du véhicule n'est pas automatiquement lié si la signalisation était insuffisante ou s'il n'était pas le conducteur. Ces réclamations sont souvent abandonnées face à une contestation motivée.",
    "amende": "Le Code de la route belge (AR 1er décembre 1975) encadre strictement les conditions de constatation des infractions. La perception immédiate (PI) doit être notifiée dans les 14 jours. En cas de radar automatique, le procès-verbal doit mentionner le certificat d'étalonnage de l'appareil. La signalisation routière doit être conforme à l'AR du 1er décembre 1975.",
    "garage_auto": "La Loi du 15 mai 2014 (Code de droit économique art. VI.57) impose au garagiste de fournir un devis préalable et d'obtenir l'accord du client avant tout dépassement. La garantie légale (art. 1641 Code civil + Loi 1/09/2004) s'applique 2 ans pour les vices cachés.",
    "assurance_auto": "La Loi du 4 avril 2014 relative aux assurances impose à l'assureur de traiter les déclarations de sinistre dans un délai raisonnable (30 jours), de motiver tout refus par écrit, et d'informer de la procédure de plainte. L'Ombudsman des Assurances est compétent pour les litiges.",
    "amende_admin": "Les amendes administratives communales (AAC) sont régies par la Loi du 24 juin 2013. Le contrevenant dispose de 30 jours pour contester auprès du fonctionnaire sanctionnateur. Les droits de défense doivent être respectés (droit d'être entendu). Recours possible devant le Tribunal de police.",
    "sncb_stib": "Les conditions générales de transport SNCB et STIB prévoient des procédures de régularisation. En cas de contestation, le Service de Médiation pour le Transport est compétent (gratuit). La SNCB dispose d'un service clientèle spécialisé pour les recours.",
    "controle_technique": "L'AR du 23 décembre 1994 relatif au contrôle technique impose un rapport motivé en cas de refus. Le propriétaire peut effectuer une contre-expertise dans un autre centre agréé dans les 15 jours. En Wallonie : SPW, en Flandre : VW, à Bruxelles : Bruxelles Mobilité.",
    "assurance_auto": "Loi du 4 avril 2014, art. 84 : droit à expertise contradictoire. Art. 87 : motivation obligatoire du refus. Ombudsman des Assurances : www.ombudsman.as",
}


def analyze_checklist(
    category: str,
    answers: dict,
    region: Optional[str] = None,
    extra_description: str = "",
    photos_base64: Optional[List[str]] = None,
    tone: str = "formel",
) -> dict:
    """Analyse la checklist de vices de forme et génère la lettre de contestation.

    Args:
        category: id de la catégorie (amende, parking_prive, etc.)
        answers: dict {question_id: bool} — True = oui, False = non
        region: bruxelles | wallonie | flandre
        extra_description: contexte supplémentaire de l'utilisateur
        photos_base64: photos du PV/document
    """
    questions = CHECKLIST_QUESTIONS.get(category, [])
    if not questions:
        raise ValueError(f"Catégorie '{category}' sans checklist disponible")

    # Détecter les vices
    vices_detected = []
    score = 0
    max_score = len(questions)

    for q in questions:
        answer = answers.get(q["id"])
        if answer is None:
            continue
        # favorable_if = True → la réponse "oui" (True) est favorable
        # favorable_if = False → la réponse "non" (False) est favorable
        is_favorable = (answer == q["favorable_if"])
        if is_favorable:
            score += 1
            vices_detected.append(q["vice"])

    contestability_pct = int((score / max_score) * 100) if max_score > 0 else 0

    if contestability_pct >= 60:
        level = "forte"
        recommendation = f"Conteste — {len(vices_detected)} argument(s) solide(s) identifié(s)"
    elif contestability_pct >= 30:
        level = "moyenne"
        recommendation = "Contestation possible — arguments limités mais recevables"
    else:
        level = "faible"
        recommendation = "Peu d'arguments détectés — paiement recommandé ou consultation d'un avocat"

    # OCR si photos
    photo_text = ""
    if photos_base64:
        try:
            from api.utils.ocr import extract_text_from_base64_list
            photo_text = extract_text_from_base64_list(photos_base64) or ""
        except Exception as e:
            log.warning(f"OCR checklist ignoré : {e}")

    # Construire la description pour Claude
    vices_str = "\n".join(f"- {v}" for v in vices_detected) if vices_detected else "Aucun vice de forme majeur détecté"
    legal_context = CHECKLIST_LEGAL_CONTEXT.get(category, "")
    region_str = f"\nRégion : {region}" if region else ""

    description = (
        f"Catégorie : {category}\n"
        f"Vices de forme détectés par la checklist :\n{vices_str}\n"
        f"Score de contestabilité : {contestability_pct}% ({level})\n"
        f"{region_str}\n"
        f"Contexte légal : {legal_context}\n"
    )
    if extra_description:
        description += f"\nInformations supplémentaires de l'utilisateur : {extra_description}"
    if photo_text:
        description += f"\n\n[Texte extrait du document/PV]\n{photo_text}"

    # Si score trop faible, pas la peine de générer une lettre
    if not vices_detected:
        return {
            "contestability_score": contestability_pct,
            "contestability_level": level,
            "vices_detected": [],
            "recommendation": recommendation,
            "letter": None,
            "next_steps": ["Consultez un avocat si vous estimez avoir des arguments supplémentaires", "Paiement dans le délai pour éviter des majorations"],
            "legal_context": legal_context,
            "disclaimer": "Lexavo est un assistant juridique. Il ne remplace pas un avocat.",
        }

    # Générer la lettre via Claude avec le ton demandé
    letter = generate_letter(description, vices_str, legal_context, tone=tone)

    next_steps = ["Envoyez cette lettre en recommandé avec accusé de réception"]
    if category == "amende":
        next_steps.append("Délai : 30 jours à compter de la notification")
        next_steps.append("Destinataire : organisme indiqué sur le PV")
    elif category == "parking_prive":
        next_steps.append("Ne payez pas avant d'avoir reçu leur réponse")
        next_steps.append("En cas de poursuite judiciaire, contactez un avocat")
    elif category == "assurance_auto":
        next_steps.append("Saisissez l'Ombudsman des Assurances si refus persistant")
    elif category in ("sncb_stib",):
        next_steps.append("Contactez le Service de Médiation pour le Transport (gratuit)")

    return {
        "contestability_score": contestability_pct,
        "contestability_level": level,
        "vices_detected": vices_detected,
        "recommendation": recommendation,
        "letter": letter,
        "next_steps": next_steps,
        "legal_context": legal_context,
        "disclaimer": "Lexavo est un assistant juridique. Il ne remplace pas un avocat.",
    }


# ─── SCAN AMENDE (OCR → extraction structurée) ───────────────────────────────

SCAN_EXTRACTION_PROMPT = """Tu es un expert en lecture de documents officiels belges (PV, amendes, lettres de parking).

Extrais les informations suivantes du document photographié. Si un champ est illisible ou absent, retourne null.

FORMAT DE RÉPONSE (JSON strict uniquement) :
{
  "montant": 150,
  "date_infraction": "2026-03-15",
  "heure": "14h32",
  "lieu": "Chaussée de Waterloo 142, Bruxelles",
  "code_infraction": "C23",
  "vitesse_constatee": 67,
  "vitesse_autorisee": 50,
  "plaque": "1-ABC-234",
  "type_document": "perception_immediate|pv_police|radar_automatique|parking_prive|amende_admin|sncb",
  "date_notification": "2026-03-22",
  "organisme": "Police locale Bruxelles-Ixelles",
  "reference": "PV/2026/00123",
  "delai_contestation": "30 jours",
  "adresse_contestation": "Adresse où envoyer la contestation si visible",
  "confidence": 0.87
}

Réponds UNIQUEMENT avec le JSON, sans texte autour."""


def scan_amende(photos_base64: List[str], category: str = "amende") -> dict:
    """Extrait les données d'un PV/amende/lettre photographié(e) via OCR + Claude Vision.

    Args:
        photos_base64: liste de photos base64 du document
        category: type de document attendu
    """
    if not photos_base64:
        raise ValueError("Au moins une photo est requise")

    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY non configurée")

    client_ai = anthropic.Anthropic(api_key=api_key)

    # Construire le message avec les images
    content = [{"type": "text", "text": SCAN_EXTRACTION_PROMPT}]
    for photo_b64 in photos_base64[:3]:  # max 3 photos
        # Détecter format (jpeg par défaut)
        media_type = "image/jpeg"
        if photo_b64.startswith("iVBOR"):
            media_type = "image/png"
        elif photo_b64.startswith("/9j/") or photo_b64.startswith("FFD8"):
            media_type = "image/jpeg"

        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": photo_b64},
        })

    try:
        resp = client_ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": content}],
        )
        raw = resp.content[0].text.strip()

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            extracted = json.loads(json_match.group())
        else:
            extracted = {}
    except Exception as e:
        log.error(f"Erreur scan amende : {e}")
        extracted = {"confidence": 0.0, "error": str(e)}

    # Pré-remplir la checklist si possible
    prefill = {}
    if category == "amende":
        if extracted.get("date_infraction") and extracted.get("date_notification"):
            try:
                from datetime import date
                d_inf = date.fromisoformat(extracted["date_infraction"])
                d_not = date.fromisoformat(extracted["date_notification"])
                days_diff = (d_not - d_inf).days
                prefill["delai"] = days_diff <= 14  # True = dans les délais
            except Exception:
                pass
        if extracted.get("plaque"):
            prefill["donnees_correctes"] = True  # présumer correct si trouvé

    return {
        "extracted": extracted,
        "prefill_checklist": prefill,
        "category_detected": extracted.get("type_document", category),
        "confidence": extracted.get("confidence", 0.5),
    }
