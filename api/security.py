"""
Security hardening for Lexavo backend.

Provides:
  - Security headers middleware (HSTS, CSP, X-Frame, etc.)
  - Account lockout (5 fails / 15min -> block 30min)
  - PII masking for logs (email, IP, no password/token/JWT)
  - File upload MIME validation (real magic bytes, not headers)
  - Webhook idempotency helpers
  - Admin audit logging
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

log = logging.getLogger("security")

# ─── 1. Security headers middleware ────────────────────────────────────────

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(self)",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        # Strip server fingerprint
        response.headers["Server"] = "Lexavo"
        return response


# ─── 2. Account lockout ─────────────────────────────────────────────────────

LOCKOUT_MAX_FAILS = 5
LOCKOUT_WINDOW_MIN = 15
LOCKOUT_DURATION_MIN = 30


def record_failed_login(email: str, ip: str) -> None:
    """Record a failed login attempt. Auto-cleans old entries."""
    from api.database import _get_conn, _execute, USE_PG
    PH = "%s" if USE_PG else "?"
    conn = _get_conn()
    try:
        _execute(
            conn,
            f"INSERT INTO failed_logins (email, ip, attempted_at) VALUES ({PH}, {PH}, CURRENT_TIMESTAMP)",
            (email.lower().strip(), ip or ""),
        )
        # cleanup > 24h
        _execute(
            conn,
            "DELETE FROM failed_logins WHERE attempted_at < "
            + ("(NOW() - INTERVAL '1 day')" if USE_PG else "datetime('now', '-1 day')"),
        )
        conn.commit()
    finally:
        conn.close()


def check_account_locked(email: str) -> None:
    """Raise 429 if email has 5+ failures in last 15 minutes (lock 30 min)."""
    from api.database import _get_conn, _fetchone, USE_PG
    PH = "%s" if USE_PG else "?"
    conn = _get_conn()
    try:
        # Count fails in last LOCKOUT_DURATION_MIN minutes (block window)
        if USE_PG:
            row = _fetchone(
                conn,
                f"SELECT COUNT(*) AS n, MAX(attempted_at) AS last FROM failed_logins "
                f"WHERE email = {PH} AND attempted_at > (NOW() - INTERVAL '{LOCKOUT_DURATION_MIN} minutes')",
                (email.lower().strip(),),
            )
        else:
            row = _fetchone(
                conn,
                f"SELECT COUNT(*) AS n, MAX(attempted_at) AS last FROM failed_logins "
                f"WHERE email = {PH} AND attempted_at > datetime('now', '-{LOCKOUT_DURATION_MIN} minutes')",
                (email.lower().strip(),),
            )
        if row and row.get("n", 0) >= LOCKOUT_MAX_FAILS:
            raise HTTPException(
                status_code=429,
                detail="Compte temporairement verrouille (trop de tentatives). Reessayez dans 30 minutes.",
            )
    finally:
        conn.close()


def reset_failed_logins(email: str) -> None:
    """Clear failed attempts after a successful login."""
    from api.database import _get_conn, _execute, USE_PG
    PH = "%s" if USE_PG else "?"
    conn = _get_conn()
    try:
        _execute(conn, f"DELETE FROM failed_logins WHERE email = {PH}", (email.lower().strip(),))
        conn.commit()
    finally:
        conn.close()


# ─── 4. PII masking for logs ────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_TOKEN_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-_\.]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")
_PASSWORD_RE = re.compile(r"(?i)(password\"?\s*[:=]\s*\"?)[^\"\s,}]+")


def mask_email(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    if not local:
        return "***@" + domain
    return local[0] + "***@" + domain


def mask_ip(ip: Optional[str]) -> str:
    """Mask last octet of IPv4 (/24) or last 80 bits of IPv6."""
    if not ip:
        return ""
    if "." in ip:  # IPv4
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    if ":" in ip:  # IPv6 — keep 3 first hextets
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::/48"
    return "***"


def scrub_pii(text: str) -> str:
    """Remove emails, tokens, JWTs, passwords from a log line."""
    if not text:
        return text
    text = _JWT_RE.sub("[JWT_REDACTED]", text)
    text = _TOKEN_RE.sub(r"\1[REDACTED]", text)
    text = _PASSWORD_RE.sub(r"\1[REDACTED]", text)
    text = _EMAIL_RE.sub(lambda m: m.group(1) + "***" + m.group(2), text)
    return text


class PIIScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = scrub_pii(record.msg)
            if record.args:
                record.args = tuple(
                    scrub_pii(a) if isinstance(a, str) else a for a in record.args
                )
        except Exception:
            pass
        return True


def install_pii_filter() -> None:
    """Attach the PII scrub filter to the root logger."""
    root = logging.getLogger()
    if not any(isinstance(f, PIIScrubFilter) for f in root.filters):
        root.addFilter(PIIScrubFilter())


# ─── 6. Webhook Stripe idempotency ──────────────────────────────────────────

def webhook_event_already_processed(event_id: str) -> bool:
    """Returns True if event_id was already inserted (idempotent processing)."""
    from api.database import _get_conn, _execute, _fetchone, USE_PG
    if not event_id:
        return False
    PH = "%s" if USE_PG else "?"
    conn = _get_conn()
    try:
        row = _fetchone(
            conn,
            f"SELECT event_id FROM stripe_webhook_events WHERE event_id = {PH}",
            (event_id,),
        )
        if row:
            return True
        try:
            _execute(
                conn,
                f"INSERT INTO stripe_webhook_events (event_id, processed_at) VALUES ({PH}, CURRENT_TIMESTAMP)",
                (event_id,),
            )
            conn.commit()
        except Exception:
            # Race condition: another worker inserted first → treat as processed.
            conn.rollback()
            return True
        return False
    finally:
        conn.close()


# ─── 7. File upload MIME validation ─────────────────────────────────────────

# Magic bytes (real MIME signatures, never trust client headers/extensions)
_MAGIC_PDF = b"%PDF-"
_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_ZIP = b"PK\x03\x04"  # DOCX is a ZIP

DOCX_MAX_UNCOMPRESSED = 50 * 1024 * 1024  # 50 MB anti zip-bomb


def validate_upload_mime(content: bytes, allowed: set[str]) -> str:
    """
    Validate file by magic bytes, NOT extension/header.
    `allowed` ⊂ {"pdf", "jpeg", "png", "docx", "txt"}.
    Returns detected type. Raises HTTP 415 on mismatch, HTTP 422 on zip-bomb.
    """
    if not content or len(content) < 4:
        raise HTTPException(400, "Fichier vide ou tronque.")

    detected: Optional[str] = None
    if content.startswith(_MAGIC_PDF):
        detected = "pdf"
    elif content.startswith(_MAGIC_JPEG):
        detected = "jpeg"
    elif content.startswith(_MAGIC_PNG):
        detected = "png"
    elif content.startswith(_MAGIC_ZIP):
        # Could be DOCX or any zip. Verify it's an Office Open XML doc.
        if "docx" in allowed:
            try:
                import zipfile
                import io
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    names = zf.namelist()
                    if "[Content_Types].xml" not in names or not any(
                        n.startswith("word/") for n in names
                    ):
                        raise HTTPException(415, "Le fichier ZIP n'est pas un DOCX valide.")
                    # Anti zip-bomb : check uncompressed total size
                    total = sum(zi.file_size for zi in zf.infolist())
                    if total > DOCX_MAX_UNCOMPRESSED:
                        raise HTTPException(422, "Document compresse trop volumineux (zip-bomb suspecte).")
                    # Compression ratio sanity check
                    compressed = sum(zi.compress_size for zi in zf.infolist()) or 1
                    if total / compressed > 100:
                        raise HTTPException(422, "Ratio de compression suspect (zip-bomb).")
                    detected = "docx"
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(415, "Fichier DOCX corrompu ou invalide.")
    elif "txt" in allowed:
        # Heuristic for plain UTF-8 text
        try:
            content[:4096].decode("utf-8")
            if all(b >= 9 or b == 0 for b in content[:512]):
                detected = "txt"
        except UnicodeDecodeError:
            pass

    if detected is None or detected not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporte. Autorises : {', '.join(sorted(allowed))}.",
        )
    return detected


# ─── 8. Admin audit log ─────────────────────────────────────────────────────

def admin_audit(user_id: int, action: str, request: Optional[Request] = None,
                details: str = "") -> None:
    """Append an entry to admin_audit_log."""
    from api.database import _get_conn, _execute, USE_PG
    PH = "%s" if USE_PG else "?"
    ip = ""
    user_agent = ""
    if request is not None:
        ip = (request.client.host if request.client else "") or ""
        user_agent = request.headers.get("user-agent", "")[:500]
    conn = _get_conn()
    try:
        _execute(
            conn,
            f"INSERT INTO admin_audit_log (user_id, action, ip, user_agent, details, created_at) "
            f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, CURRENT_TIMESTAMP)",
            (user_id, action, ip, user_agent, details[:1000]),
        )
        conn.commit()
    finally:
        conn.close()


# ─── 8 bis. CLI-only User-Agent gate ────────────────────────────────────────

_CLI_UA_PATTERNS = ("curl/", "Wget/", "lexavo-cli", "python-requests/", "httpie/", "PowerShell/")


def require_cli_user_agent(request: Request) -> None:
    """Reject /admin/backup if not invoked from a CLI tool."""
    ua = request.headers.get("user-agent", "")
    if not ua or not any(p.lower() in ua.lower() for p in _CLI_UA_PATTERNS):
        raise HTTPException(403, "Endpoint reserve aux outils CLI (curl, wget, lexavo-cli).")
