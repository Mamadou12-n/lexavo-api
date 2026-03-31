"""Lexavo Compliance — Audit legal pour independants et PME.
15 questions -> rapport de conformite RGPD, CGV, contrats, obligations sociales, TVA."""

import json
import os
import re
import logging
from typing import List, Optional

log = logging.getLogger("compliance")

COMPLIANCE_QUESTIONS = [
    {"id": 1, "question": "Avez-vous un registre des traitements de donnees (RGPD) ?", "category": "rgpd", "weight": 8},
    {"id": 2, "question": "Avez-vous designe un DPO ou une personne de contact vie privee ?", "category": "rgpd", "weight": 6},
    {"id": 3, "question": "Votre politique de confidentialite est-elle publiee sur votre site ?", "category": "rgpd", "weight": 7},
    {"id": 4, "question": "Vos CGV sont-elles a jour et conformes au Code de droit economique ?", "category": "commercial", "weight": 8},
    {"id": 5, "question": "Vos contrats de travail sont-ils ecrits et signes ?", "category": "travail", "weight": 8},
    {"id": 6, "question": "Avez-vous un reglement de travail depose au SPF Emploi ?", "category": "travail", "weight": 7},
    {"id": 7, "question": "Etes-vous en ordre de cotisations sociales (ONSS/caisse sociale) ?", "category": "social", "weight": 9},
    {"id": 8, "question": "Votre numero BCE et activites sont-ils a jour ?", "category": "commercial", "weight": 6},
    {"id": 9, "question": "Avez-vous une assurance RC professionnelle ?", "category": "assurance", "weight": 7},
    {"id": 10, "question": "Vos declarations TVA sont-elles deposees dans les delais ?", "category": "fiscal", "weight": 8},
    {"id": 11, "question": "Avez-vous un compte bancaire professionnel separe ?", "category": "commercial", "weight": 5},
    {"id": 12, "question": "Vos factures respectent-elles les mentions obligatoires ?", "category": "fiscal", "weight": 7},
    {"id": 13, "question": "Avez-vous un plan de prevention au travail (bien-etre) ?", "category": "travail", "weight": 6},
    {"id": 14, "question": "Vos cookies/traceurs web respectent-ils la legislation ePrivacy ?", "category": "rgpd", "weight": 5},
    {"id": 15, "question": "Avez-vous un document unique d'evaluation des risques ?", "category": "travail", "weight": 5},
]


def get_compliance_questions() -> list:
    return COMPLIANCE_QUESTIONS


def generate_compliance_audit(
    answers: List[dict],
    company_type: str = "independant",
    mock: bool = False,
) -> dict:
    """Genere un rapport d'audit de conformite.

    Args:
        answers: Liste de {"question_id": int, "answer": "yes"|"no"|"partial"|"na"}
        company_type: independant, pme, association
        mock: Mode test
    """
    if len(answers) < 5:
        raise ValueError("Minimum 5 reponses requises pour un audit")

    ANSWER_VALUES = {"yes": 1.0, "partial": 0.5, "no": 0.0, "na": None}

    total_weight = 0
    earned = 0
    non_compliant = []
    partially_compliant = []
    compliant = []
    category_scores = {}

    for answer in answers:
        q_id = answer["question_id"]
        raw = answer["answer"].lower()
        value = ANSWER_VALUES.get(raw)

        question = next((q for q in COMPLIANCE_QUESTIONS if q["id"] == q_id), None)
        if not question or value is None:
            continue

        weight = question["weight"]
        total_weight += weight
        points = weight * value
        earned += points

        cat = question["category"]
        if cat not in category_scores:
            category_scores[cat] = {"earned": 0, "total": 0, "items": []}
        category_scores[cat]["earned"] += points
        category_scores[cat]["total"] += weight

        item = {"question": question["question"], "category": cat, "status": raw}
        if value == 0:
            item["risk"] = _get_risk(q_id)
            non_compliant.append(item)
        elif value == 0.5:
            item["recommendation"] = _get_recommendation(q_id)
            partially_compliant.append(item)
        else:
            compliant.append(item)

    score = round((earned / total_weight) * 100) if total_weight > 0 else 0

    if score >= 80:
        overall_status = "conforme"
        risk_level = "faible"
    elif score >= 50:
        overall_status = "partiellement_conforme"
        risk_level = "moyen"
    else:
        overall_status = "non_conforme"
        risk_level = "eleve"

    cat_breakdown = {}
    for cat, data in category_scores.items():
        cat_score = round((data["earned"] / data["total"]) * 100) if data["total"] > 0 else 0
        cat_breakdown[cat] = {"score": cat_score, "status": "conforme" if cat_score >= 80 else "a_risque" if cat_score < 50 else "attention"}

    return {
        "compliance_score": score,
        "overall_status": overall_status,
        "risk_level": risk_level,
        "company_type": company_type,
        "non_compliant": non_compliant,
        "partially_compliant": partially_compliant,
        "compliant_count": len(compliant),
        "category_breakdown": cat_breakdown,
        "priority_actions": [item["risk"] for item in non_compliant[:5]],
        "disclaimer": "Audit indicatif d'auto-evaluation. Ne remplace pas un audit professionnel.",
    }


def _get_risk(question_id: int) -> str:
    risks = {
        1: "Amende RGPD possible (APD) — jusqu'a 4% du CA ou 20M EUR (art. 83 RGPD).",
        2: "Obligation si traitement systematique (art. 37 RGPD). Recommande pour toute entreprise.",
        3: "Non-conformite RGPD — amende administrative possible.",
        4: "CGV non conformes = clauses abusives potentielles (Code droit economique, Livre VI).",
        5: "Obligation legale (Loi du 3 juillet 1978). Risque prud'homal.",
        6: "Obligation pour tout employeur (Loi du 8 avril 1965). Amende administrative.",
        7: "Retard ONSS = majorations + poursuites. Impact direct sur la tresorerie.",
        8: "Activites non declarees a la BCE = infraction (Code droit economique).",
        9: "Sans RC Pro, responsabilite personnelle illimitee sur votre patrimoine.",
        10: "Retard TVA = amendes administratives (art. 70 CTVA). 15% minimum.",
        11: "Melange comptes = risque fiscal + difficulte de preuve en cas de controle.",
        12: "Factures non conformes = refus deduction TVA par le SPF Finances.",
        13: "Obligation legale (Loi du 4 aout 1996). Amende ONSS.",
        14: "Amende APD possible. Obligation consentement prealable (Directive ePrivacy).",
        15: "Obligation si personnel (Code du bien-etre au travail). Amende inspection.",
    }
    return risks.get(question_id, "Risque de non-conformite a evaluer.")


def _get_recommendation(question_id: int) -> str:
    recs = {
        1: "Completez votre registre avec tous les traitements (template APD disponible).",
        2: "Designez un responsable interne. Pas besoin de DPO formel pour les petites structures.",
        3: "Mettez a jour votre politique selon le modele APD.",
        4: "Faites relire vos CGV par un juriste. Verifiez la conformite Livre VI CDE.",
        5: "Regularisez les contrats manquants. Modele disponible sur Lexavo.",
        6: "Deposez votre reglement au SPF Emploi via l'application en ligne.",
        7: "Contactez votre secretariat social pour verifier votre situation.",
        8: "Mettez a jour via MyEnterprise.be.",
        9: "Souscrivez une RC Pro adaptee a votre activite.",
        10: "Mettez en place un rappel calendrier pour chaque echeance TVA.",
        11: "Ouvrez un compte professionnel dedie.",
        12: "Verifiez les 12 mentions obligatoires (art. 5 AR du 29 decembre 1992).",
        13: "Contactez un service externe de prevention (SEPP).",
        14: "Implementez une banniere cookies conforme avec consentement granulaire.",
        15: "Faites realiser une analyse des risques par votre SEPP.",
    }
    return recs.get(question_id, "Consultez un professionnel pour mise en conformite.")
