"""Router Auth — /auth/*, /account."""

import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from typing import Annotated

from api.models import (
    RegisterRequest, LoginRequest, UserResponse, AuthResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from api.auth import get_current_user as _get_current_user
from api.i18n import get_lang
from api.routers.deps import limiter

log = logging.getLogger("api.auth")

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=AuthResponse)
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, lang: str = Depends(get_lang)):
    """Inscription d'un nouvel utilisateur. Erreurs i18n via Accept-Language."""
    from api.auth import register_user
    result = register_user(
        email=body.email,
        password=body.password,
        name=body.name,
        language=body.language,
        lang=lang,
    )
    return AuthResponse(
        user=UserResponse(**result["user"]),
        token=result["token"],
        refresh_token=result.get("refresh_token"),
    )


@router.post("/auth/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, lang: str = Depends(get_lang)):
    """Connexion — retourne un JWT + refresh token. Account lockout 5 fails / 15min.

    Erreurs i18n via Accept-Language (FR/NL/EN/DE).
    """
    from api.auth import login_user
    from api.security import (
        check_account_locked, record_failed_login, reset_failed_logins,
        mask_email, mask_ip,
    )
    ip = request.client.host if request.client else ""
    check_account_locked(body.email)
    try:
        result = login_user(email=body.email, password=body.password, lang=lang)
    except HTTPException as e:
        if e.status_code == 401:
            record_failed_login(body.email, ip)
            log.warning("login_failed email=%s ip=%s", mask_email(body.email), mask_ip(ip))
        raise
    reset_failed_logins(body.email)
    return AuthResponse(
        user=UserResponse(**result["user"]),
        token=result["token"],
        refresh_token=result.get("refresh_token"),
    )


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: Annotated[dict, Depends(_get_current_user)]):
    """Profil de l'utilisateur connecté."""
    return UserResponse(**current_user)


@router.post("/auth/refresh")
def refresh_token_endpoint(request: Request, body: dict):
    """Échange un refresh token contre un nouveau access token + nouveau refresh token."""
    from api.database import (
        get_refresh_token, delete_refresh_token, save_refresh_token,
        get_user_by_id, delete_user_refresh_tokens,
    )
    from api.auth import create_token, create_refresh_token, REFRESH_TOKEN_EXPIRY_DAYS

    rt = body.get("refresh_token", "")
    if not rt:
        raise HTTPException(status_code=400, detail="refresh_token requis.")

    stored = get_refresh_token(rt)
    if not stored:
        hint = request.headers.get("X-Lexavo-Hint-User", "")
        if hint.isdigit():
            delete_user_refresh_tokens(int(hint))
            log.warning("refresh_token_reuse_suspected user_id=%s — all tokens revoked", hint)
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré.")

    expires_str = str(stored["expires_at"])[:19]
    try:
        expires = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            delete_refresh_token(rt)
            raise HTTPException(status_code=401, detail="Refresh token expiré.")
    except ValueError:
        pass

    user = get_user_by_id(stored["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    delete_refresh_token(rt)
    new_access = create_token(user["id"], user["email"])
    new_refresh = create_refresh_token(user["id"])
    new_expires = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    save_refresh_token(user["id"], new_refresh, new_expires)

    return {"token": new_access, "refresh_token": new_refresh, "user": user}


@router.post("/auth/forgot-password")
@limiter.limit("3/minute")
def forgot_password_endpoint(request: Request, body: ForgotPasswordRequest):
    """Génère un token de reset (valable 1h)."""
    from api.auth import forgot_password
    token = forgot_password(body.email)
    log.info("Password reset link generated for email=%s", body.email)
    _ = token
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


@router.post("/auth/reset-password")
@limiter.limit("5/minute")
def reset_password_endpoint(request: Request, body: ResetPasswordRequest, lang: str = Depends(get_lang)):
    """Valide le token et met à jour le mot de passe. Erreurs i18n."""
    from api.auth import reset_password
    reset_password(body.token, body.new_password, lang=lang)
    return {"message": "Mot de passe mis à jour avec succès. Vous pouvez vous reconnecter."}


# ─── RGPD ─────────────────────────────────────────────────────────────────────

@router.delete("/account", status_code=204)
def delete_account(current_user: Annotated[dict, Depends(_get_current_user)]):
    """RGPD art.17 — Suppression du compte utilisateur en cascade."""
    from api.database import delete_user_cascade
    delete_user_cascade(current_user["id"])
    return Response(status_code=204)


@router.get("/account/export")
def export_account_data(current_user: Annotated[dict, Depends(_get_current_user)]):
    """RGPD art.20 — Export complet des données utilisateur (JSON portable)."""
    from api.database import export_user_data
    return export_user_data(current_user["id"])
