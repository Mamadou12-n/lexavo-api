"""
api/push.py — Envoi de notifications push Expo avec i18n.

Module léger pour envoyer des push notifications via l'API Expo
(https://exp.host/--/api/v2/push/send) en respectant la langue
de chaque utilisateur (FR/NL/EN/DE).

Architecture :
- Le client mobile (Expo) enregistre son token via /push/register
- Le token est stocke dans push_tokens.token avec user_id
- Quand on declenche un push, on charge l'utilisateur pour recuperer
  son `language` puis on traduit title + body via api.i18n.t()
- Les push sont envoyes par batch (API Expo accepte 100 messages max
  par requete)

Pas de dependance externe : utilise httpx (deja dans requirements.txt).

Usage typique :

    from api.push import send_push_to_user

    send_push_to_user(
        user_id=42,
        title_key="push_new_answer_title",
        body_key="push_new_answer_body",
        data={"screen": "AskScreen"},
    )

Toutes les cles utilisees ici DOIVENT etre definies dans api/i18n.py
(_MESSAGES) en 4 langues.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from api.database import get_push_tokens_for_user, get_user_by_id
from api.i18n import t as _t

log = logging.getLogger("api.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_PUSH_TIMEOUT = 10.0  # seconds


def send_push_to_user(
    user_id: int,
    title_key: str,
    body_key: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Envoie une push notification a tous les tokens d'un utilisateur.

    La langue est lue depuis user.language (FR/NL/EN/DE). Si le user
    n'existe pas ou n'a aucun push token, retourne un dict avec status
    et raison sans lever d'exception (push best-effort).

    Args:
        user_id      : id de l'utilisateur destinataire
        title_key    : cle i18n pour le titre (ex: "push_new_answer_title")
        body_key     : cle i18n pour le body (ex: "push_new_answer_body")
        data         : payload custom (ex: {"screen": "AskScreen"})

    Returns:
        dict avec keys :
            - sent: int (nombre de tokens contactes)
            - skipped: int (tokens invalides / user introuvable)
            - errors: list[str] (erreurs Expo eventuelles)
    """
    user = get_user_by_id(user_id)
    if not user:
        log.warning("send_push_to_user user_id=%s — user not found", user_id)
        return {"sent": 0, "skipped": 0, "errors": ["user_not_found"]}

    user_lang = user.get("language") or "fr"
    title = _t(title_key, user_lang)
    body = _t(body_key, user_lang)

    tokens = get_push_tokens_for_user(user_id)
    if not tokens:
        log.info("send_push_to_user user_id=%s — no push tokens registered", user_id)
        return {"sent": 0, "skipped": 0, "errors": []}

    messages = [
        {
            "to": row["token"],
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
        }
        for row in tokens
        if row.get("token")
    ]

    if not messages:
        return {"sent": 0, "skipped": len(tokens), "errors": []}

    try:
        with httpx.Client(timeout=EXPO_PUSH_TIMEOUT) as client:
            response = client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Accept-encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        log.exception("send_push_to_user user_id=%s — Expo HTTP error", user_id)
        return {"sent": 0, "skipped": len(messages), "errors": [str(exc)]}

    # Expo retourne {"data": [{"status": "ok"}, {"status": "error", ...}]}
    results = payload.get("data", [])
    sent = sum(1 for r in results if r.get("status") == "ok")
    errors = [r.get("message", "") for r in results if r.get("status") != "ok"]

    log.info(
        "send_push_to_user user_id=%s lang=%s sent=%d errors=%d",
        user_id, user_lang, sent, len(errors),
    )

    return {"sent": sent, "skipped": len(messages) - sent, "errors": errors}


def send_push_to_users(
    user_ids: list[int],
    title_key: str,
    body_key: str,
    data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Envoie un push a plusieurs utilisateurs (batch).

    Chaque utilisateur recoit le push dans SA langue (lookup individuel).
    Pour des campagnes massives (ex: J-30 fin beta), prefer un cron qui
    appelle cette fonction par chunks de 100 user_ids.

    Returns:
        dict {sent_total: int, skipped_total: int, error_count: int}
    """
    sent_total = 0
    skipped_total = 0
    error_count = 0

    for uid in user_ids:
        result = send_push_to_user(uid, title_key, body_key, data)
        sent_total += result["sent"]
        skipped_total += result["skipped"]
        error_count += len(result["errors"])

    return {
        "sent_total": sent_total,
        "skipped_total": skipped_total,
        "error_count": error_count,
    }
