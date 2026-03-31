"""Lexavo Emergency — Bouton rouge, avocat en 2h.
Situation urgente -> formulaire rapide -> notification avocat -> 49 EUR.
Persiste en base de donnees (PostgreSQL/SQLite)."""

import logging
from datetime import datetime

log = logging.getLogger("emergency")

EMERGENCY_CATEGORIES = [
    {"id": "garde_a_vue", "label": "Garde a vue / Arrestation", "priority": "critical"},
    {"id": "expulsion", "label": "Expulsion imminente", "priority": "critical"},
    {"id": "licenciement", "label": "Licenciement immediat", "priority": "high"},
    {"id": "violence", "label": "Violence domestique", "priority": "critical"},
    {"id": "saisie", "label": "Saisie de biens", "priority": "high"},
    {"id": "accident", "label": "Accident / Blessure", "priority": "high"},
    {"id": "autre", "label": "Autre urgence juridique", "priority": "medium"},
]

EMERGENCY_PRICE_CENTS = 4900  # 49 EUR


def get_categories() -> list:
    return EMERGENCY_CATEGORIES


def create_emergency_request(
    user_id: int, category: str, description: str,
    phone: str, city: str, mock: bool = False,
) -> dict:
    if len(description.strip()) < 20:
        raise ValueError("Decrivez votre situation (minimum 20 caracteres)")
    if len(phone.strip()) < 8:
        raise ValueError("Numero de telephone requis")

    cat = next((c for c in EMERGENCY_CATEGORIES if c["id"] == category), None)
    if not cat:
        cat = {"id": "autre", "label": "Autre", "priority": "medium"}

    # Persister en DB
    from api.database import create_emergency_request as db_create
    db_record = db_create(
        user_id=user_id,
        category=cat["id"],
        priority=cat["priority"],
        description=description.strip(),
        phone=phone.strip(),
        city=city.strip(),
    )

    return {
        "request_id": f"URG-{db_record['id']}",
        "id": db_record["id"],
        "user_id": user_id,
        "category": cat["id"],
        "category_label": cat["label"],
        "priority": cat["priority"],
        "description": description,
        "phone": phone,
        "city": city,
        "status": "pending",
        "price_cents": EMERGENCY_PRICE_CENTS,
        "estimated_callback": "Dans les 2 heures",
        "created_at": str(db_record.get("created_at", datetime.now().isoformat())),
        "disclaimer": "Service de mise en relation urgente. L'avocat exerce sous sa propre responsabilite.",
    }
