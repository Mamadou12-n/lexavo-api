"""Lexavo Alertes — Alertes legislatives personnalisees.
L'utilisateur choisit ses domaines, notification push quand une loi change."""

import logging
from typing import List, Optional
from datetime import datetime

log = logging.getLogger("alerts")

ALERT_DOMAINS = [
    {"id": "travail", "label": "Droit du travail", "description": "Contrats, licenciement, salaire minimum"},
    {"id": "bail", "label": "Droit du bail", "description": "Loyers, expulsion, garantie locative"},
    {"id": "fiscal", "label": "Droit fiscal", "description": "IPP, ISOC, TVA, deductions"},
    {"id": "famille", "label": "Droit familial", "description": "Divorce, pension alimentaire, garde"},
    {"id": "entreprise", "label": "Droit des entreprises", "description": "CSA, RGPD, concurrence"},
    {"id": "social", "label": "Securite sociale", "description": "Chomage, INAMI, pensions"},
    {"id": "immobilier", "label": "Droit immobilier", "description": "Urbanisme, copropriete, vente"},
    {"id": "environnement", "label": "Droit de l'environnement", "description": "Permis, pollution, energie"},
]


def get_alert_domains() -> list:
    return ALERT_DOMAINS


def save_preferences(user_id: int, domains: List[str]) -> dict:
    valid = [d["id"] for d in ALERT_DOMAINS]
    selected = [d for d in domains if d in valid]
    return {"user_id": user_id, "domains": selected, "saved_at": datetime.now().isoformat()}


def get_alert_feed(domains: List[str], limit: int = 10, mock: bool = False) -> list:
    if mock:  # Demo feed — real feed via Moniteur belge scraping planned
        feed = [
            {"id": 1, "domain": "travail", "title": "Nouvelle CCT sur le teletravail structurel", "summary": "Le CNT a adopte la CCT n°149/2 rendant obligatoire une politique de teletravail ecrite.", "date": "2026-03-15", "source": "Moniteur belge", "url": ""},
            {"id": 2, "domain": "fiscal", "title": "Modification des tranches IPP 2026", "summary": "Indexation annuelle des baremes de l'impot des personnes physiques.", "date": "2026-03-10", "source": "SPF Finances", "url": ""},
            {"id": 3, "domain": "bail", "title": "Plafonnement de l'indexation des loyers prolonge", "summary": "Le mecanisme de protection contre l'indexation excessive des loyers est prolonge jusqu'en 2027.", "date": "2026-03-01", "source": "Moniteur belge", "url": ""},
            {"id": 4, "domain": "entreprise", "title": "Nouvelles obligations RGPD pour les PME", "summary": "L'APD publie de nouvelles lignes directrices simplifiees pour les PME de moins de 50 travailleurs.", "date": "2026-02-28", "source": "APD", "url": ""},
            {"id": 5, "domain": "social", "title": "Revalorisation des allocations de chomage", "summary": "Augmentation de 2% des allocations de chomage a partir du 1er avril 2026.", "date": "2026-02-25", "source": "ONEM", "url": ""},
        ]
        return [a for a in feed if a["domain"] in domains][:limit] if domains else feed[:limit]
