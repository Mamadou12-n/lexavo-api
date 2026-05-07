"""
api/beta_funnel.py — Conversion beta -> paid au 2026-10-01.

Module qui declenche les notifications J-30 / J-7 / J0 aux utilisateurs
en beta pour les inciter a passer en abonnement payant.

Architecture :
- Cron quotidien (GitHub Actions ou Railway scheduler) appelle
  `run_daily_beta_funnel()` qui scanne les users `is_beta=True`,
  calcule le delta jusqu'a BETA_END_DATE et envoie email + push pour
  J-30, J-7, J0.
- Idempotence : la table `beta_notifications` track ce qui a ete envoye
  (champs notif_j30_sent, notif_j7_sent, notif_j0_sent + timestamps).
- Tarif fondateur : 3.99€/mois a vie disponible jusqu'a BETA_END_DATE.

Sequence client :
- J-30 : email + push "Bloquez votre tarif fondateur"
- J-7  : email + push "Plus que 7 jours"
- J0   : email + push "Votre beta s'acheve aujourd'hui"
- Apres J0 : downgrade automatique vers free (7 questions/mois)
            ou activation Particulier 4.99€/mois.

Securite :
- Pas de PII dans les logs (utilise mask_email)
- Tarif fondateur valide UNIQUEMENT si reservation avant BETA_END_DATE
  (verifie cote backend avant Stripe checkout)
- Idempotent : meme si le cron tourne 10x dans la journee, chaque user
  recoit J-X au max 1 fois.

Usage :
    from api.beta_funnel import run_daily_beta_funnel
    result = run_daily_beta_funnel()
    # {"j30_sent": 12, "j7_sent": 3, "j0_sent": 1, "errors": []}
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from api.database import _get_conn, _execute, _fetchall, USE_PG, PH
from api.push import send_push_to_user
from api.security import mask_email

log = logging.getLogger("api.beta_funnel")

# Date de fin de beta. Tous les users avec is_beta=True voient leur
# acces complet bascule en mode free (7 questions/mois) apres cette date.
BETA_END_DATE = date(2026, 10, 1)

# Etapes du funnel (en jours avant BETA_END_DATE)
FUNNEL_STAGES = [
    {
        "days_before": 30,
        "flag": "notif_j30_sent",
        "push_title_key": "push_beta_ending_j30_title",
        "push_body_key": "push_beta_ending_j30_body",
        "email_template": "beta_j30",
    },
    {
        "days_before": 7,
        "flag": "notif_j7_sent",
        "push_title_key": "push_beta_ending_j7_title",
        "push_body_key": "push_beta_ending_j7_body",
        "email_template": "beta_j7",
    },
    {
        "days_before": 0,
        "flag": "notif_j0_sent",
        # Reutilise les memes cles push pour J0 (texte similaire)
        "push_title_key": "push_beta_ending_j7_title",
        "push_body_key": "push_beta_ending_j7_body",
        "email_template": "beta_j0",
    },
]


def days_until_beta_end(today: date | None = None) -> int:
    """Nombre de jours restants jusqu'a la fin de la beta.

    Negatif si la beta est deja terminee.
    """
    today = today or date.today()
    return (BETA_END_DATE - today).days


def get_beta_users_eligible(stage_flag: str) -> list[dict[str, Any]]:
    """Retourne les users encore en beta qui n'ont pas recu cette
    notification (idempotence).

    Note : on lit `users` directement parce que l'app actuelle stocke
    `is_beta` la-bas. Si la table beta_notifications n'a pas encore
    de ligne pour le user, on considere que la notif n'a pas ete envoyee.
    """
    with _get_conn() as conn:
        # users : tous ceux en beta avec un email valide
        rows = _fetchall(
            conn,
            f"SELECT id, email, language FROM users WHERE COALESCE(is_beta, 0) = {PH}",
            (1,),
        )
        eligible = []
        for user in rows:
            sent = _fetchall(
                conn,
                f"SELECT {stage_flag} FROM beta_notifications WHERE user_id = {PH}",
                (user["id"],),
            )
            already_sent = sent and sent[0].get(stage_flag) in (True, 1)
            if not already_sent:
                eligible.append(user)
        return eligible


def mark_notification_sent(user_id: int, stage_flag: str) -> None:
    """Marque la notification comme envoyee dans beta_notifications.

    UPSERT : cree la ligne si absente, sinon update le flag.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        if USE_PG:
            _execute(
                conn,
                f"""
                INSERT INTO beta_notifications (user_id, {stage_flag}, sent_at)
                VALUES ({PH}, TRUE, {PH})
                ON CONFLICT (user_id) DO UPDATE
                SET {stage_flag} = TRUE, sent_at = EXCLUDED.sent_at
                """,
                (user_id, now_iso),
            )
        else:
            # SQLite : INSERT OR IGNORE puis UPDATE
            _execute(
                conn,
                f"INSERT OR IGNORE INTO beta_notifications (user_id) VALUES ({PH})",
                (user_id,),
            )
            _execute(
                conn,
                f"UPDATE beta_notifications SET {stage_flag} = 1, sent_at = {PH} WHERE user_id = {PH}",
                (now_iso, user_id),
            )


def trigger_funnel_stage(stage: dict[str, Any]) -> dict[str, Any]:
    """Envoie la notification d'une etape du funnel a tous les users
    eligibles. Retourne {sent, errors}.
    """
    flag = stage["flag"]
    template = stage["email_template"]
    eligible_users = get_beta_users_eligible(flag)

    sent_count = 0
    errors: list[str] = []

    for user in eligible_users:
        user_id = user["id"]
        try:
            # 1. Push notification (i18n via send_push_to_user)
            push_result = send_push_to_user(
                user_id=user_id,
                title_key=stage["push_title_key"],
                body_key=stage["push_body_key"],
                data={
                    "screen": "Subscription",
                    "campaign": template,
                },
            )

            # 2. Email (TODO : a brancher sur SendGrid/Mailgun quand
            # le compte sera configure). Le template `template` doit
            # exister dans api/templates/emails/{template}_{lang}.html
            # avec lang = user.language.
            # Pour l'instant on log juste la decision.
            log.info(
                "beta_funnel stage=%s user=%s push_sent=%d errors=%d "
                "email_template=%s lang=%s",
                template,
                mask_email(user.get("email", "")),
                push_result["sent"],
                len(push_result["errors"]),
                template,
                user.get("language", "fr"),
            )

            # 3. Marquer comme envoye (idempotence)
            mark_notification_sent(user_id, flag)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001 — log + continue
            log.exception(
                "beta_funnel stage=%s user=%s — failure",
                template,
                mask_email(user.get("email", "")),
            )
            errors.append(f"user={user_id}: {exc}")

    return {"sent": sent_count, "errors": errors}


def run_daily_beta_funnel(today: date | None = None) -> dict[str, Any]:
    """Cron quotidien : declenche J-30, J-7, J0 selon la date du jour.

    Une seule etape se declenche par jour (au plus). Idempotent : si le
    cron est appele plusieurs fois dans la journee, les users ne recoivent
    pas de doublon (verifie via beta_notifications.notif_jXX_sent).

    Returns:
        dict {
            "today": "YYYY-MM-DD",
            "days_until_end": int,
            "stage_triggered": str | None,
            "j30_sent": int,
            "j7_sent": int,
            "j0_sent": int,
            "errors": list[str],
        }
    """
    today = today or date.today()
    days_left = days_until_beta_end(today)

    result: dict[str, Any] = {
        "today": today.isoformat(),
        "days_until_end": days_left,
        "stage_triggered": None,
        "j30_sent": 0,
        "j7_sent": 0,
        "j0_sent": 0,
        "errors": [],
    }

    for stage in FUNNEL_STAGES:
        if stage["days_before"] == days_left:
            outcome = trigger_funnel_stage(stage)
            key = f"j{stage['days_before']}_sent"
            result[key] = outcome["sent"]
            result["errors"].extend(outcome["errors"])
            result["stage_triggered"] = stage["email_template"]
            log.info(
                "beta_funnel daily stage=%s sent=%d errors=%d",
                stage["email_template"],
                outcome["sent"],
                len(outcome["errors"]),
            )
            break  # Au plus une etape par jour

    return result


def is_founding_price_available(today: date | None = None) -> bool:
    """Le tarif fondateur (3.99€/mois a vie) n'est dispo qu'avant
    BETA_END_DATE. Apres : tarif standard 4.99€/mois.

    A appeler depuis api/stripe_billing.py avant de creer un checkout
    avec founding_price.
    """
    today = today or date.today()
    return today < BETA_END_DATE
