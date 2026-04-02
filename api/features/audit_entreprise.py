"""Lexavo Audit Entreprise — Audit de conformite juridique pour PME et entreprises belges.

30 questions couvrant 8 domaines du droit belge.
Score sur 100 + rapport detaille + recommandations IA personnalisees.
Reserve aux plans Business, Firm et Enterprise.
"""

import json
import os
import re
import logging
from typing import List, Optional
from datetime import datetime

log = logging.getLogger("audit_entreprise")

# ─── 30 questions d'audit couvrant 8 domaines juridiques ────────────────────

AUDIT_QUESTIONS = [
    # ── RGPD & Vie privee (5 questions) ──────────────────────────────────
    {"id": 1, "question": "Disposez-vous d'un registre des activites de traitement (art. 30 RGPD) ?",
     "category": "rgpd", "weight": 9, "legal_ref": "Art. 30 RGPD", "risk": "Amende jusqu'a 10M EUR ou 2% CA"},
    {"id": 2, "question": "Avez-vous realise une analyse d'impact (DPIA) pour vos traitements a risque ?",
     "category": "rgpd", "weight": 8, "legal_ref": "Art. 35 RGPD", "risk": "Amende APD"},
    {"id": 3, "question": "Vos sous-traitants ont-ils signe un accord de traitement des donnees (DPA) ?",
     "category": "rgpd", "weight": 8, "legal_ref": "Art. 28 RGPD", "risk": "Responsabilite solidaire"},
    {"id": 4, "question": "Avez-vous un DPO designe ou une personne de contact vie privee ?",
     "category": "rgpd", "weight": 7, "legal_ref": "Art. 37-39 RGPD", "risk": "Non-conformite"},
    {"id": 5, "question": "Votre politique de confidentialite est-elle accessible et a jour ?",
     "category": "rgpd", "weight": 7, "legal_ref": "Art. 13-14 RGPD", "risk": "Plaintes APD"},

    # ── Droit du travail (5 questions) ────────────────────────────────────
    {"id": 6, "question": "Tous vos contrats de travail sont-ils ecrits et conformes aux CCT sectorielles ?",
     "category": "travail", "weight": 9, "legal_ref": "Loi du 3/7/1978", "risk": "CDI presume, indemnites"},
    {"id": 7, "question": "Votre reglement de travail est-il depose au SPF Emploi et mis a jour ?",
     "category": "travail", "weight": 8, "legal_ref": "Loi du 8/4/1965", "risk": "Amende penale"},
    {"id": 8, "question": "Avez-vous un plan de prevention et un CPPT operationnel ?",
     "category": "travail", "weight": 7, "legal_ref": "Loi du 4/8/1996 bien-etre", "risk": "Sanctions penales"},
    {"id": 9, "question": "Vos elections sociales sont-elles organisees si vous avez 50+ travailleurs ?",
     "category": "travail", "weight": 6, "legal_ref": "Loi du 4/12/2007", "risk": "Nullite des decisions"},
    {"id": 10, "question": "Le temps de travail et les heures supplementaires sont-ils correctement enregistres ?",
     "category": "travail", "weight": 8, "legal_ref": "Loi du 16/3/1971", "risk": "Sursalaire du + amendes"},

    # ── Droit fiscal (4 questions) ────────────────────────────────────────
    {"id": 11, "question": "Vos declarations TVA sont-elles deposees dans les delais legaux ?",
     "category": "fiscal", "weight": 9, "legal_ref": "Code TVA art. 53", "risk": "Interets + amendes 10-200%"},
    {"id": 12, "question": "Vos factures respectent-elles toutes les mentions obligatoires ?",
     "category": "fiscal", "weight": 7, "legal_ref": "AR n28 Code TVA", "risk": "Refus deduction TVA"},
    {"id": 13, "question": "Avez-vous un prix de transfert documente (si groupe international) ?",
     "category": "fiscal", "weight": 6, "legal_ref": "Art. 185/2 CIR", "risk": "Redressement fiscal"},
    {"id": 14, "question": "Votre declaration ISOC est-elle deposee dans les delais avec annexes completes ?",
     "category": "fiscal", "weight": 8, "legal_ref": "Art. 305-310 CIR", "risk": "Taxation d'office"},

    # ── Droit commercial (4 questions) ────────────────────────────────────
    {"id": 15, "question": "Vos CGV/CGU sont-elles conformes au Code de droit economique (Livre VI) ?",
     "category": "commercial", "weight": 8, "legal_ref": "CDE Livre VI", "risk": "Clauses abusives nulles"},
    {"id": 16, "question": "Votre numero BCE et les activites declarees sont-ils a jour ?",
     "category": "commercial", "weight": 7, "legal_ref": "CDE Livre III", "risk": "Sanctions administratives"},
    {"id": 17, "question": "Respectez-vous les delais de paiement legaux (30/60 jours) ?",
     "category": "commercial", "weight": 7, "legal_ref": "Loi du 2/8/2002", "risk": "Interets de retard automatiques"},
    {"id": 18, "question": "Avez-vous une procedure de lutte contre le blanchiment (si applicable) ?",
     "category": "commercial", "weight": 6, "legal_ref": "Loi du 18/9/2017", "risk": "Sanctions penales"},

    # ── Droit des societes (4 questions) ──────────────────────────────────
    {"id": 19, "question": "Vos statuts sont-ils conformes au nouveau CSA (depuis 2019) ?",
     "category": "societes", "weight": 8, "legal_ref": "CSA art. 2:8", "risk": "Responsabilite administrateurs"},
    {"id": 20, "question": "Le rapport de gestion et les comptes annuels sont-ils deposes a la BNB ?",
     "category": "societes", "weight": 8, "legal_ref": "CSA art. 3:1-3:12", "risk": "Dissolution judiciaire"},
    {"id": 21, "question": "Le test de liquidite et le test du bilan sont-ils effectues avant distribution ?",
     "category": "societes", "weight": 7, "legal_ref": "CSA art. 5:142-143", "risk": "Responsabilite personnelle"},
    {"id": 22, "question": "Le registre UBO est-il a jour avec les beneficiaires effectifs ?",
     "category": "societes", "weight": 8, "legal_ref": "Loi du 18/9/2017 art. 74", "risk": "Amende 250-50000 EUR"},

    # ── Environnement (3 questions) ───────────────────────────────────────
    {"id": 23, "question": "Disposez-vous des permis d'environnement necessaires (classe 1/2/3) ?",
     "category": "environnement", "weight": 8, "legal_ref": "Permis environnement regional", "risk": "Fermeture + amendes"},
    {"id": 24, "question": "Respectez-vous les obligations de tri et declaration des dechets ?",
     "category": "environnement", "weight": 6, "legal_ref": "AGW du 5/12/2008", "risk": "Amende environnementale"},
    {"id": 25, "question": "Avez-vous un rapport energetique si votre batiment depasse 1000m2 ?",
     "category": "environnement", "weight": 5, "legal_ref": "PEB regional", "risk": "Sanctions administratives"},

    # ── Gouvernance & compliance (3 questions) ────────────────────────────
    {"id": 26, "question": "Avez-vous un code de conduite ou une charte ethique interne ?",
     "category": "gouvernance", "weight": 5, "legal_ref": "Code Buysse III", "risk": "Risque reputationnel"},
    {"id": 27, "question": "Avez-vous un canal de signalement interne (lanceurs d'alerte) ?",
     "category": "gouvernance", "weight": 7, "legal_ref": "Loi du 28/11/2022", "risk": "Amende + sanctions"},
    {"id": 28, "question": "Vos administrateurs sont-ils assures en RC mandataires sociaux ?",
     "category": "gouvernance", "weight": 6, "legal_ref": "CSA art. 2:56", "risk": "Responsabilite personnelle"},

    # ── Propriete intellectuelle (2 questions) ────────────────────────────
    {"id": 29, "question": "Vos marques et brevets sont-ils enregistres et maintenus ?",
     "category": "pi", "weight": 7, "legal_ref": "CBPI art. 2.1", "risk": "Perte de droits exclusifs"},
    {"id": 30, "question": "Vos contrats prevoient-ils des clauses de cession de PI pour les employes/prestataires ?",
     "category": "pi", "weight": 6, "legal_ref": "Loi du 30/6/1994 art. 3", "risk": "PI appartient au createur"},
]

AUDIT_CATEGORIES = {
    "rgpd": {"label": "RGPD & Vie privee", "icon": "🔒", "branch": "droit_fondamentaux"},
    "travail": {"label": "Droit du travail", "icon": "👷", "branch": "droit_travail"},
    "fiscal": {"label": "Droit fiscal", "icon": "💰", "branch": "droit_fiscal"},
    "commercial": {"label": "Droit commercial", "icon": "🏪", "branch": "droit_commercial"},
    "societes": {"label": "Droit des societes", "icon": "🏛️", "branch": "droit_commercial"},
    "environnement": {"label": "Droit environnemental", "icon": "🌿", "branch": "droit_environnement"},
    "gouvernance": {"label": "Gouvernance", "icon": "📋", "branch": "droit_commercial"},
    "pi": {"label": "Propriete intellectuelle", "icon": "💡", "branch": "droit_propriete_intellectuelle"},
}

COMPANY_TYPES = [
    {"id": "srl", "label": "SRL (Societe a responsabilite limitee)"},
    {"id": "sa", "label": "SA (Societe anonyme)"},
    {"id": "sc", "label": "SC (Societe cooperative)"},
    {"id": "independant", "label": "Independant / Personne physique"},
    {"id": "asbl", "label": "ASBL"},
    {"id": "pme", "label": "PME (< 50 employes)"},
    {"id": "grande_entreprise", "label": "Grande entreprise (50+ employes)"},
]


def get_audit_questions(company_type: str = "srl") -> list:
    """Retourne les questions d'audit filtrees par type d'entreprise."""
    questions = AUDIT_QUESTIONS.copy()
    # Filtrer les questions non applicables
    if company_type in ("independant",):
        questions = [q for q in questions if q["id"] not in (9, 13, 19, 20, 21)]
    if company_type in ("asbl",):
        questions = [q for q in questions if q["category"] != "fiscal" or q["id"] == 11]
    return questions


def get_company_types() -> list:
    return COMPANY_TYPES


def get_audit_categories() -> list:
    return [{"id": k, **v} for k, v in AUDIT_CATEGORIES.items()]


def generate_audit_report(
    answers: List[dict],
    company_type: str = "srl",
    company_name: str = "",
    sector: str = "",
    employees: int = 0,
    mock: bool = False,
) -> dict:
    """Genere un rapport d'audit de conformite complet.

    Args:
        answers: Liste de {"question_id": int, "answer": "yes"|"no"|"partial"|"na"}
        company_type: srl, sa, sc, independant, asbl, pme, grande_entreprise
        company_name: Nom de l'entreprise
        sector: Secteur d'activite
        employees: Nombre d'employes
        mock: Mode test (pas d'appel Claude)
    """
    if len(answers) < 10:
        raise ValueError("Minimum 10 reponses requises pour un audit complet")

    ANSWER_VALUES = {"yes": 1.0, "partial": 0.5, "no": 0.0, "na": None}

    total_weight = 0
    earned = 0
    items = []
    category_scores = {}
    critical_risks = []

    for answer in answers:
        q_id = answer["question_id"]
        raw = answer["answer"].lower()
        value = ANSWER_VALUES.get(raw)

        question = next((q for q in AUDIT_QUESTIONS if q["id"] == q_id), None)
        if not question or value is None:
            continue

        weight = question["weight"]
        total_weight += weight
        points = weight * value
        earned += points

        cat = question["category"]
        if cat not in category_scores:
            cat_info = AUDIT_CATEGORIES.get(cat, {"label": cat, "icon": "📊"})
            category_scores[cat] = {
                "label": cat_info["label"],
                "icon": cat_info["icon"],
                "earned": 0,
                "total": 0,
                "items": [],
            }
        category_scores[cat]["earned"] += points
        category_scores[cat]["total"] += weight

        status_map = {"yes": "conforme", "partial": "partiel", "no": "non_conforme"}
        item = {
            "question_id": q_id,
            "question": question["question"],
            "category": cat,
            "status": status_map.get(raw, raw),
            "legal_ref": question["legal_ref"],
            "risk": question["risk"],
            "weight": weight,
        }
        category_scores[cat]["items"].append(item)
        items.append(item)

        if value == 0 and weight >= 8:
            critical_risks.append(item)

    # Score global sur 100
    score = round((earned / total_weight * 100) if total_weight > 0 else 0)

    # Verdict feu tricolore
    if score >= 80:
        verdict = "green"
        verdict_label = "Bon niveau de conformite"
    elif score >= 50:
        verdict = "orange"
        verdict_label = "Conformite partielle — actions requises"
    else:
        verdict = "red"
        verdict_label = "Non-conformite significative — risques eleves"

    # Scores par categorie
    category_results = {}
    for cat, data in category_scores.items():
        cat_score = round((data["earned"] / data["total"] * 100) if data["total"] > 0 else 0)
        category_results[cat] = {
            "label": data["label"],
            "icon": data["icon"],
            "score": cat_score,
            "verdict": "green" if cat_score >= 80 else ("orange" if cat_score >= 50 else "red"),
            "conformes": len([i for i in data["items"] if i["status"] == "conforme"]),
            "non_conformes": len([i for i in data["items"] if i["status"] == "non_conforme"]),
            "partiels": len([i for i in data["items"] if i["status"] == "partiel"]),
        }

    # Generer les recommandations IA si pas en mode mock
    recommendations = []
    if not mock and critical_risks:
        recommendations = _generate_ai_recommendations(
            critical_risks, company_type, company_name, sector, employees
        )

    # Humanizer — ton naturel sur les recommandations generees par IA
    from rag.humanizer import humanize
    for rec in recommendations:
        if rec.get("action"):
            rec["action"] = humanize(rec["action"])

    return {
        "score": score,
        "verdict": verdict,
        "verdict_label": verdict_label,
        "company_name": company_name,
        "company_type": company_type,
        "sector": sector,
        "employees": employees,
        "total_questions": len(items),
        "conformes": len([i for i in items if i["status"] == "conforme"]),
        "non_conformes": len([i for i in items if i["status"] == "non_conforme"]),
        "partiels": len([i for i in items if i["status"] == "partiel"]),
        "critical_risks": critical_risks,
        "category_results": category_results,
        "items": items,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat(),
        "disclaimer": "Outil d'information juridique. Ne constitue pas un avis professionnel. Consultez un avocat pour une analyse personnalisee.",
    }


def _generate_ai_recommendations(
    critical_risks: list,
    company_type: str,
    company_name: str,
    sector: str,
    employees: int,
) -> list:
    """Genere des recommandations personnalisees via Claude."""
    try:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return [{"priority": "high", "action": "Configurez ANTHROPIC_API_KEY pour des recommandations personnalisees."}]

        client = anthropic.Anthropic(api_key=api_key)

        risks_text = "\n".join([
            f"- {r['question']} (Ref: {r['legal_ref']}, Risque: {r['risk']})"
            for r in critical_risks
        ])

        prompt = f"""Tu es un juriste belge specialise en conformite des entreprises.

Entreprise : {company_name or 'Non renseignee'} ({company_type})
Secteur : {sector or 'Non renseigne'}
Employes : {employees or 'Non renseigne'}

Risques critiques identifies :
{risks_text}

Genere 3-5 recommandations concretes et prioritaires pour corriger ces non-conformites.
Pour chaque recommandation, indique :
- L'action concrete a entreprendre
- Le delai recommande
- Le cout estime (si applicable)
- La reference legale

Reponds en JSON :
[{{"priority": "high|medium", "action": "...", "deadline": "...", "cost_estimate": "...", "legal_ref": "..."}}]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        json_match = re.search(r'\[[\s\S]*\]', raw)
        if json_match:
            return json.loads(json_match.group())
        return []

    except Exception as e:
        log.error(f"Erreur generation recommandations IA : {e}")
        return []
