"""
Stripe billing for Lexavo — Subscriptions & Checkout.
7 tiers : free, basic (4,99€), pro (49,99€), business (79,99€),
          firm_s (149,99€), firm_m (299,99€), enterprise (sur devis).
Beta : gratuit pour tous jusqu'au 1er octobre 2026.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import HTTPException, Request, status

from api.database import (
    get_subscription,
    update_subscription,
    get_subscription_by_stripe_customer,
    get_user_by_id,
    get_user_by_email,
)

log = logging.getLogger("stripe_billing")

# ─── Config ──────────────────────────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

FRONTEND_URL = os.getenv("LEXAVO_FRONTEND_URL", "http://localhost:8081")

# Beta : gratuit pour tous jusqu'a cette date (YYYY-MM-DD)
BETA_END_DATE = os.getenv("LEXAVO_BETA_END", "2026-10-01")

def is_beta_active() -> bool:
    """True tant qu'on est dans la periode beta (gratuit pour tous)."""
    try:
        end = datetime.strptime(BETA_END_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < end
    except ValueError:
        return False

# ─── Plans ───────────────────────────────────────────────────────────────────
# Prix en .99 — pricing psychologique
PLANS = {
    "free": {
        "label": "Lexavo Free",
        "subtitle": "Etudiants en droit",
        "price_monthly": 0,
        "price_annual": 0,
        "questions_per_month": 3,
        "max_users": 1,
        "features": [
            "3 questions / mois",
            "Recherche vectorielle",
            "Acces a la base juridique",
            "Lexavo Score",
        ],
    },
    "basic": {
        "label": "Lexavo Basic",
        "subtitle": "Particuliers",
        "price_monthly": 4.99,
        "price_annual": 49.99,
        "founding_price": 3.99,
        "questions_per_month": -1,
        "max_users": 1,
        "stripe_price_id": os.getenv("STRIPE_PRICE_BASIC", ""),
        "stripe_price_annual_id": os.getenv("STRIPE_PRICE_BASIC_ANNUAL", ""),
        "features": [
            "Chat IA illimite",
            "15 branches du droit",
            "3 modeles de contrats / mois",
            "Alertes legislatives de base",
            "Lexavo Score",
            "Historique complet",
        ],
    },
    "pro": {
        "label": "Lexavo Pro",
        "subtitle": "Avocats & juristes",
        "price_monthly": 49.99,
        "price_annual": 499.99,
        "founding_price": 39.99,
        "questions_per_month": -1,
        "max_users": 1,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", ""),
        "stripe_price_annual_id": os.getenv("STRIPE_PRICE_PRO_ANNUAL", ""),
        "features": [
            "Tout Basic inclus",
            "Base documentaire complete",
            "Generation de documents illimitee",
            "Analyse de contrats (Shield)",
            "Label Avocat certifie Lexavo",
            "Leads qualifies via l'app",
            "Statistiques profil",
            "Support prioritaire (48h)",
        ],
    },
    "business": {
        "label": "Lexavo Business",
        "subtitle": "PME (jusqu'a 5 utilisateurs)",
        "price_monthly": 79.99,
        "price_annual": 799.99,
        "founding_price": 59.99,
        "questions_per_month": -1,
        "max_users": 5,
        "stripe_price_id": os.getenv("STRIPE_PRICE_BUSINESS", ""),
        "stripe_price_annual_id": os.getenv("STRIPE_PRICE_BUSINESS_ANNUAL", ""),
        "features": [
            "Tout Pro inclus",
            "Jusqu'a 5 utilisateurs",
            "Analyse de contrats illimitee",
            "Generation de documents illimitee",
            "Alertes RGPD et conformite",
            "Export PDF & rapports",
            "Support prioritaire",
        ],
    },
    "firm_s": {
        "label": "Lexavo Firm",
        "subtitle": "Petit cabinet (2-10 avocats)",
        "price_monthly": 149.99,
        "price_annual": None,  # sur devis pour annuel
        "questions_per_month": -1,
        "max_users": 10,
        "stripe_price_id": os.getenv("STRIPE_PRICE_FIRM_S", ""),
        "features": [
            "Tout Business inclus",
            "Jusqu'a 10 utilisateurs",
            "Documents de marque (logo cabinet)",
            "Tableau de bord gestion dossiers",
            "Formation et onboarding inclus",
            "Analytics avances",
            "Support dedie",
        ],
    },
    "firm_m": {
        "label": "Lexavo Firm+",
        "subtitle": "Cabinet moyen (10-30 avocats)",
        "price_monthly": 299.99,
        "price_annual": None,
        "questions_per_month": -1,
        "max_users": 30,
        "stripe_price_id": os.getenv("STRIPE_PRICE_FIRM_M", ""),
        "features": [
            "Tout Firm inclus",
            "Jusqu'a 30 utilisateurs",
            "API acces complet",
            "Integrations sur mesure",
            "Account manager dedie",
        ],
    },
    "enterprise": {
        "label": "Lexavo Enterprise",
        "subtitle": "Grandes entreprises & directions juridiques",
        "price_monthly": -1,  # sur devis
        "price_annual": None,
        "questions_per_month": -1,
        "max_users": -1,  # illimite
        "features": [
            "Tout Firm+ inclus",
            "Utilisateurs illimites",
            "SLA garanti",
            "Deploiement on-premise possible",
            "Formation equipe complete",
            "Support 24/7",
        ],
    },
}

# Plans payants pouvant etre achetes via Stripe checkout
PAID_PLANS = {"basic", "pro", "business", "firm_s", "firm_m"}


# ─── Checkout ────────────────────────────────────────────────────────────────

def create_checkout_session(user_id: int, plan: str, billing: str = "monthly") -> dict:
    """Create a Stripe Checkout Session for subscription.
    billing: 'monthly' ou 'annual'.
    """
    if plan not in PAID_PLANS:
        raise HTTPException(
            status_code=400,
            detail=f"Plan invalide. Choisissez parmi : {', '.join(sorted(PAID_PLANS))}.",
        )

    if not stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe non configure. Contactez le support.",
        )

    plan_config = PLANS[plan]
    if billing == "annual":
        annual_id = plan_config.get("stripe_price_annual_id", "")
        if not annual_id:
            raise HTTPException(
                status_code=400,
                detail=f"L'abonnement annuel n'est pas disponible pour le plan {plan}. Contactez-nous.",
            )
        price_id = annual_id
    else:
        price_id = plan_config.get("stripe_price_id", "")
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Prix Stripe non configure pour le plan {plan}.",
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    # Get or create Stripe customer
    sub = get_subscription(user_id)
    customer_id = sub.get("stripe_customer_id") if sub else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            name=user["name"],
            metadata={"lexavo_user_id": str(user_id)},
        )
        customer_id = customer.id
        update_subscription(
            user_id=user_id,
            plan="free",
            stripe_customer_id=customer_id,
        )

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing/cancel",
            metadata={
                "lexavo_user_id": str(user_id),
                "lexavo_plan": plan,
            },
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        log.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=502, detail="Erreur Stripe. Reessayez.")


# ─── Customer Portal ────────────────────────────────────────────────────────

def create_portal_session(user_id: int) -> dict:
    """Create a Stripe Customer Portal session to manage subscription."""
    sub = get_subscription(user_id)
    if not sub or not sub.get("stripe_customer_id"):
        raise HTTPException(
            status_code=400,
            detail="Aucun abonnement Stripe actif.",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=sub["stripe_customer_id"],
            return_url=f"{FRONTEND_URL}/settings",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        log.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=502, detail="Erreur Stripe. Reessayez.")


# ─── Webhook ─────────────────────────────────────────────────────────────────

def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Process Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        log.error("STRIPE_WEBHOOK_SECRET non configure — webhook rejete par securite.")
        raise HTTPException(
            status_code=503,
            detail="Webhook Stripe non configure. Contactez l'administrateur.",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload invalide.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature invalide.")

    event_type = event["type"]
    data = event["data"]["object"]

    log.info(f"Webhook Stripe: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data)

    return {"status": "ok", "event": event_type}


def _handle_checkout_completed(session: dict):
    """Checkout completed — activate subscription."""
    customer_id = session.get("customer")
    metadata = session.get("metadata", {})
    user_id = metadata.get("lexavo_user_id")
    plan = metadata.get("lexavo_plan", "pro")
    subscription_id = session.get("subscription")

    if not user_id:
        log.warning("Checkout sans lexavo_user_id dans metadata")
        return

    update_subscription(
        user_id=int(user_id),
        plan=plan,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        status="active",
    )
    log.info(f"Subscription activee: user={user_id}, plan={plan}")


def _handle_subscription_updated(subscription: dict):
    """Subscription updated (upgrade, downgrade, renewal)."""
    customer_id = subscription.get("customer")
    sub = get_subscription_by_stripe_customer(customer_id)
    if not sub:
        log.warning(f"Subscription update pour customer inconnu: {customer_id}")
        return

    stripe_status = subscription.get("status", "active")
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "trialing": "trialing",
    }
    mapped_status = status_map.get(stripe_status, "active")

    period_start = subscription.get("current_period_start")
    period_end = subscription.get("current_period_end")

    start_str = datetime.fromtimestamp(period_start, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if period_start else None
    end_str = datetime.fromtimestamp(period_end, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if period_end else None

    update_subscription(
        user_id=sub["user_id"],
        plan=sub["plan"],
        status=mapped_status,
        current_period_start=start_str,
        current_period_end=end_str,
    )
    log.info(f"Subscription updated: user={sub['user_id']}, status={mapped_status}")


def _handle_subscription_deleted(subscription: dict):
    """Subscription canceled — downgrade to free."""
    customer_id = subscription.get("customer")
    sub = get_subscription_by_stripe_customer(customer_id)
    if not sub:
        return

    update_subscription(
        user_id=sub["user_id"],
        plan="free",
        status="canceled",
    )
    log.info(f"Subscription annulee: user={sub['user_id']} -> free")


def _handle_payment_failed(invoice: dict):
    """Payment failed — mark as past_due."""
    customer_id = invoice.get("customer")
    sub = get_subscription_by_stripe_customer(customer_id)
    if not sub:
        return

    update_subscription(
        user_id=sub["user_id"],
        plan=sub["plan"],
        status="past_due",
    )
    log.info(f"Paiement echoue: user={sub['user_id']}")


# ─── Quota check ─────────────────────────────────────────────────────────────

def check_quota(user_id: int) -> dict:
    """
    Check if user can ask a question.
    Returns quota info. Raises HTTPException if quota exceeded.
    Pendant la beta, tout le monde a un acces illimite.
    """
    # Beta = illimite pour tous
    if is_beta_active():
        sub = get_subscription(user_id)
        return {
            "allowed": True,
            "plan": sub.get("plan", "free") if sub else "free",
            "questions_used": sub.get("questions_used", 0) if sub else 0,
            "questions_limit": -1,
            "beta": True,
            "beta_end": BETA_END_DATE,
        }

    sub = get_subscription(user_id)
    plan = sub.get("plan", "free") if sub else "free"
    plan_config = PLANS.get(plan, PLANS["free"])
    limit = plan_config["questions_per_month"]

    # Unlimited plans
    if limit == -1:
        return {
            "allowed": True,
            "plan": plan,
            "questions_used": sub.get("questions_used", 0) if sub else 0,
            "questions_limit": -1,
        }

    questions_used = sub.get("questions_used", 0) if sub else 0

    if questions_used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Quota mensuel atteint",
                "message": f"Vous avez utilise vos {limit} questions gratuites ce mois-ci. Passez au plan Basic (4,99€/mois) pour un acces illimite.",
                "plan": plan,
                "questions_used": questions_used,
                "questions_limit": limit,
                "upgrade_url": f"{FRONTEND_URL}/billing/upgrade",
            },
        )

    return {
        "allowed": True,
        "plan": plan,
        "questions_used": questions_used,
        "questions_limit": limit,
        "questions_remaining": limit - questions_used,
    }


def cancel_subscription(user_id: int) -> dict:
    """
    Annule l'abonnement Stripe à la fin de la période en cours (cancel_at_period_end).
    Si pas de Stripe configuré, met le statut en 'canceled' en base directement.
    """
    sub = get_subscription(user_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Aucun abonnement trouvé.")

    stripe_sub_id = sub.get("stripe_subscription_id")

    if stripe_sub_id and stripe.api_key:
        try:
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        except stripe.error.StripeError as e:
            log.error(f"Stripe cancel error: {e}")
            raise HTTPException(status_code=502, detail=f"Erreur Stripe : {str(e)}")
    else:
        # Pas de Stripe configuré — annulation immédiate en base
        update_subscription(
            user_id=user_id,
            plan=sub.get("plan", "free"),
            status="canceled",
        )

    return {"status": "canceled", "message": "Abonnement annulé à la fin de la période en cours."}


def restore_subscription(user_id: int) -> dict:
    """
    Réactive un abonnement dont cancel_at_period_end=True.
    Uniquement possible si l'abonnement n'est pas encore terminé.
    """
    sub = get_subscription(user_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Aucun abonnement trouvé.")

    stripe_sub_id = sub.get("stripe_subscription_id")

    if stripe_sub_id and stripe.api_key:
        try:
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=False)
        except stripe.error.StripeError as e:
            log.error(f"Stripe restore error: {e}")
            raise HTTPException(status_code=502, detail=f"Erreur Stripe : {str(e)}")
    else:
        update_subscription(
            user_id=user_id,
            plan=sub.get("plan", "free"),
            status="active",
        )

    return {"status": "active", "message": "Abonnement réactivé avec succès."}
