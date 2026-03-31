"""
JWT authentication for Lexavo FastAPI.
Uses hashlib (stdlib) for password hashing and PyJWT for tokens.
"""

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.database import create_user, get_user_by_email, get_user_by_id

# ─── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("LEXAVO_JWT_SECRET", "")
if not SECRET_KEY:
    import warnings
    warnings.warn(
        "LEXAVO_JWT_SECRET non defini — utilisation d'une cle ephemere. "
        "Les tokens ne survivront pas au redemarrage.",
        stacklevel=1,
    )
    SECRET_KEY = secrets.token_hex(32)  # cle ephemere, securisee mais non persistante

ALGORITHM = "HS256"
TOKEN_EXPIRY_DAYS = 7

# FastAPI security scheme
security = HTTPBearer()


# ─── Password hashing ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt (industry standard, GPU-resistant).
    Returns the bcrypt hash string directly.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.
    Also supports legacy SHA-256 salt$hash format for migration.
    """
    if password_hash.startswith("$2b$") or password_hash.startswith("$2a$"):
        # bcrypt format
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    # Legacy SHA-256 format: salt$hash — still verify but flag for upgrade
    if "$" not in password_hash:
        return False
    salt, stored_hash = password_hash.split("$", 1)
    computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, stored_hash)


# ─── JWT tokens ──────────────────────────────────────────────────────────────

def create_token(user_id: int, email: str) -> str:
    """Create a JWT token with 7-day expiry."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises on invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré. Veuillez vous reconnecter.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide.",
        )


# ─── FastAPI dependency ─────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency: extract and validate user from Authorization header.
    Returns user dict (id, email, name, language, created_at).
    """
    payload = decode_token(credentials.credentials)

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformé.",
        )
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )
    return user


# ─── Auth logic (used by endpoints) ─────────────────────────────────────────

def register_user(email: str, password: str, name: str, language: str = "fr") -> dict:
    """Register a new user. Returns dict with user info + token.
    Raises HTTPException on duplicate email or validation error.
    """
    # Validate
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adresse email invalide.",
        )
    if not password or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 6 caractères.",
        )
    if not name or len(name.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom doit contenir au moins 2 caractères.",
        )
    if language not in ("fr", "nl", "en"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Langue invalide. Choisissez parmi : fr, nl, en.",
        )

    # Check duplicate
    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email.",
        )

    # Create
    pw_hash = hash_password(password)
    user = create_user(email, pw_hash, name.strip(), language)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du compte.",
        )

    token = create_token(user["id"], user["email"])
    return {"user": user, "token": token}


def login_user(email: str, password: str) -> dict:
    """Authenticate a user. Returns dict with user info + token.
    Raises HTTPException on invalid credentials.
    """
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    if not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    # Return user without password_hash
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    token = create_token(safe_user["id"], safe_user["email"])
    return {"user": safe_user, "token": token}
