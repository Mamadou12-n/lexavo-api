#!/usr/bin/env python3
"""
Lexavo — Envoi automatique des emails de fin de beta.
100% autonome. Execute par GitHub Actions chaque jour a 8h UTC.

Milestones : J-30, J-7, Jour J
Protections : anti-doublons (idempotency Resend), retry x3 backoff,
              auto-correction des echecs, dry-run, multilingue FR/NL/EN/DE.

Usage :
  python scripts/send_beta_emails.py                        # normal
  python scripts/send_beta_emails.py --dry-run              # simulation
  python scripts/send_beta_emails.py --force-milestone j30  # forcer
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests

# ─── Config ──────────────────────────────────────────────────────────────────

DATABASE_URL     = os.getenv("DATABASE_URL", "")
RESEND_API_KEY   = os.getenv("RESEND_API_KEY", "")
BETA_END_DATE    = os.getenv("LEXAVO_BETA_END", "2026-10-01")
FROM_EMAIL       = os.getenv("RESEND_FROM_EMAIL", "Lexavo <hello@lexavo.be>")
CHECKOUT_BASE    = os.getenv("LEXAVO_CHECKOUT_URL", "https://lexavo.be/checkout/basic")
UNSUBSCRIBE_BASE = os.getenv("LEXAVO_UNSUBSCRIBE_URL", "https://lexavo.be/unsubscribe")

RESEND_API_URL = "https://api.resend.com/emails"
MAX_RETRIES    = 3
RETRY_DELAYS   = [2, 4, 8]

EMAIL_REGEX     = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
SUPPORTED_LANGS = ("fr", "nl", "en", "de")
DEFAULT_LANG    = "fr"
MILESTONES      = {30: "j30", 7: "j7", 0: "j0"}
TEMPLATE_DIR    = Path(__file__).parent.parent / "api" / "templates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("beta_emails")


# ─── Sujets i18n ─────────────────────────────────────────────────────────────

SUBJECTS: dict[str, dict[str, str]] = {
    "j30": {
        "fr": "Lexavo évolue — bloquez votre tarif fondateur 3,99 €/mois",
        "nl": "Lexavo evolueert — reserveer uw oprichtersprijs € 3,99/maand",
        "en": "Lexavo is evolving — lock in your founder price €3.99/month",
        "de": "Lexavo entwickelt sich — sichern Sie sich den Gründerpreis 3,99 €/Monat",
    },
    "j7": {
        "fr": "Plus que 7 jours pour bloquer votre tarif fondateur",
        "nl": "Nog maar 7 dagen om uw oprichtersprijs vast te zetten",
        "en": "Only 7 days left to lock in your founder price",
        "de": "Nur noch 7 Tage, um Ihren Gründerpreis zu sichern",
    },
    "j0": {
        "fr": "Votre accès beta Lexavo se termine aujourd'hui",
        "nl": "Uw Lexavo-betatoegang eindigt vandaag",
        "en": "Your Lexavo beta access ends today",
        "de": "Ihr Lexavo-Beta-Zugang endet heute",
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize_lang(code: str | None) -> str:
    if not code:
        return DEFAULT_LANG
    primary = str(code).strip().lower()[:2]
    return primary if primary in SUPPORTED_LANGS else DEFAULT_LANG


def validate_config() -> None:
    errors: list[str] = []
    if not DATABASE_URL:
        errors.append("DATABASE_URL non configure")
    if not RESEND_API_KEY:
        errors.append("RESEND_API_KEY non configure")
    try:
        datetime.strptime(BETA_END_DATE, "%Y-%m-%d")
    except ValueError:
        errors.append(f"LEXAVO_BETA_END invalide : {BETA_END_DATE}")
    if errors:
        for e in errors:
            log.error("ERREUR CONFIG : %s", e)
        sys.exit(1)
    log.info("Config OK — Beta end: %s, From: %s", BETA_END_DATE, FROM_EMAIL)


def get_days_remaining() -> int:
    end = datetime.strptime(BETA_END_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (end - now).days


def load_template(milestone: str, lang: str) -> str:
    """Charge le template HTML pour un milestone + langue. Fallback FR."""
    safe_lang = normalize_lang(lang)
    path = TEMPLATE_DIR / f"beta_{milestone}_{safe_lang}.html"
    if not path.exists():
        log.warning("Template %s introuvable, fallback FR", path.name)
        path = TEMPLATE_DIR / f"beta_{milestone}_fr.html"
    if not path.exists():
        log.error("Template introuvable : %s", path)
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if len(content.strip()) < 50:
        log.error("Template vide : %s", path)
        sys.exit(1)
    return content


def personalize(template: str, name: str, email: str, user_id: int) -> str:
    checkout_url    = f"{CHECKOUT_BASE}?ref=beta-{user_id}"
    unsubscribe_url = f"{UNSUBSCRIBE_BASE}?uid={user_id}"
    return (
        template
        .replace("{{NAME}}", name or "")
        .replace("{{EMAIL}}", email or "")
        .replace("{{BETA_END}}", BETA_END_DATE)
        .replace("{{CHECKOUT_URL}}", checkout_url)
        .replace("{{UNSUBSCRIBE_URL}}", unsubscribe_url)
    )


def get_subject(milestone: str, lang: str) -> str:
    safe_lang = normalize_lang(lang)
    return SUBJECTS.get(milestone, {}).get(safe_lang, f"Lexavo — {milestone}")


# ─── Base de donnees ─────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(DATABASE_URL)


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS beta_notifications (
                id        SERIAL PRIMARY KEY,
                user_id   INTEGER NOT NULL,
                milestone TEXT    NOT NULL,
                email_to  TEXT    NOT NULL,
                status    TEXT    NOT NULL DEFAULT 'sent',
                error_msg TEXT,
                sent_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, milestone)
            );
        """)
        conn.commit()


def get_users_to_notify(conn, milestone: str) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT u.id, u.email, u.name,
                   COALESCE(u.language, 'fr') AS language
            FROM users u
            WHERE u.id NOT IN (
                SELECT bn.user_id FROM beta_notifications bn
                WHERE bn.milestone = %s AND bn.status = 'sent'
            )
            ORDER BY u.id;
        """, (milestone,))
        return cur.fetchall()


def get_failed_notifications(conn) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT bn.id, bn.user_id, bn.milestone, bn.email_to,
                   u.name, COALESCE(u.language, 'fr') AS language
            FROM beta_notifications bn
            JOIN users u ON u.id = bn.user_id
            WHERE bn.status = 'failed'
            ORDER BY bn.sent_at;
        """)
        return cur.fetchall()


def mark_sent(conn, user_id: int, milestone: str, email: str) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO beta_notifications (user_id, milestone, email_to, status)
            VALUES (%s, %s, %s, 'sent')
            ON CONFLICT (user_id, milestone)
            DO UPDATE SET status = 'sent', error_msg = NULL,
                          sent_at = CURRENT_TIMESTAMP;
        """, (user_id, milestone, email))
        conn.commit()


def mark_failed(conn, user_id: int, milestone: str, email: str, error: str) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO beta_notifications (user_id, milestone, email_to, status, error_msg)
            VALUES (%s, %s, %s, 'failed', %s)
            ON CONFLICT (user_id, milestone)
            DO UPDATE SET status = 'failed', error_msg = %s,
                          sent_at = CURRENT_TIMESTAMP;
        """, (user_id, milestone, email, error, error))
        conn.commit()


# ─── Envoi email via Resend API ───────────────────────────────────────────────

def send_email(to: str, subject: str, html: str, idempotency_key: str) -> bool:
    """Envoie via Resend API avec idempotency key et retry exponentiel.

    Idempotency key : beta-<milestone>/<user_id> — expire apres 24h,
    safe pour un cron quotidien. Le suffix -retry evite le conflit 409
    lors des auto-corrections de J-1.
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                return True
            # 409 = meme key + payload identique → Resend deduplique, OK
            if resp.status_code == 409:
                log.warning("Resend dedup (409) pour %s — compte comme envoye", to)
                return True
            # 400/422 = payload invalide → inutile de retenter
            if resp.status_code in (400, 422):
                log.error("Resend %d pour %s : %s", resp.status_code, to, resp.text[:200])
                return False
            log.warning(
                "Resend %d pour %s (tentative %d/%d)",
                resp.status_code, to, attempt + 1, MAX_RETRIES,
            )
        except requests.RequestException as exc:
            log.warning("Erreur reseau pour %s (tentative %d/%d) : %s", to, attempt + 1, MAX_RETRIES, exc)

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAYS[attempt])

    return False


# ─── Logique metier ───────────────────────────────────────────────────────────

def process_milestone(conn, milestone: str, dry_run: bool, stats: dict) -> None:
    users = get_users_to_notify(conn, milestone)
    if not users:
        log.info("Aucun utilisateur a notifier pour %s", milestone)
        return

    log.info("%d utilisateur(s) a notifier pour %s", len(users), milestone)

    for user in users:
        email = user["email"]
        if not EMAIL_REGEX.match(email or ""):
            log.warning("Email invalide, skip : %s", email)
            stats["skipped"] += 1
            continue

        lang     = normalize_lang(user.get("language"))
        html     = personalize(load_template(milestone, lang), user["name"] or "", email, user["id"])
        subject  = get_subject(milestone, lang)
        idem_key = f"beta-{milestone}/{user['id']}"

        if dry_run:
            log.info("[DRY-RUN] %s → %s (%s, lang=%s)", milestone, email, user["name"], lang)
            stats["sent"] += 1
            continue

        if send_email(email, subject, html, idem_key):
            mark_sent(conn, user["id"], milestone, email)
            log.info("ENVOYE : %s (%s, lang=%s)", email, milestone, lang)
            stats["sent"] += 1
        else:
            mark_failed(conn, user["id"], milestone, email, "3 retries failed")
            log.warning("ECHEC : %s (%s) — sera retente demain", email, milestone)
            stats["failed"] += 1


def autocorrect_failed(conn, dry_run: bool, stats: dict) -> None:
    try:
        failed = get_failed_notifications(conn)
    except Exception as exc:
        log.warning("Impossible de verifier les echecs precedents : %s", exc)
        return

    if not failed:
        return

    log.info("Auto-correction : %d envoi(s) echoue(s)", len(failed))
    for f in failed:
        ms       = f["milestone"]
        lang     = normalize_lang(f.get("language"))
        html     = personalize(load_template(ms, lang), f["name"] or "", f["email_to"], f["user_id"])
        subject  = get_subject(ms, lang)
        # Suffix -retry pour eviter conflit 409 avec la key originale
        idem_key = f"beta-{ms}/{f['user_id']}-retry"

        if dry_run:
            log.info("[DRY-RUN] Corrigerait %s (%s)", f["email_to"], ms)
            stats["corrected"] += 1
            continue

        if send_email(f["email_to"], subject, html, idem_key):
            mark_sent(conn, f["user_id"], ms, f["email_to"])
            log.info("CORRIGE : %s (%s)", f["email_to"], ms)
            stats["corrected"] += 1
        else:
            log.warning("ECHEC CORRECTION : %s (%s)", f["email_to"], ms)
            stats["failed"] += 1


def _print_report(stats: dict, days: int, milestone: str | None) -> None:
    report = {
        "date": datetime.now(timezone.utc).isoformat(),
        "days_remaining": days,
        "beta_end": BETA_END_DATE,
        "milestone": milestone,
        "emails_sent": stats["sent"],
        "emails_failed": stats["failed"],
        "emails_skipped": stats["skipped"],
        "emails_corrected": stats["corrected"],
    }
    log.info("=" * 60)
    log.info("RAPPORT FINAL  milestone=%s", milestone or "none")
    log.info("  Envoyes   : %d", stats["sent"])
    log.info("  Echoues   : %d", stats["failed"])
    log.info("  Ignores   : %d", stats["skipped"])
    log.info("  Corriges  : %d", stats["corrected"])
    log.info("=" * 60)

    gh_output = os.environ.get("GITHUB_OUTPUT", "")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"report={json.dumps(report)}\n")
    else:
        print(json.dumps(report, indent=2))

    if stats["failed"] > 0:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-milestone", type=str, default="")
    args = parser.parse_args()

    validate_config()

    days = get_days_remaining()
    log.info("Jours restants avant fin beta : %d", days)

    if args.force_milestone:
        if args.force_milestone not in ("j30", "j7", "j0"):
            log.error("Milestone invalide : %s. Valeurs : j30, j7, j0", args.force_milestone)
            sys.exit(1)
        milestone: str | None = args.force_milestone
        log.info("MODE FORCE : milestone=%s", milestone)
    elif days in MILESTONES:
        milestone = MILESTONES[days]
        log.info("Milestone detecte : %s (J-%d)", milestone, days)
    else:
        milestone = None
        log.info("Aucun milestone aujourd'hui (J-%d)", days)

    stats: dict[str, int] = {"sent": 0, "failed": 0, "skipped": 0, "corrected": 0}

    conn = get_db()
    try:
        ensure_table(conn)
        autocorrect_failed(conn, args.dry_run, stats)
        if milestone:
            process_milestone(conn, milestone, args.dry_run, stats)
    finally:
        conn.close()

    _print_report(stats, days, milestone)


if __name__ == "__main__":
    main()
