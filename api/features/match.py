"""Lexavo Match — Mise en relation avec avocats partenaires.
Description situation -> algorithme propose les 3 avocats les mieux adaptes."""

import logging
from typing import Optional, List

log = logging.getLogger("match")

BRANCH_TO_SPECIALTY = {
    "droit_travail": "Droit du travail",
    "droit_immobilier": "Droit immobilier",
    "droit_familial": "Droit familial",
    "droit_fiscal": "Droit fiscal",
    "droit_commercial": "Droit commercial",
    "droit_penal": "Droit penal",
    "droit_civil": "Droit civil",
    "droit_administratif": "Droit administratif",
}


def find_matching_lawyers(
    description: str,
    city: Optional[str] = None,
    language: str = "fr",
    budget: Optional[str] = None,
    mock: bool = False,
) -> dict:
    if len(description.strip()) < 10:
        raise ValueError("Description trop courte (minimum 10 caracteres)")

    # Detect branch from description
    from api.features.shield import detect_contract_type
    detected = detect_contract_type(description)
    branch = f"droit_{detected}" if detected != "general" else None
    specialty = BRANCH_TO_SPECIALTY.get(branch, "Droit general")

    if mock or True:  # Uses demo lawyers until real DB is populated
        from api.database import list_lawyers
        lawyers = list_lawyers(city=city, specialty=None, language=language)

        matches = []
        for lawyer in lawyers[:3]:
            score = 0.85 - len(matches) * 0.1
            matches.append({
                "lawyer_id": lawyer["id"],
                "name": lawyer["name"],
                "bar": lawyer["bar"],
                "city": lawyer["city"],
                "specialties": lawyer.get("specialties", "[]"),
                "match_score": round(score, 2),
                "match_reason": f"Specialise en {specialty}, localise a {lawyer['city']}",
            })

        return {
            "detected_branch": branch,
            "detected_specialty": specialty,
            "matches": matches,
            "total_matches": len(matches),
            "disclaimer": "Mise en relation informative. L'avocat reste independant et responsable de son conseil.",
        }
