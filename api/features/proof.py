"""Lexavo Proof — Construire son dossier.
Documenter des faits au fil du temps avec timestamps automatiques."""

import logging
from datetime import datetime
from typing import Optional, List

log = logging.getLogger("proof")


def create_case(user_id: int, title: str, category: str = "general", description: str = "") -> dict:
    if len(title.strip()) < 3:
        raise ValueError("Titre requis (minimum 3 caracteres)")
    return {
        "case_id": f"PROOF-{datetime.now().strftime('%Y%m%d%H%M')}-{user_id}",
        "user_id": user_id,
        "title": title,
        "category": category,
        "description": description,
        "entries": [],
        "created_at": datetime.now().isoformat(),
        "status": "open",
    }


def add_entry(case: dict, entry_type: str, content: str, evidence_description: Optional[str] = None) -> dict:
    if len(content.strip()) < 5:
        raise ValueError("Contenu requis (minimum 5 caracteres)")

    entry = {
        "entry_id": len(case.get("entries", [])) + 1,
        "type": entry_type,  # "fait", "preuve", "temoin", "document"
        "content": content,
        "evidence_description": evidence_description,
        "timestamp": datetime.now().isoformat(),
        "verified": False,
    }
    case.setdefault("entries", []).append(entry)
    return entry


def get_case_summary(case: dict) -> dict:
    entries = case.get("entries", [])
    return {
        "case_id": case.get("case_id"),
        "title": case.get("title"),
        "total_entries": len(entries),
        "types_count": {
            t: sum(1 for e in entries if e.get("type") == t)
            for t in set(e.get("type") for e in entries)
        },
        "date_range": {
            "first": entries[0]["timestamp"] if entries else None,
            "last": entries[-1]["timestamp"] if entries else None,
        },
        "status": case.get("status"),
        "disclaimer": "Journal factuel personnel. Ne constitue pas un dossier juridique formel.",
    }
