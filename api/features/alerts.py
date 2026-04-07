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


# Correspondance domaine → termes de recherche ChromaDB
_DOMAIN_QUERIES = {
    "travail":      "droit du travail contrat emploi licenciement salaire CCT",
    "bail":         "bail loyer locataire propriétaire expulsion garantie locative",
    "fiscal":       "impôt taxe TVA IPP ISOC déclaration fiscale",
    "famille":      "divorce pension alimentaire garde enfant mariage succession",
    "entreprise":   "société entreprise RGPD concurrence CSA faillite",
    "social":       "sécurité sociale chômage INAMI pension maladie",
    "immobilier":   "urbanisme permis construire copropriété vente immeuble",
    "environnement": "environnement permis pollution énergie déchet protection",
}


def get_alert_feed(domains: List[str], limit: int = 10, mock: bool = False) -> list:
    """Retourne des alertes depuis ChromaDB (données réelles)."""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from rag.retriever import retrieve

        effective_domains = domains if domains else list(_DOMAIN_QUERIES.keys())
        results = []
        seen_doc_ids = set()

        per_domain = max(1, limit // len(effective_domains)) if effective_domains else limit

        for domain in effective_domains:
            query = _DOMAIN_QUERIES.get(domain, domain)
            try:
                chunks = retrieve(query, top_k=per_domain * 2)
                count = 0
                for chunk in chunks:
                    if count >= per_domain:
                        break
                    doc_id = chunk.get("doc_id", "")
                    if doc_id in seen_doc_ids:
                        continue
                    seen_doc_ids.add(doc_id)
                    title = chunk.get("title") or doc_id or "Document juridique"
                    results.append({
                        "id": len(results) + 1,
                        "domain": domain,
                        "title": title[:120],
                        "summary": (chunk.get("chunk_text") or "")[:300].strip(),
                        "date": chunk.get("date", ""),
                        "source": chunk.get("source", "Base juridique Lexavo"),
                        "url": chunk.get("url", ""),
                    })
                    count += 1
            except Exception as e:
                log.warning("Erreur retrieve domaine %s : %s", domain, e)

        return results[:limit]

    except Exception as e:
        log.error("get_alert_feed erreur : %s", e)
        return []
