"""cron_alerts.py — Notifie les users des nouvelles publications juridiques.

Lance apres cron_update.py pour matcher les nouveaux documents indexes avec
les preferences alert_preferences des users.

Usage:
    python cron_alerts.py                    # Tous les users
    python cron_alerts.py --since 7         # Docs depuis 7 jours
    python cron_alerts.py --dry-run         # Simulation, pas d'envoi push
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("cron_alerts")


# Mapping source/title -> domaines alertes (cf. api/features/alerts.py)
SOURCE_TO_DOMAIN: dict[str, list[str]] = {
    "loi_contrats_travail": ["travail"],
    "cct_109": ["travail"],
    "code_civil": ["bail", "famille", "immobilier"],
    "nouveau_code_civil": ["bail", "famille", "immobilier"],
    "cir_1992": ["fiscal"],
    "code_tva": ["fiscal"],
    "csa": ["entreprise"],
    "cde": ["entreprise"],
    "code_penal": ["famille"],
    "MONITEUR": ["travail", "bail", "fiscal", "famille", "entreprise", "social", "immobilier", "environnement"],
    "JUSTEL": ["travail", "bail", "fiscal", "famille", "entreprise", "social", "immobilier"],
    "CCT": ["travail", "social"],
    "INAMI": ["social"],
    "FSMA": ["entreprise"],
    "BNB": ["entreprise"],
    "WALLEX": ["immobilier", "environnement"],
    "GALLILEX": ["famille", "social"],
    "CODEX": ["immobilier", "environnement"],
    "BRUXELLES": ["bail", "immobilier"],
}


def get_recent_docs(days: int = 7) -> list[dict]:
    """Retourne les docs Qdrant indexes dans les N derniers jours."""
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        log.error("qdrant-client non installe")
        return []

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=30)

    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cutoff_date = cutoff_iso[:10]
    log.info(f"Recherche docs ajoutes depuis {cutoff_date}")

    docs: list[dict] = []
    seen: set[str] = set()
    offset = None
    page = 0
    while page < 50:
        try:
            result = client.scroll(
                collection_name="legal_docs_be",
                limit=500,
                offset=offset,
                with_payload=["doc_id", "source", "title", "date", "url"],
                with_vectors=False,
            )
        except Exception as exc:
            log.warning(f"Scroll Qdrant echoue : {exc}")
            break
        points, next_offset = result
        for p in points:
            doc_id = p.payload.get("doc_id", "")
            if doc_id in seen:
                continue
            seen.add(doc_id)
            doc_date = p.payload.get("date") or ""
            if doc_date and doc_date >= cutoff_date:
                docs.append(p.payload)
        if next_offset is None:
            break
        offset = next_offset
        page += 1

    log.info(f"{len(docs)} docs recents detectes (depuis {days}j)")
    return docs


def doc_domains(doc: dict) -> list[str]:
    """Inferer les domaines d'un doc selon sa source/titre."""
    source = (doc.get("source") or "").upper()
    title = (doc.get("title") or "").lower()
    domains: set[str] = set()

    for src_key, dom_list in SOURCE_TO_DOMAIN.items():
        if src_key.upper() in source or src_key.lower() in title:
            domains.update(dom_list)

    keyword_rules: list[tuple[tuple[str, ...], str]] = [
        (("travail", "emploi", "preavis"), "travail"),
        (("bail", "loyer", "logement"), "bail"),
        (("tva", "impot", "fiscal", "cir"), "fiscal"),
        (("divorce", "famille", "succession"), "famille"),
        (("societe", "entreprise", "csa", "rgpd", "donnees personnelles"), "entreprise"),
        (("environnement", "permis"), "environnement"),
        (("chomage", "pension", "inami"), "social"),
    ]
    for kws, domain in keyword_rules:
        if any(kw in title for kw in kws):
            domains.add(domain)
    return sorted(domains)


def get_users_with_prefs() -> list[dict]:
    try:
        from api.database import _get_conn, _fetchall
    except Exception as exc:
        log.error(f"Import database echoue : {exc}")
        return []

    conn = _get_conn()
    try:
        rows = _fetchall(
            conn,
            "SELECT ap.user_id, ap.domains, ap.frequency, u.email, u.language "
            "FROM alert_preferences ap JOIN users u ON u.id = ap.user_id "
            "WHERE ap.domains IS NOT NULL AND ap.domains != ''",
            (),
        )
    except Exception as exc:
        log.warning(f"Query alert_preferences echoue : {exc}")
        return []
    return [dict(r) for r in rows]


def match_user_to_docs(user: dict, docs: list[dict]) -> list[dict]:
    raw = user.get("domains") or ""
    user_domains = {d.strip() for d in raw.split(",") if d.strip()}
    if not user_domains:
        return []
    return [doc for doc in docs if user_domains & set(doc_domains(doc))]


def already_notified(user_id: int, doc_ids: Iterable[str]) -> set[str]:
    try:
        from api.database import _get_conn, _fetchall, USE_PG
    except Exception:
        return set()

    PH = "%s" if USE_PG else "?"
    conn = _get_conn()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS alert_history ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "  user_id INTEGER NOT NULL, "
            "  doc_id TEXT NOT NULL, "
            "  notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "  UNIQUE(user_id, doc_id))"
        )
        if hasattr(conn, "commit"):
            conn.commit()
    except Exception as exc:
        log.debug(f"create alert_history skip : {exc}")

    ids = list(doc_ids)
    if not ids:
        return set()
    placeholders = ",".join([PH] * len(ids))
    try:
        rows = _fetchall(
            conn,
            f"SELECT doc_id FROM alert_history WHERE user_id = {PH} AND doc_id IN ({placeholders})",
            (user_id, *ids),
        )
    except Exception:
        return set()
    return {r["doc_id"] for r in rows}


def record_notified(user_id: int, doc_ids: Iterable[str]) -> None:
    try:
        from api.database import _get_conn, USE_PG
    except Exception:
        return

    conn = _get_conn()
    sql = (
        "INSERT INTO alert_history (user_id, doc_id) VALUES (%s, %s) ON CONFLICT (user_id, doc_id) DO NOTHING"
        if USE_PG else
        "INSERT OR IGNORE INTO alert_history (user_id, doc_id) VALUES (?, ?)"
    )
    for doc_id in doc_ids:
        try:
            conn.execute(sql, (user_id, doc_id))
        except Exception as exc:
            log.debug(f"insert alert_history skip : {exc}")
    if hasattr(conn, "commit"):
        conn.commit()


def send_alert_push(user_id: int, docs: list[dict], lang: str = "fr") -> bool:
    try:
        from api.push import send_push_to_user
    except Exception as exc:
        log.warning(f"api.push indisponible : {exc}")
        return False

    n = len(docs)
    if n == 0:
        return False
    titles_preview = " | ".join((d.get("title") or "")[:50] for d in docs[:3])
    titles = {
        "fr": (f"{n} nouvelle(s) publication(s) juridique(s)", titles_preview),
        "nl": (f"{n} nieuwe juridische publicatie(s)", titles_preview),
        "en": (f"{n} new legal publication(s)", titles_preview),
        "de": (f"{n} neue juristische Veroffentlichung(en)", titles_preview),
    }
    title, body = titles.get(lang, titles["fr"])
    try:
        send_push_to_user(
            user_id=user_id,
            title=title,
            body=body,
            data={"type": "legal_update", "doc_count": n},
        )
        return True
    except Exception as exc:
        log.warning(f"send_push_to_user user={user_id} echoue : {exc}")
        return False


def run(days: int = 7, dry_run: bool = False) -> dict:
    log.info(f"=== Lexavo Alert Cron — {datetime.now().isoformat()} ===")
    log.info(f"Mode : {'DRY RUN' if dry_run else 'PRODUCTION'}")

    docs = get_recent_docs(days=days)
    if not docs:
        log.info("Aucun nouveau doc detecte. Fin.")
        return {"docs": 0, "users_notified": 0}

    users = get_users_with_prefs()
    log.info(f"{len(users)} users avec preferences alertes configurees")

    notified_count = 0
    for user in users:
        user_id = user["user_id"]
        lang = user.get("language") or "fr"
        matches = match_user_to_docs(user, docs)
        if not matches:
            continue
        match_ids = [d.get("doc_id") for d in matches if d.get("doc_id")]
        already = already_notified(user_id, match_ids)
        new_matches = [d for d in matches if d.get("doc_id") not in already]
        if not new_matches:
            continue
        log.info(f"  user={user_id} -> {len(new_matches)} docs (filtres : {user.get('domains')})")
        if dry_run:
            notified_count += 1
            continue
        if send_alert_push(user_id, new_matches, lang=lang):
            record_notified(user_id, [d["doc_id"] for d in new_matches if d.get("doc_id")])
            notified_count += 1

    log.info(f"=== Termine : {notified_count} users notifies sur {len(docs)} docs ===")
    return {"docs": len(docs), "users_notified": notified_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Lexavo Alert Cron")
    parser.add_argument("--days", type=int, default=7, help="Docs depuis N jours")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans envoi")
    args = parser.parse_args()

    summary = run(days=args.days, dry_run=args.dry_run)
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
