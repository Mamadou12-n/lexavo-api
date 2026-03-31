"""Lexavo Score — Score de sante juridique sur 100.
10 questions -> score pondere + rapport avec points faibles."""

import logging
from typing import List

log = logging.getLogger("score")

SCORE_QUESTIONS = [
    {"id": 1, "question": "Avez-vous un contrat de travail ecrit et signe ?", "weight": 12, "category": "travail"},
    {"id": 2, "question": "Votre bail est-il enregistre aupres du SPF Finances ?", "weight": 12, "category": "logement"},
    {"id": 3, "question": "Avez-vous un testament ou une planification successorale ?", "weight": 10, "category": "succession"},
    {"id": 4, "question": "Vos assurances (RC, incendie, hospitalisation) sont-elles a jour ?", "weight": 10, "category": "assurances"},
    {"id": 5, "question": "Connaissez-vous vos droits en cas de licenciement ?", "weight": 8, "category": "travail"},
    {"id": 6, "question": "Avez-vous une procuration ou un mandat extrajudiciaire ?", "weight": 8, "category": "protection"},
    {"id": 7, "question": "Votre declaration fiscale est-elle a jour ?", "weight": 12, "category": "fiscal"},
    {"id": 8, "question": "Avez-vous un contrat de mariage ou convention de cohabitation ?", "weight": 10, "category": "famille"},
    {"id": 9, "question": "Vos donnees personnelles (RGPD) sont-elles protegees ?", "weight": 8, "category": "rgpd"},
    {"id": 10, "question": "Avez-vous verifie vos contrats d'abonnement (telecom, energie) ?", "weight": 10, "category": "consommation"},
]


def get_score_questions() -> list:
    """Retourne les 10 questions du Score."""
    return SCORE_QUESTIONS


def calculate_score(answers: List[dict]) -> dict:
    """Calcule le score de sante juridique.

    Args:
        answers: Liste de {"question_id": int, "answer": "yes"|"no"|"partial"|"na"}

    Returns:
        Score sur 100 + rapport detaille
    """
    if len(answers) < 5:
        raise ValueError("Minimum 5 reponses requises")

    ANSWER_VALUES = {"yes": 1.0, "partial": 0.5, "no": 0.0, "na": None}

    total_weight = 0
    earned_points = 0
    weak_points = []
    strong_points = []
    category_scores = {}

    for answer in answers:
        q_id = answer["question_id"]
        raw = answer["answer"].lower()
        value = ANSWER_VALUES.get(raw)

        question = next((q for q in SCORE_QUESTIONS if q["id"] == q_id), None)
        if not question:
            continue
        if value is None:
            continue

        weight = question["weight"]
        total_weight += weight
        points = weight * value
        earned_points += points

        cat = question["category"]
        if cat not in category_scores:
            category_scores[cat] = {"earned": 0, "total": 0}
        category_scores[cat]["earned"] += points
        category_scores[cat]["total"] += weight

        if value < 0.5:
            weak_points.append({
                "question": question["question"],
                "category": cat,
                "recommendation": _get_recommendation(q_id),
            })
        elif value == 1.0:
            strong_points.append({
                "question": question["question"],
                "category": cat,
            })

    score = round((earned_points / total_weight) * 100) if total_weight > 0 else 0

    # Rating
    if score >= 80:
        rating = "excellent"
        message = "Votre sante juridique est excellente. Continuez a maintenir vos documents a jour."
    elif score >= 60:
        rating = "bon"
        message = "Votre situation juridique est correcte mais quelques points meritent attention."
    elif score >= 40:
        rating = "moyen"
        message = "Plusieurs aspects de votre protection juridique necessitent une action."
    else:
        rating = "critique"
        message = "Votre situation juridique presente des risques importants. Agissez rapidement."

    cat_breakdown = {}
    for cat, data in category_scores.items():
        cat_score = round((data["earned"] / data["total"]) * 100) if data["total"] > 0 else 0
        cat_breakdown[cat] = cat_score

    return {
        "score": score,
        "rating": rating,
        "message": message,
        "total_questions": len(answers),
        "weak_points": weak_points,
        "strong_points": strong_points,
        "category_breakdown": cat_breakdown,
        "disclaimer": "Score indicatif d'auto-evaluation. Ne constitue pas un avis juridique.",
    }


def _get_recommendation(question_id: int) -> str:
    """Recommandation par question."""
    recommendations = {
        1: "Demandez une copie ecrite de votre contrat de travail a votre employeur (obligation legale art. 3 Loi du 3 juillet 1978).",
        2: "Enregistrez votre bail via MyMinfin.be — c'est gratuit et obligatoire (art. 227 Code des droits d'enregistrement).",
        3: "Consultez un notaire pour etablir un testament. Sans testament, c'est le Code civil qui decide.",
        4: "Verifiez vos polices. L'assurance RC familiale et incendie (locataire) sont quasi indispensables en Belgique.",
        5: "Consultez la fiche preavis sur Lexavo — calculez votre preavis exact selon la CCT n109.",
        6: "Une procuration extrajudiciaire protege vos interets si vous devenez incapable. Renseignez-vous aupres d'un notaire.",
        7: "Verifiez sur MyMinfin.be. Le delai de depot est generalement fin juin (IPP) ou fin septembre (ISOC).",
        8: "Un contrat de mariage protege vos biens. En cohabitation legale, la convention clarifie les droits de chacun.",
        9: "Exercez vos droits RGPD : demande d'acces, rectification, effacement via les formulaires du DPO.",
        10: "Comparez vos abonnements et verifiez les clauses de reconduction automatique (Loi du 28 aout 2011).",
    }
    return recommendations.get(question_id, "Consultez un professionnel pour un avis personnalise.")
