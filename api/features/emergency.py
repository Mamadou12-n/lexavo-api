"""Lexavo Emergency — Bouton rouge, avocat en 2h.
Situation urgente -> formulaire rapide -> notification avocat -> 49 EUR.
Persiste en base de donnees (PostgreSQL/SQLite)."""

import logging
from datetime import datetime

log = logging.getLogger("emergency")

EMERGENCY_CATEGORIES = [
    {"id": "garde_a_vue", "label": "Garde a vue / Arrestation", "name": "Garde a vue", "emoji": "\ud83d\ude94", "description": "Arrestation, detention, garde a vue", "priority": "critical"},
    {"id": "expulsion", "label": "Expulsion imminente", "name": "Expulsion", "emoji": "\ud83c\udfe0", "description": "Menace d'expulsion du logement", "priority": "critical"},
    {"id": "licenciement", "label": "Licenciement immediat", "name": "Licenciement", "emoji": "\ud83d\udc77", "description": "Licenciement abusif ou immediat", "priority": "high"},
    {"id": "violence", "label": "Violence domestique", "name": "Violence", "emoji": "\ud83d\udee1\ufe0f", "description": "Violence conjugale ou domestique", "priority": "critical"},
    {"id": "saisie", "label": "Saisie de biens", "name": "Saisie", "emoji": "\ud83d\udce6", "description": "Saisie mobiliere ou immobiliere", "priority": "high"},
    {"id": "accident", "label": "Accident / Blessure", "name": "Accident", "emoji": "\ud83d\ude91", "description": "Accident de la route ou du travail", "priority": "high"},
    {"id": "autre", "label": "Autre urgence juridique", "name": "Autre urgence", "emoji": "\u26a0\ufe0f", "description": "Toute autre situation urgente", "priority": "medium"},
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
