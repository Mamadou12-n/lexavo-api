"""Router Billing — /billing/*."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Annotated

from api.models import (
    CheckoutRequest, CheckoutResponse, PortalResponse,
    SubscriptionResponse, PlanInfo, PlansResponse,
)
from api.auth import get_current_user as _get_current_user

log = logging.getLogger("api.billing")

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=PlansResponse)
def list_plans():
    """Liste les plans tarifaires disponibles."""
    from api.stripe_billing import PLANS, is_beta_active, BETA_END_DATE
    plans = [
        PlanInfo(
            key=key,
            label=cfg["label"],
            subtitle=cfg.get("subtitle", ""),
            price_monthly=cfg["price_monthly"],
            price_annual=cfg.get("price_annual"),
            founding_price=cfg.get("founding_price"),
            max_users=cfg.get("max_users", 1),
            questions_per_month=cfg["questions_per_month"],
            features=cfg["features"],
        )
        for key, cfg in PLANS.items()
    ]
    return PlansResponse(
        plans=plans,
        beta_active=is_beta_active(),
        beta_end=BETA_END_DATE if is_beta_active() else None,
    )


@router.get("/subscription", response_model=SubscriptionResponse)
def get_my_subscription(current_user: Annotated[dict, Depends(_get_current_user)]):
    """État de l'abonnement de l'utilisateur connecté."""
    from api.database import get_subscription
    from api.stripe_billing import PLANS, is_beta_active, BETA_END_DATE

    sub = get_subscription(current_user["id"])
    plan = sub.get("plan", "free") if sub else "free"
    plan_config = PLANS.get(plan, PLANS["free"])
    limit = plan_config["questions_per_month"]
    used = sub.get("questions_used", 0) if sub else 0
    beta = is_beta_active()

    return SubscriptionResponse(
        plan=plan,
        status=sub.get("status", "active") if sub else "active",
        questions_used=used,
        questions_limit=-1 if beta else limit,
        questions_remaining=None if (beta or limit == -1) else (limit - used),
        current_period_end=sub.get("current_period_end") if sub else None,
        beta=beta,
        beta_end=BETA_END_DATE if beta else None,
    )


@router.get("/quota/status")
def get_quota_status_endpoint(
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Etat du quota avec niveau de warning paywall progressif.

    Ne consomme pas de quota — pour le mobile (banner + modals).
    Retourne :
    - warning_level : 'none' | 'soft' (50%+) | 'hard' (80%+) | 'blocked' (100%)
    - upgrade_recommended : True si warning_level in ('hard', 'blocked')
    - next_reset : ISO datetime du prochain reset mensuel
    """
    from api.stripe_billing import get_quota_status
    return get_quota_status(current_user["id"])


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    current_user: Annotated[dict, Depends(_get_current_user)],
):
    """Créer une session Checkout pour s'abonner à un plan payant."""
    from api.stripe_billing import create_checkout_session
    result = create_checkout_session(current_user["id"], request.plan, request.billing)
    return CheckoutResponse(**result)


@router.post("/portal", response_model=PortalResponse)
def create_portal(current_user: Annotated[dict, Depends(_get_current_user)]):
    """Ouvrir le portail client pour gérer l'abonnement."""
    from api.stripe_billing import create_portal_session
    result = create_portal_session(current_user["id"])
    return PortalResponse(**result)


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Webhook paiement — traite les événements de facturation."""
    from api.stripe_billing import handle_webhook
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not sig:
        raise HTTPException(400, "Signature manquante")
    return handle_webhook(payload, sig)
