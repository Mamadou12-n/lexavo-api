"""
Stripe billing for Lexavo — Subscriptions & Checkout.
Plans: free (5 questions/mois), pro (29€/mois), cabinet (99€/mois).
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

# ─── Plans ───────────────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "label": "Gratuit",
        "price_monthly": 0,
        "questions_per_month": 5,
        "features": ["5 questions/mois", "3 branches du droit", "Sources de base"],
    },
    "pro": {
        "label": "Pro",
        "price_monthly": 29,
        "questions_per_month": -1,  # illimite
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", ""),
        "features": [
            "Questions illimitees",
            "15 branches du droit",
            "Toutes les sources",
            "Historique complet",
            "Annuaire avocats premium",
        ],
    },
    "cabinet": {
        "label": "Cabinet",
        "price_monthly": 99,
        "questions_per_month": -1,  # illimite
        "stripe_price_id": os.getenv("STRIPE_PRICE_CABINET", ""),
        "features": [
            "Tout Pro inclus",
            "Multi-utilisateurs (5 comptes)",
            "Acces API",
            "Analytics & rapports",
            "Support prioritaire",
        ],
    },
}


# ─── Checkout ────────────────────────────────────────────────────────────────

def create_checkout_session(user_id: int, plan: str) -> dict:
    """Create a Stripe Checkout Session for subscription."""
    if plan not in ("pro", "cabinet"):
        raise HTTPException(
            status_code=400,
            detail="Plan invalide. Choisissez 'pro' ou 'cabinet'.",
        )

    if not stripe.api_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe non configure. Contactez le support.",
        )

    plan_config = PLANS[plan]
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
    """
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
                "message": f"Vous avez utilise vos {limit} questions gratuites ce mois-ci. Passez au plan Pro pour des questions illimitees.",
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
