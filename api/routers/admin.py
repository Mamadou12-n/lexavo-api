"""Router Admin — endpoints admin reserves (role=admin uniquement)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import get_current_user as _get_current_user
from api.security import admin_audit

log = logging.getLogger("api.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: dict, request: Request, action: str) -> None:
    if current_user.get("role") != "admin":
        try:
            admin_audit(current_user["id"], f"{action}_denied_role", request, str(current_user.get("role")))
        except Exception:
            pass
        raise HTTPException(403, "Acces reserve a l'administrateur.")


@router.get("/legal-update-status")
def legal_update_status(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
) -> dict:
    """Retourne l'etat de la derniere mise a jour de la base juridique."""
    _require_admin(current_user, request, "legal_update_status")

    from rag.indexer_qdrant import get_index_stats

    stats = get_index_stats()

    log_dir = Path(__file__).parent.parent.parent / "logs"
    last_update_log: str | None = None
    last_update_time: str | None = None
    new_docs: int = 0
    if log_dir.exists():
        candidates = sorted(
            log_dir.glob("update_*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            f = candidates[0]
            last_update_log = f.name
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            last_update_time = mtime.isoformat()
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                import re
                m = re.search(r"(\d+)\s+nouveaux documents", content)
                if m:
                    new_docs = int(m.group(1))
            except Exception as exc:
                log.warning(f"Erreur lecture log {f}: {exc}")

    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7 or 7
    next_run = (now + timedelta(days=days_ahead)).replace(hour=3, minute=0, second=0, microsecond=0)

    try:
        admin_audit(current_user["id"], "legal_update_status_ok", request, "")
    except Exception:
        pass

    return {
        "qdrant": {
            "status": stats.get("status", "unknown"),
            "total_chunks": stats.get("total_chunks", 0),
            "total_documents_sample": stats.get("total_documents_sample", 0),
            "sources_sample": stats.get("sources_sample", {}),
        },
        "last_update": {
            "log_file": last_update_log,
            "completed_at": last_update_time,
            "new_docs_added": new_docs,
        },
        "next_scheduled_run": next_run.isoformat(),
        "cron": "0 3 * * 1 (every Monday 03:00 UTC)",
    }


@router.get("/alerts-status")
def alerts_status(
    request: Request,
    current_user: Annotated[dict, Depends(_get_current_user)],
) -> dict:
    """Retourne l'etat des alertes utilisateurs (combien notifies, quand)."""
    _require_admin(current_user, request, "alerts_status")

    from api.database import _get_conn, _fetchone, USE_PG

    PH = "%s" if USE_PG else "?"
    conn = _get_conn()

    out: dict = {}
    try:
        out["users_with_prefs"] = _fetchone(
            conn,
            "SELECT COUNT(*) AS n FROM alert_preferences WHERE domains IS NOT NULL AND domains != ''",
            (),
        )["n"]
    except Exception:
        out["users_with_prefs"] = None

    try:
        out["push_tokens"] = _fetchone(conn, "SELECT COUNT(*) AS n FROM push_tokens", ())["n"]
    except Exception:
        out["push_tokens"] = None

    try:
        out["alerts_sent_total"] = _fetchone(conn, "SELECT COUNT(*) AS n FROM alert_history", ())["n"]
    except Exception:
        out["alerts_sent_total"] = 0

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        out["alerts_sent_7d"] = _fetchone(
            conn,
            f"SELECT COUNT(*) AS n FROM alert_history WHERE notified_at >= {PH}",
            (cutoff,),
        )["n"]
    except Exception:
        out["alerts_sent_7d"] = 0

    try:
        admin_audit(current_user["id"], "alerts_status_ok", request, "")
    except Exception:
        pass

    return out
