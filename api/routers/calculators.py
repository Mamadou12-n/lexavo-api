"""Router Calculateurs — /calculators/*."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Annotated

from api.auth import get_current_user as _get_current_user
from api.routers.deps import limiter

log = logging.getLogger("api.calculators")

router = APIRouter(prefix="/calculators", tags=["calculators"])

_REL_MAP = {
    "enfant": "direct_line", "fils": "direct_line", "fille": "direct_line",
    "parent": "direct_line", "père": "direct_line", "pere": "direct_line",
    "mère": "direct_line", "mere": "direct_line",
    "epoux": "direct_line", "époux": "direct_line", "conjoint": "direct_line",
    "epouse": "direct_line", "épouse": "direct_line",
    "frere": "siblings", "frère": "siblings",
    "soeur": "siblings", "sœur": "siblings",
    "autre": "others", "other": "others",
    "oncle": "others", "tante": "others", "neveu": "others",
    "cousin": "others", "cousine": "others",
}


def _normalize_rel(raw: str) -> str:
    raw = str(raw).strip().lower()
    if raw in ("direct_line", "siblings", "others"):
        return raw
    return _REL_MAP.get(raw, raw)


@router.post("/notice-period")
@limiter.limit("30/minute")
def calc_notice(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Calculateur de préavis de licenciement (CCT n°109)."""
    from api.features.calculators import calculate_notice_period
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    try:
        years = int(body.get("years", body.get("anciennete", 0)))
        monthly_salary = float(
            body.get("monthly_salary") or body.get("salaire_mensuel")
            or body.get("salaire_brut_mensuel") or 0
        )
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    if monthly_salary <= 0:
        raise HTTPException(400, "Salaire mensuel requis (> 0)")
    return calculate_notice_period(years=years, monthly_salary=monthly_salary)


@router.post("/alimony")
@limiter.limit("30/minute")
def calc_alimony(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Calculateur de pension alimentaire (barème Renard)."""
    from api.features.calculators import calculate_alimony_renard
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    try:
        income_high = float(body.get("income_high", 0))
        income_low = float(body.get("income_low", 0))
        children = int(body.get("children", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    return calculate_alimony_renard(income_high=income_high, income_low=income_low, children=children)


@router.post("/succession")
@limiter.limit("30/minute")
def calc_succession(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Calculateur de droits de succession par région."""
    from api.features.calculators import calculate_succession_duties
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    region = body.get("region", "bruxelles")
    try:
        amount = float(body.get("amount", 0) or body.get("estate_value", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    relationship = _normalize_rel(body.get("relationship") or body.get("lien_parente") or "direct_line")
    return calculate_succession_duties(region=region, amount=amount, relationship=relationship)


@router.post("/indexation-loyer")
@limiter.limit("30/minute")
def calc_indexation_loyer(
    request: Request,
    body: dict,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Calculateur d'indexation de loyer (indice santé belge)."""
    from api.features.calculators import calculate_indexation_loyer
    from api.stripe_billing import check_quota
    check_quota(current_user["id"])
    try:
        loyer_base = float(body.get("loyer_base") or body.get("loyer_actuel") or body.get("loyer") or 0)
        indice_depart = float(body.get("indice_depart") or body.get("indice_initial") or body.get("indice_base") or 0)
        indice_nouveau = float(body.get("indice_nouveau") or body.get("indice_actuel") or body.get("indice_courant") or 0)
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    try:
        return calculate_indexation_loyer(
            loyer_base=loyer_base,
            indice_depart=indice_depart,
            indice_nouveau=indice_nouveau,
            region=body.get("region", "bruxelles"),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
