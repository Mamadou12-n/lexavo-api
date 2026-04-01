#!/usr/bin/env python3
"""
Lexavo — Envoi automatique des emails de fin de beta.
100% autonome. Execute par GitHub Actions chaque jour a 8h UTC.

Milestones : J-30, J-15, J-7, Jour J
Protections : anti-doublons, retry x3, auto-correction des echecs, dry-run.

Usage :
  python scripts/send_beta_emails.py                     # normal
  python scripts/send_beta_emails.py --dry-run            # simulation
  python scripts/send_beta_emails.py --force-milestone j30  # forcer un milestone
"""

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
DATABASE_URL = os.getenv("DATABASE_URL", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
BETA_END_DATE = os.getenv("LEXAVO_BETA_END", "2026-10-01")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "Lexavo <onboarding@resend.dev>")

RESEND_API_URL = "https://api.resend.com/emails"
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # secondes (exponentiel)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

MILESTONES = {30: "j30", 15: "j15", 7: "j7", 0: "j0"}

TEMPLATE_DIR = Path(__file__).parent.parent / "api" / "templates"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("beta_emails")


# ─── Validation pre-envoi ────────────────────────────────────────────────────

def validate_config():
    """Verifie que toute la config est en place. Exit 1 si critique."""
    errors = []
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
            log.error(f"ERREUR CONFIG : {e}")
        sys.exit(1)

    log.info(f"Config OK — Beta end: {BETA_END_DATE}, From: {FROM_EMAIL}")


def get_days_remaining() -> int:
    """Calcule les jours restants avant la fin de la beta."""
    end = datetime.strptime(BETA_END_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (end - now).days


def load_template(milestone: str) -> str:
    """Charge le template HTML pour un milestone. Exit si introuvable."""
    path = TEMPLATE_DIR / f"beta_{milestone}.html"
    if not path.exists():
        log.error(f"Template introuvable : {path}")
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if len(content.strip()) < 50:
        log.error(f"Template vide ou trop court : {path}")
        sys.exit(1)
    return content


def personalize(template: str, name: str, email: str) -> str:
    """Remplace les placeholders dans le template."""
    return (
        template
        .replace("{{NAME}}", name or "")
        .replace("{{EMAIL}}", email or "")
        .replace("{{BETA_END}}", BETA_END_DATE)
    )


# ─── Base de donnees ─────────────────────────────────────────────────────────

def get_db():
    """Connexion PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def ensure_table(conn):
    """Cree la table beta_notifications si elle n'existe pas."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS beta_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                milestone TEXT NOT NULL,
                email_to TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'sent',
                error_msg TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, milestone)
            );
        """)
        conn.commit()


def get_users_to_notify(conn, milestone: str) -> list:
    """Recupere les users qui n'ont PAS encore recu ce milestone (ou qui ont failed)."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT u.id, u.email, u.name
            FROM users u
            WHERE u.id NOT IN (
                SELECT bn.user_id FROM beta_notifications bn
                WHERE bn.milestone = %s AND bn.status = 'sent'
            )
            ORDER BY u.id;
        """, (milestone,))
        return cur.fetchall()


def get_failed_notifications(conn) -> list:
    """Recupere les notifications echouees pour auto-correction."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT bn.id, bn.user_id, bn.milestone, bn.email_to, u.name
            FROM beta_notifications bn
            JOIN users u ON u.id = bn.user_id
            WHERE bn.status = 'failed'
            ORDER BY bn.sent_at;
        """)
        return cur.fetchall()


def mark_sent(conn, user_id: int, milestone: str, email: str):
    """Marque un envoi reussi (INSERT ou UPDATE si failed avant)."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO beta_notifications (user_id, milestone, email_to, status)
            VALUES (%s, %s, %s, 'sent')
            ON CONFLICT (user_id, milestone)
            DO UPDATE SET status = 'sent', error_msg = NULL, sent_at = CURRENT_TIMESTAMP;
        """, (user_id, milestone, email))
        conn.commit()


def mark_failed(conn, user_id: int, milestone: str, email: str, error: str):
    """Marque un echec d'envoi."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO beta_notifications (user_id, milestone, email_to, status, error_msg)
            VALUES (%s, %s, %s, 'failed', %s)
            ON CONFLICT (user_id, milestone)
            DO UPDATE SET status = 'failed', error_msg = %s, sent_at = CURRENT_TIMESTAMP;
        """, (user_id, milestone, email, error, error))
        conn.commit()


# ─── Envoi email via Resend ──────────────────────────────────────────────────

SUBJECT_MAP = {
    "j30": "Lexavo evolue bientot — decouvrez ce qui vous attend",
    "j15": "Offre Founding Member — prix reduit a vie",
    "j7":  "Plus que 7 jours pour profiter du tarif Founding Member",
    "j0":  "Votre acces Lexavo change aujourd'hui",
}


def send_email(to: str, subject: str, html: str) -> bool:
    """Envoie un email via Resend API avec retry x3."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
                timeout=15,
            )
            if resp.status_code in (200, 201):
                return True
            error = resp.text
            log.warning(f"Resend {resp.status_code} pour {to} (tentative {attempt+1}/{MAX_RETRIES}): {error}")
        except requests.RequestException as e:
            error = str(e)
            log.warning(f"Erreur reseau pour {to} (tentative {attempt+1}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            log.info(f"Retry dans {delay}s...")
            time.sleep(delay)

    return False


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Envoi automatique emails fin de beta Lexavo")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans envoi")
    parser.add_argument("--force-milestone", type=str, default="", help="Forcer un milestone (j30, j15, j7, j0)")
    args = parser.parse_args()

    validate_config()

    days = get_days_remaining()
    log.info(f"Jours restants avant fin beta : {days}")

    # Determiner le milestone
    if args.force_milestone:
        milestone = args.force_milestone
        if milestone not in ("j30", "j15", "j7", "j0"):
            log.error(f"Milestone invalide : {milestone}. Valeurs : j30, j15, j7, j0")
            sys.exit(1)
        log.info(f"MODE FORCE : milestone={milestone}")
    elif days in MILESTONES:
        milestone = MILESTONES[days]
        log.info(f"Milestone detecte : {milestone} (J-{days})")
    else:
        log.info(f"Aucun milestone aujourd'hui (J-{days}). Rien a envoyer.")
        # Quand meme verifier les failed pour auto-correction
        milestone = None

    # Si aucun milestone et pas de force → rien a faire, pas besoin de DB
    if milestone is None and not args.force_milestone:
        stats = {"sent": 0, "failed": 0, "skipped": 0, "corrected": 0}
        _print_report(stats, days)
        return

    conn = get_db()
    try:
        ensure_table(conn)

        stats = {"sent": 0, "failed": 0, "skipped": 0, "corrected": 0}

        # 1. Auto-correction des echecs precedents
        try:
            failed = get_failed_notifications(conn)
        except Exception as e:
            log.warning(f"Impossible de verifier les echecs precedents : {e}")
            failed = []

        if failed:
            log.info(f"Auto-correction : {len(failed)} envoi(s) echoue(s) a retenter")
            for f in failed:
                ms = f["milestone"]
                template = load_template(ms)
                html = personalize(template, f["name"], f["email_to"])
                subject = SUBJECT_MAP.get(ms, "Lexavo — Notification")

                if args.dry_run:
                    log.info(f"[DRY-RUN] Corrigerait {f['email_to']} ({ms})")
                    stats["corrected"] += 1
                    continue

                if send_email(f["email_to"], subject, html):
                    mark_sent(conn, f["user_id"], ms, f["email_to"])
                    log.info(f"CORRIGE : {f['email_to']} ({ms})")
                    stats["corrected"] += 1
                else:
                    log.warning(f"ECHEC CORRECTION : {f['email_to']} ({ms})")
                    stats["failed"] += 1

        # 2. Envoi du milestone du jour
        if milestone is None:
            _print_report(stats, days)
            return

        template = load_template(milestone)
        subject = SUBJECT_MAP.get(milestone, "Lexavo — Notification")
        users = get_users_to_notify(conn, milestone)

        if not users:
            log.info(f"Aucun utilisateur a notifier pour {milestone}")
            _print_report(stats, days)
            return

        log.info(f"{len(users)} utilisateur(s) a notifier pour {milestone}")

        for user in users:
            email = user["email"]

            # Validation email
            if not EMAIL_REGEX.match(email):
                log.warning(f"Email invalide, skip : {email}")
                stats["skipped"] += 1
                continue

            html = personalize(template, user["name"], email)

            if args.dry_run:
                log.info(f"[DRY-RUN] Enverrait a {email} ({user['name']}) — {milestone}")
                stats["sent"] += 1
                continue

            if send_email(email, subject, html):
                mark_sent(conn, user["id"], milestone, email)
                log.info(f"ENVOYE : {email} ({milestone})")
                stats["sent"] += 1
            else:
                mark_failed(conn, user["id"], milestone, email, "3 retries failed")
                log.warning(f"ECHEC : {email} ({milestone}) — sera retente demain")
                stats["failed"] += 1

        _print_report(stats, days)

    finally:
        conn.close()


def _print_report(stats: dict, days: int):
    """Affiche le rapport final."""
    report = {
        "date": datetime.now(timezone.utc).isoformat(),
        "days_remaining": days,
        "beta_end": BETA_END_DATE,
        "emails_sent": stats["sent"],
        "emails_failed": stats["failed"],
        "emails_skipped": stats["skipped"],
        "emails_corrected": stats["corrected"],
    }
    log.info("=" * 60)
    log.info("RAPPORT FINAL")
    log.info(f"  Envoyes   : {stats['sent']}")
    log.info(f"  Echoues   : {stats['failed']}")
    log.info(f"  Ignores   : {stats['skipped']}")
    log.info(f"  Corriges  : {stats['corrected']}")
    log.info("=" * 60)
    # JSON pour parsing automatique dans GitHub Actions
    print(f"::set-output name=report::{json.dumps(report)}")


if __name__ == "__main__":
    main()
