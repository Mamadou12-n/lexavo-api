"""Router admin — /admin/beta-funnel/*

Endpoints de pilotage manuel du funnel beta→paid.
Protection : header X-Admin-Key requis (env LEXAVO_ADMIN_KEY).
Usage prevu : tests pre-prod, relance manuelle, monitoring.
"""

from __future__ import annotations

import os
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from api.beta_funnel import (
    run_daily_beta_funnel,
    trigger_funnel_stage,
    days_until_beta_end,
    FUNNEL_STAGES,
)

log = logging.getLogger("api.beta_funnel_router")

router = APIRouter(prefix="/admin/beta-funnel", tags=["admin"])

ADMIN_KEY = os.getenv("LEXAVO_ADMIN_KEY", "")


# ─── Auth admin ──────────────────────────────────────────────────────────────

def require_admin_key(
    x_admin_key: str | None = None,
) -> None:
    from fastapi import Header
    # Re-import ici pour pouvoir utiliser Header comme default dans la signature
    # (FastAPI resout les dependencies via Depends, pas via la signature directe)
    pass


def _check_admin(x_admin_key: str = "") -> None:
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LEXAVO_ADMIN_KEY non configuree cote serveur.",
        )
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cle admin invalide.",
        )


def admin_auth(x_admin_key: str = "") -> None:
    """Dependency FastAPI : valide le header X-Admin-Key."""
    _check_admin(x_admin_key)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class FunnelStatusResponse(BaseModel):
    today: str
    days_until_beta_end: int
    beta_end_date: str
    next_milestone: str | None
    days_to_next: int | None


class TriggerRequest(BaseModel):
    milestone: str  # "j30" | "j7" | "j0"
    dry_run: bool = False


class TriggerResponse(BaseModel):
    milestone: str
    dry_run: bool
    sent: int
    errors: list[str]


class DailyRunResponse(BaseModel):
    today: str
    days_until_end: int
    stage_triggered: str | None
    j30_sent: int
    j7_sent: int
    j0_sent: int
    errors: list[str]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status", response_model=FunnelStatusResponse)
def get_funnel_status(
    x_admin_key: str = Header(default=""),
) -> FunnelStatusResponse:
    """Etat du funnel : jours restants, prochain milestone."""
    _check_admin(x_admin_key)
    days_left = days_until_beta_end()
    next_milestone = None
    days_to_next = None

    # Prochain milestone non encore atteint
    for stage in sorted(FUNNEL_STAGES, key=lambda s: s["days_before"], reverse=True):
        if days_left >= stage["days_before"]:
            next_milestone = stage["email_template"]
            days_to_next = days_left - stage["days_before"]
            break

    return FunnelStatusResponse(
        today=date.today().isoformat(),
        days_until_beta_end=days_left,
        beta_end_date="2026-10-01",
        next_milestone=next_milestone,
        days_to_next=days_to_next,
    )


@router.post("/trigger", response_model=TriggerResponse)
def trigger_milestone(
    body: TriggerRequest,
    x_admin_key: str = Header(default=""),
) -> TriggerResponse:
    """Declenche manuellement un milestone du funnel.

    dry_run=True : simule sans envoyer ni marquer en DB.
    """
    _check_admin(x_admin_key)

    valid = {s["email_template"] for s in FUNNEL_STAGES}
    if body.milestone not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Milestone invalide. Valeurs : {sorted(valid)}",
        )

    stage = next(s for s in FUNNEL_STAGES if s["email_template"] == body.milestone)

    if body.dry_run:
        log.info("DRY-RUN trigger milestone=%s (admin)", body.milestone)
        return TriggerResponse(
            milestone=body.milestone,
            dry_run=True,
            sent=0,
            errors=["dry_run=True : aucun email envoye"],
        )

    log.info("Admin trigger milestone=%s", body.milestone)
    result = trigger_funnel_stage(stage)

    return TriggerResponse(
        milestone=body.milestone,
        dry_run=False,
        sent=result["sent"],
        errors=result["errors"],
    )


@router.post("/run-daily", response_model=DailyRunResponse)
def run_daily(
    x_admin_key: str = Header(default=""),
) -> DailyRunResponse:
    """Execute le cron quotidien manuellement (idempotent).

    Utile pour tester le workflow complet sans attendre le cron GitHub Actions.
    """
    _check_admin(x_admin_key)
    log.info("Admin run-daily beta funnel")
    result: dict[str, Any] = run_daily_beta_funnel()
    return DailyRunResponse(**result)
