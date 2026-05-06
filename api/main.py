"""
FastAPI — App Droit Belgique (Lexavo)

Usage :
  uvicorn api.main:app --reload --port 8000
  python -m api.main
"""

import os
import logging
from pathlib import Path
from typing import Optional

# Charger .env avant tout (ANTHROPIC_API_KEY, JWT_SECRET, STRIPE...)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True, encoding="utf-8-sig")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import (
    IndexStats,
    LawyerResponse, LawyerListResponse,
)


def _setup_json_logging():
    try:
        from pythonjsonlogger import jsonlogger
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    except ImportError:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


_setup_json_logging()
log = logging.getLogger("api")

# ─── Sentry (observabilité erreurs + performance) ─────────────────────────────
try:
    import sentry_sdk
    _sentry_dsn = os.getenv("SENTRY_DSN")
    if _sentry_dsn:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_RATE", "0.05")),
            environment=os.getenv("SENTRY_ENV", "production" if os.getenv("DATABASE_URL") else "development"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "2.1.0"),
            send_default_pii=False,  # RGPD — jamais de PII dans Sentry
        )
        log.info("Sentry initialisé (env=%s)", os.getenv("SENTRY_ENV", "production"))
    else:
        log.info("SENTRY_DSN non défini — observabilité désactivée")
except ImportError:
    log.info("sentry-sdk non installé — pip install sentry-sdk[fastapi]")
except Exception as _sentry_err:
    log.warning("Sentry init échoué (non bloquant) : %s", _sentry_err)

try:
    from api.security import install_pii_filter
    install_pii_filter()
except Exception:
    pass

# ─── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─── App FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Lexavo — API Juridique Belge",
    description=(
        "API RAG spécialisée droit belge — 17 sources officielles. "
        "HUDOC (CEDH), EUR-Lex (CJUE), Juridat (Cass.), Moniteur belge, "
        "Cour constitutionnelle, Conseil d'État, CCE (étrangers), CNT, JUSTEL, "
        "APD (RGPD), GalliLex (FWB), FSMA (finance), WalLex (Wallonie), "
        "Cour des comptes, Chambre des représentants, "
        "Codex Vlaanderen (Flandre), Bruxelles (ordonnances RBC). "
        "Toutes les données sont 100% réelles."
    ),
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Origines autorisées — strict whitelist, jamais de "*", jamais de regex permissive.
_CORS_ORIGINS_ENV = os.getenv("LEXAVO_ALLOWED_ORIGINS", "")
if _CORS_ORIGINS_ENV:
    _raw_origins = [o.strip() for o in _CORS_ORIGINS_ENV.split(",") if o.strip()]
    _ALLOWED_ORIGINS: list[str] = [o for o in _raw_origins if o != "*"]
    if os.getenv("DATABASE_URL"):
        _ALLOWED_ORIGINS = [
            o for o in _ALLOWED_ORIGINS
            if o.startswith("https://") or o.startswith("exp://") or o.startswith("lexavo://")
        ]
else:
    if os.getenv("DATABASE_URL"):
        log.warning("PRODUCTION sans LEXAVO_ALLOWED_ORIGINS — CORS restreint a lexavo.be")
        _ALLOWED_ORIGINS = [
            "https://lexavo.be",
            "https://www.lexavo.be",
            "https://app.lexavo.be",
            "exp://exp.host",
            "lexavo://",
        ]
    else:
        _ALLOWED_ORIGINS = [
            "http://localhost:8081",
            "http://localhost:19000",
            "http://localhost:19006",
            "http://localhost:3000",
            "exp://localhost:8081",
            "exp://127.0.0.1:8081",
        ]

assert "*" not in _ALLOWED_ORIGINS, "CORS wildcard '*' interdit (allow_credentials=True)"

from api.security import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Masque les erreurs internes — ne jamais exposer de stack trace en prod."""
    log.error("Erreur non gérée sur %s %s : %s", request.method, request.url.path, exc, exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Erreur interne. Veuillez réessayer."})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log chaque requête : endpoint, user_id, duration_ms, status_code."""
    import time
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    user_id = None
    try:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            from api.auth import decode_token
            payload = decode_token(auth[7:])
            user_id = payload.get("sub")
    except Exception:
        pass
    log.info(
        "request",
        extra={
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
        },
    )
    return response


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    missing = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.getenv("LEXAVO_JWT_SECRET"):
        log.warning("LEXAVO_JWT_SECRET non defini — cle ephemere generee (tokens ne survivront pas au redemarrage)")
    for key in missing:
        log.warning(f"Variable d'environnement manquante : {key} — /ask ne fonctionnera pas")

    from api.database import init_db
    from api.lawyers import seed_demo_lawyers
    init_db()
    seeded = seed_demo_lawyers()
    if seeded:
        log.info(f"Base de données initialisée. {seeded} avocats de démo ajoutés.")

    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_command.upgrade(alembic_cfg, "head")
        log.info("Alembic migrations appliquées")
    except Exception as e:
        log.warning(f"Alembic skip: {e}")

    try:
        from rag.retriever import get_model
        log.info("Préchargement du modèle SentenceTransformer...")
        get_model()
        log.info("Modèle embedding prêt.")
    except Exception as exc:
        log.warning(f"Préchargement modèle échoué (non bloquant) : {exc}")


# ─── Auth dependency (local shortcut) ─────────────────────────────────────────
from api.auth import get_current_user as _get_current_user


# ─── Routers ──────────────────────────────────────────────────────────────────
from api.routers.rag import router as rag_router
from api.routers.auth import router as auth_router
from api.routers.conversations import router as conversations_router
from api.routers.billing import router as billing_router
from api.routers.shield import router as shield_router
from api.routers.decode import router as decode_router
from api.routers.calculators import router as calculators_router
from api.routers.features import router as features_router
from api.routers.student import router as student_router
from api.routers.beta_funnel import router as beta_funnel_router

app.include_router(rag_router)
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(billing_router)
app.include_router(shield_router)
app.include_router(decode_router)
app.include_router(calculators_router)
app.include_router(features_router)
app.include_router(student_router)
app.include_router(beta_funnel_router)

# SEO router (existant avant le split)
from fastapi.templating import Jinja2Templates  # noqa: E402
from api.seo import router as seo_router
app.include_router(seo_router, tags=["SEO"])


# ─── Endpoints globaux ────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Vérifie que l'API et l'index sont opérationnels."""
    from rag.indexer_qdrant import get_index_stats
    index = get_index_stats()
    return {
        "status": "ok" if index["status"] == "ok" else "degraded",
        "api_version": "2.1.0",
        "index": index,
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


@app.get("/stats", response_model=IndexStats)
def stats():
    """Retourne les statistiques de l'index vectoriel."""
    from rag.indexer_qdrant import get_index_stats
    data = get_index_stats()
    return IndexStats(**data)


@app.post("/admin/backup")
def admin_backup(request: Request, current_user: dict = Depends(_get_current_user)):
    """Cree un backup SQLite. Reserve aux admins, accessible UNIQUEMENT via outils CLI."""
    from api.security import require_cli_user_agent, admin_audit, mask_ip
    if current_user.get("role") != "admin":
        admin_audit(current_user["id"], "admin_backup_denied_role", request,
                    f"role={current_user.get('role')}")
        raise HTTPException(403, "Acces reserve a l'administrateur.")
    require_cli_user_agent(request)
    from api.database import backup_database
    try:
        path = backup_database()
    except Exception as e:
        admin_audit(current_user["id"], "admin_backup_failed", request, str(e)[:200])
        raise
    admin_audit(current_user["id"], "admin_backup_ok", request, f"path={path}")
    log.info("admin_backup user_id=%s ip=%s", current_user["id"],
             mask_ip(request.client.host if request.client else ""))
    return {"status": "ok", "backup_path": path}


@app.get("/lawyers", response_model=LawyerListResponse)
def lawyers_list(
    city: Optional[str] = Query(default=None, description="Filtrer par ville"),
    specialty: Optional[str] = Query(default=None, description="Filtrer par spécialité"),
    language: Optional[str] = Query(default=None, description="Filtrer par langue"),
):
    """Liste des avocats avec filtres optionnels."""
    from api.lawyers import list_lawyers
    results = list_lawyers(city=city, specialty=specialty, language=language)
    return LawyerListResponse(
        lawyers=[LawyerResponse(**l) for l in results],
        total=len(results),
    )


@app.get("/lawyers/{lawyer_id}", response_model=LawyerResponse)
def lawyer_detail(lawyer_id: int):
    """Profil d'un avocat."""
    from api.lawyers import get_lawyer
    result = get_lawyer(lawyer_id)
    return LawyerResponse(**result)


# ─── Démarrage direct ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
