"""
FastAPI — App Droit Belgique (Lexavo)
Endpoint /ask : question juridique → réponse RAG avec sources

Usage :
  uvicorn api.main:app --reload --port 8000
  python -m api.main

Endpoints :
  POST /ask     → Réponse RAG (question + contexte + Claude)
  POST /search  → Recherche vectorielle seule (sans LLM)
  GET  /health  → Statut de l'API et de l'index
  GET  /stats   → Statistiques de la base documentaire
  POST /auth/register  → Inscription
  POST /auth/login     → Connexion JWT
  GET  /auth/me        → Profil utilisateur (auth requise)
  GET  /lawyers        → Liste d'avocats avec filtres
  GET  /lawyers/{id}   → Profil d'un avocat
  POST /conversations  → Créer une conversation (auth requise)
  GET  /conversations  → Liste des conversations (auth requise)
  GET  /conversations/{id}/messages  → Messages d'une conversation (auth requise)
  POST /conversations/{id}/messages  → Ajouter un message (auth requise)
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Charger .env avant tout (ANTHROPIC_API_KEY, JWT_SECRET, STRIPE...)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True, encoding="utf-8-sig")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Depends, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import (
    AskRequest, AskResponse, SourceDoc,
    SearchRequest, SearchResponse, SearchResult,
    IndexStats,
    # Auth models
    RegisterRequest, LoginRequest, UserResponse, AuthResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    LawyerResponse, LawyerListResponse,
    CreateConversationRequest, ConversationResponse, ConversationListResponse,
    CreateMessageRequest, MessageResponse, MessageListResponse,
    # Billing models
    CheckoutRequest, CheckoutResponse, PortalResponse,
    SubscriptionResponse, PlanInfo, PlansResponse,
    # Shield models
    ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldClause,
    ShieldUploadResponse,
    # Audit Entreprise models
    AuditRequest, AuditResponse,
    # Defend models
    DefendRequest, DefendResponse,
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

# Origines autorisées — lire depuis l'env pour ne pas hardcoder en prod
_CORS_ORIGINS_ENV = os.getenv("LEXAVO_ALLOWED_ORIGINS", "")
if _CORS_ORIGINS_ENV:
    _ALLOWED_ORIGINS: list[str] = [o.strip() for o in _CORS_ORIGINS_ENV.split(",") if o.strip()]
else:
    if os.getenv("DATABASE_URL"):
        log.warning("PRODUCTION sans LEXAVO_ALLOWED_ORIGINS — CORS restreint a lexavo.be")
        _ALLOWED_ORIGINS = ["https://lexavo.be", "https://www.lexavo.be"]
    else:
        _ALLOWED_ORIGINS = [
            "http://localhost:8081",
            "http://localhost:19000",
            "http://localhost:3000",
            "exp://localhost:8081",
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
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
    # Extraire user_id depuis Authorization header (best-effort, sans lever d'exception)
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


# ─── Startup : init DB + seed ───────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    # ─── Validation config critique ────────────────────────────────────────
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

    # ─── Alembic migrations automatiques ─────────────────────────────────────
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_command.upgrade(alembic_cfg, "head")
        log.info("Alembic migrations appliquées")
    except Exception as e:
        log.warning(f"Alembic skip: {e}")

    # ─── Préchargement modèle embedding (évite timeout au 1er /ask) ───────────
    try:
        from rag.retriever import get_model
        log.info("Préchargement du modèle SentenceTransformer...")
        get_model()
        log.info("Modèle embedding prêt.")
    except Exception as exc:
        log.warning(f"Préchargement modèle échoué (non bloquant) : {exc}")


# ─── Dependency : utilisateur authentifié ───────────────────────────────────
from api.auth import get_current_user as _get_current_user


# ─── Dependency : clé API Anthropic ──────────────────────────────────────────
def get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY non définie. Configurez la variable d'environnement.",
        )
    return key


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Vérifie que l'API et l'index sont opérationnels."""
    from rag.indexer import get_index_stats
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
    from rag.indexer import get_index_stats
    data = get_index_stats()
    return IndexStats(**data)


@app.post("/admin/backup")
def admin_backup(current_user: dict = Depends(_get_current_user)):
    """Cree un backup SQLite. Reserve aux admins (user_id=1 pour le MVP)."""
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Acces reserve a l'administrateur.")
    from api.database import backup_database
    path = backup_database()
    return {"status": "ok", "backup_path": path}


@app.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
def ask_endpoint(
    request: Request,
    body: AskRequest,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """
    Endpoint principal : question juridique → reponse RAG avec detection de branche.
    Authentification requise. Quota selon le plan (free: 5/mois, pro/cabinet: illimite).
    Memoire conversationnelle : passer conversation_id pour continuer un fil.
    """
    from rag.pipeline import ask
    from rag.indexer import CHROMA_DIR
    from api.stripe_billing import check_quota
    from api.database import (
        increment_question_count, create_conversation,
        list_messages, create_message, get_conversation_by_id,
    )
    import json

    # Vérifier que l'index est disponible avant de charger le modèle
    if not CHROMA_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail="Index ChromaDB non disponible sur ce serveur. Utilisez l'API locale avec l'index chargé.",
        )

    # Verifier le quota avant d'appeler Claude
    check_quota(current_user["id"])

    # Memoire conversationnelle : charger l'historique si conversation_id fourni
    conversation_id = body.conversation_id
    history = None

    if conversation_id:
        conv = get_conversation_by_id(conversation_id)
        if not conv or conv["user_id"] != current_user["id"]:
            raise HTTPException(404, "Conversation non trouvee.")
        prev_messages = list_messages(conversation_id)
        if prev_messages:
            history = [{"role": m["role"], "content": m["content"]} for m in prev_messages]
    else:
        # Creer une nouvelle conversation avec les premiers mots de la question
        title = body.question[:60] + ("..." if len(body.question) > 60 else "")
        conv = create_conversation(current_user["id"], title)
        conversation_id = conv["id"]

    # OCR des photos si fournies
    enriched_question = body.question
    if body.photos_base64:
        try:
            from api.utils.ocr import extract_text_from_base64_list
            ocr_text = extract_text_from_base64_list(body.photos_base64)
            if ocr_text:
                enriched_question = f"{body.question}\n\n[Texte extrait des photos jointes]\n{ocr_text}"
        except Exception as e:
            log.warning(f"OCR photos /ask ignoré : {e}")

    try:
        result = ask(
            question=enriched_question,
            top_k=body.top_k,
            source_filter=body.source_filter,
            model=body.model,
            anthropic_api_key=api_key,
            branch=body.branch,
            region=body.region,
            history=history,
            language=body.language,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Index indisponible : {str(e)}. Lancez d'abord l'indexation.",
        )
    except Exception as e:
        log.error(f"Erreur pipeline RAG : {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Incrementer le compteur seulement si la reponse a reussi
    increment_question_count(current_user["id"])

    # Sauvegarder la question et la reponse dans la conversation
    sources_list = result.get("sources", [])
    create_message(conversation_id, "user", body.question)
    create_message(conversation_id, "assistant", result["answer"], json.dumps(sources_list, default=str))

    sources = [
        SourceDoc(
            doc_id=s.get("doc_id", ""),
            source=s.get("source", ""),
            title=s.get("title", ""),
            date=s.get("date", ""),
            ecli=s.get("ecli", ""),
            url=s.get("url", ""),
            similarity=s.get("similarity", 0.0),
        )
        for s in sources_list
    ]

    return AskResponse(
        answer=result["answer"],
        sources=sources,
        chunks_used=result["chunks_used"],
        model=result["model"],
        branch=result.get("branch"),
        branch_label=result.get("branch_label"),
        branch_confidence=result.get("branch_confidence", 0.0),
        conversation_id=conversation_id,
    )


@app.get("/branches")
def branches_list():
    """Liste les 15 branches du droit disponibles avec detection automatique."""
    from rag.branches import list_branches
    branches = list_branches()
    return {"branches": branches, "total": len(branches)}


@app.post("/search", response_model=SearchResponse)
@limiter.limit("20/minute")
def search_endpoint(request: Request, body: SearchRequest):
    """
    Recherche vectorielle seule (sans appel LLM).
    Utile pour explorer la base documentaire directement.
    """
    from rag.retriever import retrieve
    from rag.indexer import CHROMA_DIR

    if not CHROMA_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail="Index ChromaDB non disponible sur ce serveur.",
        )

    try:
        chunks = retrieve(
            query=body.query,
            top_k=body.top_k,
            source_filter=body.source_filter,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Index indisponible : {str(e)}",
        )

    results = [
        SearchResult(
            doc_id=c.get("doc_id", ""),
            source=c.get("source", ""),
            doc_type=c.get("doc_type", ""),
            jurisdiction=c.get("jurisdiction", ""),
            title=c.get("title", ""),
            date=c.get("date", ""),
            url=c.get("url", ""),
            ecli=c.get("ecli", ""),
            chunk_text=c.get("chunk_text", ""),
            similarity=c.get("similarity", 0.0),
            score=c.get("score", 0.0),
        )
        for c in chunks
    ]

    return SearchResponse(
        query=body.query,
        results=results,
        total=len(results),
    )


# ─── Auth Endpoints ──────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=AuthResponse)
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest):
    """Inscription d'un nouvel utilisateur."""
    from api.auth import register_user
    result = register_user(
        email=body.email,
        password=body.password,
        name=body.name,
        language=body.language,
    )
    return AuthResponse(
        user=UserResponse(**result["user"]),
        token=result["token"],
        refresh_token=result.get("refresh_token"),
    )


@app.post("/auth/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    """Connexion — retourne un JWT + refresh token."""
    from api.auth import login_user
    result = login_user(email=body.email, password=body.password)
    return AuthResponse(
        user=UserResponse(**result["user"]),
        token=result["token"],
        refresh_token=result.get("refresh_token"),
    )


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: dict = Depends(_get_current_user)):
    """Profil de l'utilisateur connecté."""
    return UserResponse(**current_user)


@app.post("/auth/refresh")
def refresh_token_endpoint(body: dict):
    """Echange un refresh token contre un nouveau access token + nouveau refresh token."""
    from api.database import get_refresh_token, delete_refresh_token, save_refresh_token, get_user_by_id
    from api.auth import create_token, create_refresh_token, REFRESH_TOKEN_EXPIRY_DAYS

    rt = body.get("refresh_token", "")
    if not rt:
        raise HTTPException(status_code=400, detail="refresh_token requis.")

    stored = get_refresh_token(rt)
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expire.")

    # Verifier expiration
    expires_str = str(stored["expires_at"])[:19]
    try:
        expires = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            delete_refresh_token(rt)
            raise HTTPException(status_code=401, detail="Refresh token expire.")
    except ValueError:
        pass

    user = get_user_by_id(stored["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    # Rotation : supprimer l'ancien, creer un nouveau
    delete_refresh_token(rt)
    new_access = create_token(user["id"], user["email"])
    new_refresh = create_refresh_token(user["id"])
    new_expires = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    save_refresh_token(user["id"], new_refresh, new_expires)

    return {"token": new_access, "refresh_token": new_refresh, "user": user}


@app.post("/auth/forgot-password")
@limiter.limit("3/minute")
def forgot_password_endpoint(request: Request, body: ForgotPasswordRequest):
    """Génère un token de reset (valable 1h). En prod, l'envoyer par email."""
    from api.auth import forgot_password
    token = forgot_password(body.email)
    # En prod : envoyer par email. En dev : logger dans les logs serveur.
    log.info("Password reset token pour %s : %s", body.email, token)
    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


@app.post("/auth/reset-password")
@limiter.limit("5/minute")
def reset_password_endpoint(request: Request, body: ResetPasswordRequest):
    """Valide le token et met à jour le mot de passe."""
    from api.auth import reset_password
    reset_password(body.token, body.new_password)
    return {"message": "Mot de passe mis à jour avec succès. Vous pouvez vous reconnecter."}


# ─── Lawyer Endpoints ───────────────────────────────────────────────────────

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


# ─── User Context Endpoints ──────────────────────────────────────────────────

@app.get("/user/context")
def get_user_context_endpoint(
    current_user: dict = Depends(_get_current_user),
):
    """Recuperer le contexte utilisateur (region, profession, langue)."""
    from api.database import get_user_context
    return get_user_context(current_user["id"])


@app.put("/user/context")
def update_user_context_endpoint(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Mettre a jour le contexte utilisateur (region, profession, langue)."""
    from api.database import update_user_context
    return update_user_context(
        current_user["id"],
        region=body.get("region"),
        profession=body.get("profession"),
        language=body.get("language"),
    )


# ─── Conversation Endpoints ─────────────────────────────────────────────────

@app.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(_get_current_user),
):
    """Créer une nouvelle conversation."""
    from api.database import create_conversation as db_create_conv
    conv = db_create_conv(user_id=current_user["id"], title=request.title)
    return ConversationResponse(**conv)


@app.get("/conversations", response_model=ConversationListResponse)
def list_conversations(current_user: dict = Depends(_get_current_user)):
    """Liste des conversations de l'utilisateur connecté."""
    from api.database import list_conversations as db_list_convs
    convs = db_list_convs(user_id=current_user["id"])
    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in convs],
        total=len(convs),
    )


@app.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int,
    current_user: dict = Depends(_get_current_user),
):
    """Supprimer une conversation et tous ses messages (cascade)."""
    from api.database import get_conversation_by_id, delete_conversation

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Acces refuse.")

    delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}


@app.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def get_messages(
    conversation_id: int,
    current_user: dict = Depends(_get_current_user),
):
    """Récupérer les messages d'une conversation."""
    from api.database import get_conversation_by_id, list_messages as db_list_msgs

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    msgs = db_list_msgs(conversation_id)
    return MessageListResponse(
        messages=[MessageResponse(**m) for m in msgs],
        total=len(msgs),
    )


@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def add_message(
    conversation_id: int,
    request: CreateMessageRequest,
    current_user: dict = Depends(_get_current_user),
):
    """Ajouter un message à une conversation."""
    from api.database import get_conversation_by_id, create_message as db_create_msg

    conv = get_conversation_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    if conv["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    if request.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Role doit être 'user' ou 'assistant'.")

    msg = db_create_msg(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        sources_json=request.sources_json or "[]",
    )
    return MessageResponse(**msg)


# ─── Billing Endpoints ─────────────────────────────────────────────────────

@app.get("/billing/plans", response_model=PlansResponse)
def list_plans():
    """Liste les plans tarifaires disponibles."""
    from api.stripe_billing import PLANS, is_beta_active, BETA_END_DATE
    plans = [
        PlanInfo(
            key=key,
            label=cfg["label"],
            subtitle=cfg.get("subtitle", ""),
            price_monthly=cfg["price_monthly"],
            price_annual=cfg.get("price_annual"),
            founding_price=cfg.get("founding_price"),
            max_users=cfg.get("max_users", 1),
            questions_per_month=cfg["questions_per_month"],
            features=cfg["features"],
        )
        for key, cfg in PLANS.items()
    ]
    return PlansResponse(
        plans=plans,
        beta_active=is_beta_active(),
        beta_end=BETA_END_DATE if is_beta_active() else None,
    )


@app.get("/billing/subscription", response_model=SubscriptionResponse)
def get_my_subscription(current_user: dict = Depends(_get_current_user)):
    """Etat de l'abonnement de l'utilisateur connecte."""
    from api.database import get_subscription
    from api.stripe_billing import PLANS, is_beta_active, BETA_END_DATE

    sub = get_subscription(current_user["id"])
    plan = sub.get("plan", "free") if sub else "free"
    plan_config = PLANS.get(plan, PLANS["free"])
    limit = plan_config["questions_per_month"]
    used = sub.get("questions_used", 0) if sub else 0
    beta = is_beta_active()

    return SubscriptionResponse(
        plan=plan,
        status=sub.get("status", "active") if sub else "active",
        questions_used=used,
        questions_limit=-1 if beta else limit,
        questions_remaining=None if (beta or limit == -1) else (limit - used),
        current_period_end=sub.get("current_period_end") if sub else None,
        beta=beta,
        beta_end=BETA_END_DATE if beta else None,
    )


@app.post("/billing/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    current_user: dict = Depends(_get_current_user),
):
    """Creer une session Stripe Checkout pour s'abonner a un plan payant."""
    from api.stripe_billing import create_checkout_session
    result = create_checkout_session(current_user["id"], request.plan, request.billing)
    return CheckoutResponse(**result)


@app.post("/billing/portal", response_model=PortalResponse)
def create_portal(current_user: dict = Depends(_get_current_user)):
    """Ouvrir le portail client Stripe pour gerer l'abonnement."""
    from api.stripe_billing import create_portal_session
    result = create_portal_session(current_user["id"])
    return PortalResponse(**result)


@app.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Webhook Stripe — traite les evenements de paiement."""
    from api.stripe_billing import handle_webhook
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not sig:
        raise HTTPException(400, "Stripe signature manquante")
    result = handle_webhook(payload, sig)
    return result


# ─── Shield Endpoints ─────────────────────────────────────────────────────

@app.post("/shield/analyze", response_model=ShieldAnalyzeResponse)
@limiter.limit("5/minute")
def shield_analyze(
    request: Request,
    body: ShieldAnalyzeRequest,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Analyse un contrat et retourne le verdict feu tricolore."""
    from api.features.shield import analyze_contract_text
    from api.database import save_shield_analysis
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import json as _json

    check_quota(current_user["id"])

    try:
        result = analyze_contract_text(
            text=body.contract_text,
            contract_type=body.contract_type,
            region=body.region,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Shield analysis error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du contrat.")

    increment_question_count(current_user["id"])

    save_shield_analysis(
        user_id=current_user["id"],
        contract_type=result.get("contract_type_detected", "general"),
        verdict=result["verdict"],
        summary=result["summary"],
        clauses_json=_json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=_json.dumps(result.get("sources", []), ensure_ascii=False),
    )

    sources = [SourceDoc(**s) for s in result.get("sources", [])]

    return ShieldAnalyzeResponse(
        verdict=result["verdict"],
        score=result.get("score", 50),
        summary=result["summary"],
        clauses=[ShieldClause(**c) for c in result.get("clauses", [])],
        contract_type_detected=result.get("contract_type_detected"),
        region=result.get("region"),
        legal_sources=sources,
    )


@app.post("/shield/upload", response_model=ShieldUploadResponse)
@limiter.limit("5/minute")
async def shield_upload(
    request: Request,
    file: UploadFile = File(..., description="Contrat PDF ou image (JPG/PNG)"),
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Upload un contrat (PDF/image) puis OCR puis analyse Shield."""
    from api.utils.ocr import extract_text_from_image, extract_text_from_pdf
    from api.features.shield import analyze_contract_text
    from api.database import save_shield_analysis, increment_question_count
    from api.stripe_billing import check_quota
    import json as _json

    check_quota(current_user["id"])

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fichier trop volumineux (max 10 MB)")
    if not (content[:4] == b'%PDF' or content[:3] == b'\xff\xd8\xff' or content[:4] == b'\x89PNG'):
        raise HTTPException(400, "Format non supporté. PDF, JPG ou PNG uniquement.")
    filename = file.filename.lower() if file.filename else ""

    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
    elif filename.endswith((".jpg", ".jpeg", ".png", ".tiff", ".bmp")):
        text = extract_text_from_image(content)
    else:
        raise HTTPException(400, "Format non supporté. Utilisez PDF, JPG ou PNG.")

    if len(text.strip()) < 50:
        raise HTTPException(400, "Impossible d'extraire suffisamment de texte du document.")

    result = analyze_contract_text(text=text)
    increment_question_count(current_user["id"])

    save_shield_analysis(
        user_id=current_user["id"],
        contract_type=result.get("contract_type_detected", "general"),
        verdict=result["verdict"],
        summary=result["summary"],
        clauses_json=_json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=_json.dumps(result.get("sources", []), ensure_ascii=False),
    )

    sources = [SourceDoc(**s) for s in result.get("sources", [])]

    return ShieldUploadResponse(
        extracted_text=text[:2000],
        analysis=ShieldAnalyzeResponse(
            verdict=result["verdict"],
            summary=result["summary"],
            clauses=[ShieldClause(**c) for c in result.get("clauses", [])],
            contract_type_detected=result.get("contract_type_detected"),
            legal_sources=sources,
        ),
    )


@app.get("/shield/history")
def shield_history(current_user: dict = Depends(_get_current_user)):
    """Historique des analyses Shield de l'utilisateur."""
    from api.database import list_shield_analyses
    import json as _json

    analyses = list_shield_analyses(current_user["id"])
    for a in analyses:
        a["clauses"] = _json.loads(a.get("clauses_json", "[]"))
        a["sources"] = _json.loads(a.get("sources_json", "[]"))
    return {"analyses": analyses, "total": len(analyses)}


# ─── Decode Endpoints ──────────────────────────────────────────────────────

@app.post("/decode/analyze")
@limiter.limit("5/minute")
def decode_analyze(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Traduit un document administratif en langage clair."""
    from api.features.decode import decode_document
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    text = body.get("document_text") or body.get("text", "")
    if len(text.strip()) < 20:
        raise HTTPException(400, "Le document est trop court.")

    check_quota(current_user["id"])
    result = decode_document(text=text)
    increment_question_count(current_user["id"])
    return result


@app.post("/decode/upload")
@limiter.limit("5/minute")
async def decode_upload(
    request: Request,
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Upload un document admin (PDF/image) puis OCR puis traduction."""
    from api.utils.ocr import extract_text_from_image, extract_text_from_pdf
    from api.features.decode import decode_document
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    check_quota(current_user["id"])

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Fichier trop volumineux (max 10 MB)")
    if not (content[:4] == b'%PDF' or content[:3] == b'\xff\xd8\xff' or content[:4] == b'\x89PNG'):
        raise HTTPException(400, "Format non supporté. PDF, JPG ou PNG uniquement.")
    filename = file.filename.lower() if file.filename else ""

    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
    elif filename.endswith((".jpg", ".jpeg", ".png", ".tiff", ".bmp")):
        text = extract_text_from_image(content)
    else:
        raise HTTPException(400, "Format non supporté.")

    if len(text.strip()) < 20:
        raise HTTPException(400, "Impossible d'extraire du texte.")

    result = decode_document(text=text)
    increment_question_count(current_user["id"])
    return {"extracted_text": text[:2000], "analysis": result}


# ─── Calculator Endpoints ──────────────────────────────────────────────────

@app.post("/calculators/notice-period")
def calc_notice(body: dict):
    """Calculateur de préavis de licenciement (CCT n 109)."""
    from api.features.calculators import calculate_notice_period
    try:
        years = int(body.get("years", 0))
        monthly_salary = float(body.get("monthly_salary", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    if monthly_salary <= 0:
        raise HTTPException(400, "Salaire mensuel requis (> 0)")
    return calculate_notice_period(years=years, monthly_salary=monthly_salary)


@app.post("/calculators/alimony")
def calc_alimony(body: dict):
    """Calculateur de pension alimentaire (barème Renard)."""
    from api.features.calculators import calculate_alimony_renard
    try:
        income_high = float(body.get("income_high", 0))
        income_low = float(body.get("income_low", 0))
        children = int(body.get("children", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    return calculate_alimony_renard(
        income_high=income_high, income_low=income_low, children=children
    )


@app.post("/calculators/succession")
def calc_succession(body: dict):
    """Calculateur de droits de succession par région."""
    from api.features.calculators import calculate_succession_duties
    region = body.get("region", "bruxelles")
    try:
        amount = float(body.get("amount", 0) or body.get("estate_value", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")
    raw_rel = body.get("relationship", "direct_line")
    # Normaliser les variantes courantes
    rel_map = {"enfant": "direct_line", "parent": "direct_line", "conjoint": "direct_line",
               "frere": "siblings", "soeur": "siblings", "frère": "siblings", "sœur": "siblings",
               "autre": "others", "other": "others", "oncle": "others", "tante": "others", "neveu": "others"}
    relationship = rel_map.get(raw_rel, raw_rel) if raw_rel not in ("direct_line", "siblings", "others") else raw_rel
    return calculate_succession_duties(
        region=region, amount=amount, relationship=relationship
    )


# ─── Diagnostic Endpoints ──────────────────────────────────────────────────

@app.get("/diagnostic/questions")
def diagnostic_questions():
    """Retourne les 6 questions du diagnostic."""
    from api.features.diagnostic import get_questions
    return {"questions": get_questions()}


@app.post("/diagnostic/analyze")
@limiter.limit("5/minute")
def diagnostic_analyze(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere un diagnostic personnalise a partir des reponses."""
    from api.features.diagnostic import generate_diagnostic
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    answers = body.get("answers", [])
    # Si description directe (sans questionnaire), créer une réponse auto
    description = body.get("description", "")
    if not answers and description:
        answers = [
            {"question_id": 1, "answer": description},
            {"question_id": 2, "answer": body.get("region", "bruxelles")},
            {"question_id": 3, "answer": "analyse demandée"},
        ]
    if len(answers) < 3:
        raise HTTPException(status_code=400, detail="Minimum 3 réponses requises pour un diagnostic.")
    check_quota(current_user["id"])
    try:
        result = generate_diagnostic(answers=answers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    increment_question_count(current_user["id"])
    return result


# ─── Score Endpoints ───────────────────────────────────────────────────────

@app.get("/score/questions")
def score_questions():
    """Retourne les 10 questions du Score de sante juridique."""
    from api.features.score import get_score_questions
    return {"questions": get_score_questions()}


@app.post("/score/evaluate")
def score_evaluate(body: dict):
    """Calcule le score de sante juridique."""
    from api.features.score import calculate_score
    answers = body.get("answers", [])
    # Convertir dict en liste si nécessaire
    if isinstance(answers, dict):
        answers = [{"question_id": i+1, "answer": v} for i, (k, v) in enumerate(answers.items())]
    if not isinstance(answers, list):
        raise HTTPException(status_code=400, detail="answers doit être une liste.")
    try:
        return calculate_score(answers=answers)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Legal Response Endpoints ──────────────────────────────────────────────

@app.post("/response/generate")
@limiter.limit("5/minute")
def response_generate(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere une reponse a un courrier juridique recu."""
    from api.features.legal_response import generate_response
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    received_text = body.get("received_text", "") or body.get("received_letter", "") or body.get("letter_text", "")
    user_context = body.get("user_context") or body.get("tone")

    if len(received_text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Le courrier est trop court (minimum 20 caractères).")
    check_quota(current_user["id"])
    try:
        result = generate_response(received_text=received_text, user_context=user_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    increment_question_count(current_user["id"])
    return result


# ─── Contracts Endpoints ──────────────────────────────────────────────────

@app.get("/contracts/templates")
def contracts_list(
    category: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
):
    """Liste les templates de contrats disponibles."""
    from api.features.contracts import list_templates
    templates = list_templates(category=category, region=region)
    return {"templates": templates, "total": len(templates)}


@app.get("/contracts/{template_id}")
def contracts_get(template_id: str):
    """Detail d'un template de contrat."""
    from api.features.contracts import get_template
    template = get_template(template_id)
    if not template:
        raise HTTPException(404, "Template introuvable.")
    return template


@app.post("/contracts/{template_id}/generate")
def contracts_generate(
    template_id: str,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Genere un contrat HTML rempli."""
    from api.features.contracts import generate_contract_html
    variables = body.get("variables", {})
    html = generate_contract_html(template_id=template_id, variables=variables)
    return {"html": html, "template_id": template_id}


# ─── Compliance Endpoints ──────────────────────────────────────────────────

@app.get("/compliance/questions")
def compliance_questions():
    """Retourne les 15 questions d'audit compliance."""
    from api.features.compliance import get_compliance_questions
    return {"questions": get_compliance_questions()}


@app.post("/compliance/audit")
@limiter.limit("3/minute")
def compliance_audit(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Genere un rapport d'audit de conformite."""
    from api.features.compliance import generate_compliance_audit
    answers = body.get("answers", [])
    company_type = body.get("company_type", "independant")
    if not answers or len(answers) < 5:
        raise HTTPException(status_code=400, detail="Minimum 5 réponses requises. Utilisez GET /compliance/questions pour obtenir les questions.")
    try:
        return generate_compliance_audit(answers=answers, company_type=company_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Audit Entreprise Endpoints ───────────────────────────────────────────

@app.get("/audit/questions")
def audit_questions(
    company_type: str = Query(default="srl", description="Type d'entreprise"),
):
    """Retourne les 30 questions d'audit adaptees au type d'entreprise."""
    from api.features.audit_entreprise import get_audit_questions, get_company_types, get_audit_categories
    return {
        "questions": get_audit_questions(company_type),
        "company_types": get_company_types(),
        "categories": get_audit_categories(),
    }


@app.post("/audit/generate", response_model=AuditResponse)
@limiter.limit("3/minute")
def audit_generate(
    request: Request,
    body: AuditRequest,
    current_user: dict = Depends(_get_current_user),
):
    """Genere un rapport d'audit de conformite complet pour PME/entreprise.
    Reserve aux plans Business, Firm et Enterprise."""
    from api.features.audit_entreprise import generate_audit_report
    from api.stripe_billing import check_quota
    from api.database import get_subscription
    import json as _json

    # Verifier le quota
    check_quota(current_user["id"])

    # Verifier le plan (business+ uniquement, sauf beta)
    from api.stripe_billing import is_beta_active
    if not is_beta_active():
        sub = get_subscription(current_user["id"])
        plan = sub.get("plan", "free") if sub else "free"
        if plan in ("free", "basic"):
            raise HTTPException(
                status_code=403,
                detail="L'audit entreprise est reserve aux plans Business, Firm et Enterprise. Mettez a niveau votre abonnement.",
            )

    result = generate_audit_report(
        answers=[{"question_id": a.question_id, "answer": a.answer} for a in body.answers],
        company_type=body.company_type,
        company_name=body.company_name or "",
        sector=body.sector or "",
        employees=body.employees or 0,
    )

    # Incrementer le compteur de questions
    from api.database import increment_question_count
    increment_question_count(current_user["id"])

    return AuditResponse(**result)


@app.get("/audit/history")
def audit_history(current_user: dict = Depends(_get_current_user)):
    """Historique des audits de l'utilisateur."""
    from api.database import get_audit_reports
    reports = get_audit_reports(current_user["id"])
    return {"reports": reports, "total": len(reports)}


# ─── Lexavo Defend Endpoints ──────────────────────────────────────────────

@app.get("/defend/categories")
def defend_categories():
    """Retourne les categories de situations contestables."""
    from api.features.defend import get_defend_categories
    return {"categories": get_defend_categories()}


@app.post("/defend/detect")
def defend_detect(body: dict):
    """Detecte automatiquement le type de situation."""
    from api.features.defend import detect_situation_type
    description = body.get("description", "")
    if len(description.strip()) < 10:
        raise HTTPException(400, "Description trop courte")
    return detect_situation_type(description)


@app.post("/defend/analyze", response_model=DefendResponse)
@limiter.limit("5/minute")
def defend_analyze(
    request: Request,
    body: DefendRequest,
    current_user: dict = Depends(_get_current_user),
):
    """Analyse la situation et genere le document de contestation/recours."""
    from api.features.defend import analyze_and_generate
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    check_quota(current_user["id"])

    try:
        result = analyze_and_generate(
            description=body.description,
            category=body.category,
            region=body.region,
            user_name=body.user_name or "",
            user_address=body.user_address or "",
            photos_base64=body.photos_base64 or [],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Defend error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse.")

    increment_question_count(current_user["id"])

    sources = [SourceDoc(**s) for s in result.get("sources", [])]
    laws = [{"article": l.get("article", ""), "content": l.get("content", ""), "source": l.get("source")} for l in result.get("applicable_law", [])]

    return DefendResponse(
        detection=result.get("detection", {}),
        situation_analysis=result.get("situation_analysis", ""),
        applicable_law=laws,
        contestation_possible=result.get("contestation_possible", False),
        success_probability=result.get("success_probability", "indeterminee"),
        document_type=result.get("document_type", "contestation"),
        document_text=result.get("document_text", ""),
        recipient=result.get("recipient"),
        deadline=result.get("deadline"),
        next_steps=result.get("next_steps", []),
        cost_estimate=result.get("cost_estimate"),
        sources=sources,
        generated_at=result.get("generated_at", ""),
    )


@app.post("/defend/checklist")
@limiter.limit("10/minute")
def defend_checklist(request: Request, body: dict):
    """Analyse la checklist de vices de forme et génère la lettre de contestation."""
    from api.features.defend import analyze_checklist
    try:
        result = analyze_checklist(
            category=body.get("category", "amende"),
            answers=body.get("answers", {}),
            region=body.get("region"),
            extra_description=body.get("description", ""),
            photos_base64=body.get("photos", []),
            tone=body.get("tone", "formel"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/defend/checklist error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse")


@app.post("/defend/regenerate-letter")
@limiter.limit("10/minute")
def defend_regenerate_letter(request: Request, body: dict):
    """Régénère uniquement la lettre avec un ton différent, sans relancer l'analyse."""
    from api.features.defend import generate_letter, TONE_INSTRUCTIONS
    tone = body.get("tone", "formel")
    if tone not in TONE_INSTRUCTIONS:
        raise HTTPException(status_code=400, detail=f"Ton invalide. Options : {list(TONE_INSTRUCTIONS.keys())}")
    description = body.get("description", "")
    vices_str   = body.get("vices_str", "")
    legal_ctx   = body.get("legal_context", "")
    try:
        letter = generate_letter(description, vices_str, legal_ctx, tone=tone)
        return {"letter": letter, "tone": tone}
    except Exception as e:
        log.error(f"/defend/regenerate-letter error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération")


@app.post("/defend/scan-amende")
@limiter.limit("5/minute")
def defend_scan_amende(request: Request, body: dict):
    """Extrait les données d'un PV ou lettre photographié(e) via Claude Vision."""
    from api.features.defend import scan_amende
    photos = body.get("photos", [])
    if not photos:
        raise HTTPException(status_code=400, detail="Au moins une photo est requise")
    try:
        result = scan_amende(
            photos_base64=photos,
            category=body.get("category", "amende"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/defend/scan-amende error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du scan")


# ─── Alerts Endpoints ─────────────────────────────────────────────────────

@app.get("/alerts/domains")
def alerts_domains():
    """Liste les domaines juridiques disponibles pour les alertes."""
    from api.features.alerts import get_alert_domains
    return {"domains": get_alert_domains()}


@app.post("/alerts/preferences")
def alerts_save_preferences(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Sauvegarde les preferences d'alertes de l'utilisateur (persistees en DB)."""
    from api.database import update_alert_preferences
    domains = body.get("domains", [])
    frequency = body.get("frequency")
    enabled = body.get("enabled")
    prefs = update_alert_preferences(
        user_id=current_user["id"], domains=domains, frequency=frequency, enabled=enabled,
    )
    return prefs


@app.get("/alerts/feed")
def alerts_feed(
    current_user: dict = Depends(_get_current_user),
    domains: Optional[str] = Query(default=None, description="Domaines séparés par virgule"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Retourne le fil d'alertes legislatives personnalise."""
    from api.features.alerts import get_alert_feed
    try:
        if domains:
            domain_list = [d.strip() for d in domains.split(",")]
        else:
            from api.database import get_alert_preferences
            prefs = get_alert_preferences(current_user["id"])
            domain_list = prefs.get("domains", []) if isinstance(prefs, dict) else []
    except Exception:
        domain_list = []
    if not domain_list:
        domain_list = ["travail", "fiscal", "bail"]
    try:
        feed = get_alert_feed(domains=domain_list, limit=limit)
    except Exception:
        feed = []
    return {"alerts": feed, "total": len(feed)}


# ─── Litigation Endpoints ─────────────────────────────────────────────────

@app.get("/litigation/stages")
def litigation_stages():
    """Liste les etapes du recouvrement d'impayes."""
    from api.features.litigation import get_stages
    return {"stages": get_stages()}


@app.post("/litigation/start")
@limiter.limit("5/minute")
def litigation_start(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Demarre une procedure de recouvrement d'impaye."""
    from api.features.litigation import start_litigation
    try:
        result = start_litigation(
            creditor_name=body.get("creditor_name", ""),
            debtor_name=body.get("debtor_name", ""),
            amount=body.get("amount", 0),
            invoice_number=body.get("invoice_number", ""),
            due_date=body.get("due_date", ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Match Endpoints ─────────────────────────────────────────────────────

@app.post("/match/find")
def match_find(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Trouve les avocats les mieux adaptes a la situation."""
    from api.features.match import find_matching_lawyers
    try:
        result = find_matching_lawyers(
            description=body.get("description", ""),
            city=body.get("city"),
            language=body.get("language", "fr"),
            budget=body.get("budget"),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Emergency Endpoints ─────────────────────────────────────────────────

@app.get("/emergency/categories")
def emergency_categories():
    """Liste les categories d'urgence juridique."""
    from api.features.emergency import get_categories
    return {"categories": get_categories()}


@app.post("/emergency/request")
def emergency_request(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Cree une demande d'assistance juridique urgente (49 EUR) + Stripe checkout."""
    from api.features.emergency import create_emergency_request, EMERGENCY_PRICE_CENTS
    try:
        result = create_emergency_request(
            user_id=current_user["id"],
            category=body.get("category", "autre"),
            description=body.get("description", ""),
            phone=body.get("phone", ""),
            city=body.get("city", ""),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Creer la session Stripe 49 EUR (paiement unique)
    try:
        import stripe as _stripe
        from api.stripe_billing import FRONTEND_URL
        session = _stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": EMERGENCY_PRICE_CENTS,
                    "product_data": {"name": "Lexavo Emergency — Avocat en 2h"},
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/emergency/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/emergency/cancel",
            metadata={
                "lexavo_user_id": str(current_user["id"]),
                "lexavo_type": "emergency",
                "emergency_id": str(result["id"]),
            },
        )
        result["checkout_url"] = session.url
        result["stripe_session_id"] = session.id
    except Exception as e:
        log.error(f"Stripe emergency checkout error: {e}")
        # Retourner le résultat sans checkout_url — mobile gère le cas
        result["checkout_url"] = None
        result["stripe_session_id"] = None

    return result


# ─── Proof Endpoints ─────────────────────────────────────────────────────

@app.post("/proof/create")
def proof_create(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Cree un nouveau dossier de preuves (persiste en DB)."""
    from api.database import create_proof_case
    title = body.get("title", "")
    if not title or len(title.strip()) < 3:
        raise HTTPException(400, "Le titre du dossier doit contenir au moins 3 caracteres.")
    result = create_proof_case(
        user_id=current_user["id"],
        title=title.strip(),
        description=body.get("description", ""),
    )
    return result


@app.get("/proof/cases")
def proof_list(current_user: dict = Depends(_get_current_user)):
    """Liste les dossiers de preuves de l'utilisateur."""
    from api.database import list_proof_cases
    cases = list_proof_cases(current_user["id"])
    return {"cases": cases, "total": len(cases)}


@app.post("/proof/{case_id}/add-entry")
def proof_add_entry(
    case_id: int,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Ajoute une piece au dossier de preuves (persiste en DB)."""
    from api.database import get_proof_case, add_proof_entry
    case = get_proof_case(case_id)
    if not case:
        raise HTTPException(404, "Dossier de preuves introuvable.")
    if case["user_id"] != current_user["id"]:
        raise HTTPException(403, "Acces refuse a ce dossier.")
    entry = add_proof_entry(
        case_id=case_id,
        entry_type=body.get("type", "note"),
        content=body.get("content", ""),
        metadata=body.get("metadata"),
    )
    return entry


@app.get("/proof/{case_id}/entries")
def proof_entries(
    case_id: int,
    current_user: dict = Depends(_get_current_user),
):
    """Liste les pieces d'un dossier de preuves."""
    from api.database import get_proof_case, list_proof_entries
    case = get_proof_case(case_id)
    if not case:
        raise HTTPException(404, "Dossier de preuves introuvable.")
    if case["user_id"] != current_user["id"]:
        raise HTTPException(403, "Acces refuse.")
    entries = list_proof_entries(case_id)
    return {"entries": entries, "total": len(entries)}


# ─── Heritage Endpoints ──────────────────────────────────────────────────

@app.post("/heritage/guide")
def heritage_guide(body: dict):
    """Genere un guide succession personnalise par region."""
    from api.features.heritage import generate_heritage_guide
    try:
        result = generate_heritage_guide(
            region=body.get("region", ""),
            relationship=body.get("relationship", "direct_line"),
            has_testament=body.get("has_testament", False),
            has_real_estate=body.get("has_real_estate", False),
            estimated_value=body.get("estimated_value", 0),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Fiscal Endpoints ────────────────────────────────────────────────────

@app.post("/fiscal/ask")
@limiter.limit("5/minute")
def fiscal_ask(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Copilote fiscal — repond aux questions TVA et impots."""
    from api.features.fiscal import ask_fiscal
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    question = body.get("question", "")
    photos_base64 = body.get("photos_base64") or []
    check_quota(current_user["id"])
    try:
        result = ask_fiscal(question=question, photos_base64=photos_base64)
        increment_question_count(current_user["id"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Newsletter Endpoints ────────────────────────────────────────────────────

@app.get("/newsletter/preview")
def newsletter_preview(week: int = Query(default=1, ge=1, le=52, description="Numéro de semaine (1-52)")):
    """
    GET /newsletter/preview?week=1
    Retourne le HTML de la newsletter de la semaine donnée.
    Utile pour prévisualiser avant envoi.
    """
    from api.features.newsletter import generate_newsletter_html
    from fastapi.responses import HTMLResponse
    html = generate_newsletter_html(week_num=week)
    return HTMLResponse(content=html, status_code=200)


@app.post("/newsletter/subscribe")
def newsletter_subscribe(body: dict):
    """
    POST /newsletter/subscribe
    Body : { "email": "...", "domains": ["travail", "fiscal"] }
    Inscrit l'email à la newsletter hebdomadaire.
    """
    from api.database import subscribe_newsletter
    import re

    email = body.get("email", "").strip().lower()
    domains = body.get("domains", [])

    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise HTTPException(status_code=400, detail="Adresse email invalide.")

    if not isinstance(domains, list):
        domains = []

    result = subscribe_newsletter(email=email, domains=domains)
    if not result:
        raise HTTPException(status_code=409, detail="Email déjà inscrit.")

    return {
        "status": "subscribed",
        "email": result["email"],
        "domains": result["domains"],
        "confirmed": result["confirmed"],
        "message": "Inscription enregistrée. Consultez vos emails pour confirmer.",
    }


@app.get("/newsletter/unsubscribe")
def newsletter_unsubscribe(token: str = Query(..., description="Token de désinscription")):
    """
    GET /newsletter/unsubscribe?token=xxx
    Désinscrit l'abonné correspondant au token.
    """
    from api.database import unsubscribe_newsletter
    from fastapi.responses import HTMLResponse

    success = unsubscribe_newsletter(token=token)
    if success:
        html = """<!DOCTYPE html><html><body style="font-family:Arial;text-align:center;padding:60px">
        <h2 style="color:#1C2B3A">Vous êtes désinscrit(e)</h2>
        <p>Vous ne recevrez plus la newsletter Lexavo.</p>
        <a href="https://lexavo.be" style="color:#E85D26">Retourner sur Lexavo →</a>
        </body></html>"""
        return HTMLResponse(content=html, status_code=200)
    raise HTTPException(status_code=404, detail="Token de désinscription inconnu ou déjà utilisé.")


# ─── Push Notifications Endpoints ────────────────────────────────────────────

@app.post("/notifications/register")
def notifications_register(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """
    POST /notifications/register
    Enregistre le token push Expo d'un appareil.
    Body : { "token": "ExponentPushToken[...]" }
    """
    from api.database import save_push_token

    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token push manquant.")

    save_push_token(user_id=current_user["id"], token=token)
    return {"status": "registered", "token": token}


@app.post("/notifications/preferences")
def notifications_preferences(
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """
    POST /notifications/preferences
    Met à jour les préférences de notification d'un utilisateur.
    Body : {
      "token": "ExponentPushToken[...]",
      "preferences": { "legal_alerts": true, "deadlines": true, "news": false, "subscription": true }
    }
    """
    from api.database import update_push_preferences

    token       = body.get("token", "").strip()
    preferences = body.get("preferences", {})

    if not isinstance(preferences, dict):
        raise HTTPException(status_code=400, detail="Préférences invalides.")

    update_push_preferences(
        user_id=current_user["id"],
        token=token,
        preferences=preferences,
    )
    return {"status": "updated", "preferences": preferences}


# ─── Billing cancel / restore ─────────────────────────────────────────────────

@app.post("/billing/cancel")
def billing_cancel(current_user: dict = Depends(_get_current_user)):
    """
    POST /billing/cancel
    Annule l'abonnement Stripe de l'utilisateur connecté (à la fin de la période).
    """
    from api.stripe_billing import cancel_subscription

    result = cancel_subscription(current_user["id"])
    return result


@app.post("/billing/restore")
def billing_restore(current_user: dict = Depends(_get_current_user)):
    """
    POST /billing/restore
    Réactive un abonnement annulé (si encore dans la période de grâce Stripe).
    """
    from api.stripe_billing import restore_subscription

    result = restore_subscription(current_user["id"])
    return result


# ─── Student Endpoints (Quiz + Flashcards + Résumés) ─────────────────────────

STUDENT_BRANCHES = [
    "Droit du travail", "Droit familial", "Droit fiscal", "Droit penal",
    "Droit civil", "Droit administratif", "Droit commercial", "Droit immobilier",
    "Droit de l'environnement", "Propriete intellectuelle", "Securite sociale",
    "Droit des etrangers", "Droits fondamentaux", "Marches publics", "Droit europeen",
]


@app.get("/student/branches")
def student_branches():
    """Liste les branches du droit disponibles pour les étudiants."""
    return {"branches": STUDENT_BRANCHES}


@app.post("/student/quiz")
@limiter.limit("10/minute")
def student_quiz(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Génère un quiz de 10 questions QCM sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic, json as _json

    branch = body.get("branch", "Droit civil")
    difficulty = body.get("difficulty", "moyen")
    try:
        num_questions = min(int(body.get("num_questions", 10)), 15)
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")

    check_quota(current_user["id"])

    client = anthropic.Anthropic()
    prompt = f"""Tu es un professeur de droit belge. Génère un quiz de {num_questions} questions QCM
sur la branche : {branch}. Difficulté : {difficulty}.

Réponds UNIQUEMENT en JSON valide (pas de markdown, pas de ```):
{{
  "branch": "{branch}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "id": 1,
      "question": "La question...",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "explanation": "Explication juridique avec référence légale belge..."
    }}
  ]
}}

Chaque question doit référencer un article de loi belge ou un principe juridique belge réel.
Ne jamais inventer de loi ou d'article."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (quiz): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du quiz: {e}")
    text = msg.content[0].text.strip()
    # Nettoyer le JSON si enveloppé dans ```json
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = _json.loads(text)
    except _json.JSONDecodeError:
        result = {"branch": branch, "raw_response": text}

    increment_question_count(current_user["id"])
    return result


@app.post("/student/flashcards")
@limiter.limit("10/minute")
def student_flashcards(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Génère des flashcards recto/verso sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic, json as _json

    branch = body.get("branch", "Droit civil")
    topic = body.get("topic", "")
    try:
        num_cards = min(int(body.get("num_cards", 12)), 20)
    except (ValueError, TypeError):
        raise HTTPException(400, "Paramètres numériques invalides")

    check_quota(current_user["id"])

    extra = f" Focus sur le sujet : {topic}." if topic else ""
    client = anthropic.Anthropic()
    prompt = f"""Tu es un professeur de droit belge. Génère {num_cards} flashcards pour réviser
la branche : {branch}.{extra}

Réponds UNIQUEMENT en JSON valide (pas de markdown, pas de ```):
{{
  "branch": "{branch}",
  "cards": [
    {{
      "id": 1,
      "front": "Question ou concept (recto)",
      "back": "Réponse détaillée avec article de loi belge (verso)",
      "category": "sous-catégorie"
    }}
  ]
}}

Chaque carte doit référencer le droit belge réel. Ne jamais inventer."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (flashcards): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des flashcards: {e}")
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = _json.loads(text)
    except _json.JSONDecodeError:
        result = {"branch": branch, "raw_response": text}

    increment_question_count(current_user["id"])
    return result


@app.post("/student/summary")
@limiter.limit("10/minute")
def student_summary(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Génère un résumé structuré d'un sujet de droit belge pour étudiants."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    import anthropic

    branch = body.get("branch", "Droit civil")
    topic = body.get("topic", branch)

    check_quota(current_user["id"])

    client = anthropic.Anthropic()
    prompt = f"""Tu es un professeur de droit belge. Rédige un résumé structuré et pédagogique sur :
**{topic}** (branche : {branch}).

Structure :
1. Définition et principes fondamentaux
2. Base légale (articles de loi belges réels)
3. Conditions d'application
4. Jurisprudence importante (arrêts réels belges)
5. Points d'attention pour l'examen
6. Schéma récapitulatif (en texte)

Niveau : étudiant en droit (Bachelor/Master). Droit belge uniquement.
Ne jamais inventer de loi, d'article ou de jurisprudence."""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        log.error(f"Erreur API Claude (summary): {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du résumé: {e}")

    increment_question_count(current_user["id"])
    return {"branch": branch, "topic": topic, "summary": msg.content[0].text}


# ─── Student Gamification Endpoints ─────────────────────────────────────────

@app.get("/student/dashboard")
@limiter.limit("20/minute")
def student_dashboard(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Dashboard etudiant : XP, level, streak, badges, progression, activite recente."""
    from api.features.student import get_dashboard_data
    return get_dashboard_data(current_user["id"])


@app.post("/student/activity")
@limiter.limit("30/minute")
def student_activity(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Enregistre une activite et calcule XP, streak, badges."""
    from api.features.student import calculate_xp, check_and_award_badges, compute_level
    from api.database import (
        upsert_student_progress, update_student_streak,
        save_quiz_history, get_student_total_xp,
    )

    mode = body.get("mode", "quiz")
    branch = body.get("branch", "Droit civil")
    score = int(body.get("score", 0))
    total = int(body.get("total", 0))

    streak_info = update_student_streak(current_user["id"])
    streak_active = streak_info.get("streak_count", 0) > 1

    xp_earned = calculate_xp(mode, score, total, streak_active)
    upsert_student_progress(current_user["id"], branch, xp_earned,
                            quiz_done=1 if mode in ("quiz", "mock_exam", "interleaved", "free_recall") else 0,
                            correct=score, mode=mode)
    save_quiz_history(current_user["id"], branch, mode, score, total, "moyen", xp_earned)
    new_badges = check_and_award_badges(current_user["id"])
    total_xp = get_student_total_xp(current_user["id"])
    level = compute_level(total_xp)

    return {
        "xp_earned": xp_earned,
        "total_xp": total_xp,
        "level": level,
        "streak": streak_info,
        "new_badges": new_badges,
        "streak_multiplier": streak_active,
    }


@app.get("/student/leaderboard")
@limiter.limit("20/minute")
def student_leaderboard(
    request: Request,
    scope: str = "global",
    branch: str = None,
    group_id: int = None,
):
    """Leaderboard global, par branche ou par groupe."""
    from api.database import get_leaderboard, get_group_leaderboard
    if scope == "group" and group_id:
        return {"scope": "group", "group_id": group_id, "ranking": get_group_leaderboard(group_id)}
    return {"scope": scope, "branch": branch, "ranking": get_leaderboard(branch=branch, limit=20)}


@app.get("/student/badges")
@limiter.limit("20/minute")
def student_badges_endpoint(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Liste tous les badges disponibles + ceux gagnes."""
    from api.database import get_student_badges
    from api.features.student import BADGES
    earned = get_student_badges(current_user["id"])
    earned_ids = {b["badge_id"] for b in earned}
    return {
        "earned": earned,
        "available": [dict(b, earned=b["id"] in earned_ids) for b in BADGES],
    }


@app.get("/student/weak-branches")
@limiter.limit("20/minute")
def student_weak_branches(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Branches les plus faibles pour revision ciblee."""
    from api.database import get_weak_branches
    return {"weak_branches": get_weak_branches(current_user["id"], limit=3)}


@app.post("/student/case-study")
@limiter.limit("5/minute")
def student_case_study(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere un cas pratique IA sur une branche du droit belge."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_case_study

    branch = body.get("branch", "Droit civil")
    difficulty = body.get("difficulty", "moyen")

    check_quota(current_user["id"])

    # Optionnel: enrichir avec RAG
    rag_context = ""
    try:
        from rag.retriever import search_legal
        results = search_legal(f"jurisprudence {branch} Belgique", top_k=5)
        if results:
            rag_context = "\n".join([r.get("text", "")[:300] for r in results[:3]])
    except Exception:
        pass

    result = generate_case_study(branch, difficulty, rag_context)
    increment_question_count(current_user["id"])
    return result


@app.post("/student/case-study/evaluate")
@limiter.limit("5/minute")
def student_case_study_evaluate(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Evalue la reponse d'un etudiant a un cas pratique."""
    from api.features.student import evaluate_case_study
    case_data = body.get("case_data", {})
    answer = body.get("answer", "")
    if not answer or len(answer.strip()) < 50:
        raise HTTPException(status_code=400, detail="Reponse trop courte (minimum 50 caracteres).")
    return evaluate_case_study(case_data, answer.strip())


@app.post("/student/mock-exam")
@limiter.limit("5/minute")
def student_mock_exam(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere un examen blanc QCM multi-branches."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_mock_exam

    branches = body.get("branches", ["Droit civil"])
    num_questions = min(int(body.get("num_questions", 20)), 30)

    check_quota(current_user["id"])
    result = generate_mock_exam(branches, num_questions)
    increment_question_count(current_user["id"])
    return result


@app.post("/student/mock-exam/submit")
@limiter.limit("10/minute")
def student_mock_exam_submit(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Corrige et note un examen blanc soumis."""
    from api.features.student import evaluate_mock_exam
    exam_data = body.get("exam_data", {})
    answers = body.get("answers", {})
    return evaluate_mock_exam(exam_data, answers)


@app.post("/student/free-recall")
@limiter.limit("5/minute")
def student_free_recall(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere une question ouverte pour rappel libre (active recall maximal)."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_free_recall_question

    branch = body.get("branch", "Droit civil")
    check_quota(current_user["id"])
    result = generate_free_recall_question(branch)
    increment_question_count(current_user["id"])
    return result


@app.post("/student/free-recall/evaluate")
@limiter.limit("5/minute")
def student_free_recall_evaluate(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Evalue une reponse de rappel libre."""
    from api.features.student import evaluate_free_recall
    question_data = body.get("question_data", {})
    answer = body.get("answer", "")
    if not answer or len(answer.strip()) < 20:
        raise HTTPException(status_code=400, detail="Reponse trop courte (minimum 20 caracteres).")
    return evaluate_free_recall(question_data, answer.strip())


@app.post("/student/interleaved-quiz")
@limiter.limit("5/minute")
def student_interleaved_quiz(
    request: Request,
    body: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere un quiz melange multi-branches (interleaving)."""
    from api.stripe_billing import check_quota
    from api.database import increment_question_count
    from api.features.student import generate_interleaved_quiz

    branches = body.get("branches", ["Droit civil", "Droit penal", "Droit du travail"])
    num_per_branch = min(int(body.get("num_per_branch", 3)), 5)

    check_quota(current_user["id"])
    result = generate_interleaved_quiz(branches, num_per_branch)
    increment_question_count(current_user["id"])
    return result


# ─── Student Groups Endpoints ──────────────────────────────────────────────

@app.post("/student/groups")
@limiter.limit("10/minute")
def create_group(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Cree un groupe d'etude. Retourne le code a partager."""
    from api.database import create_student_group
    name = body.get("name", "").strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nom du groupe requis (min 2 caracteres).")
    group = create_student_group(name, current_user["id"])
    return group


@app.post("/student/groups/join")
@limiter.limit("10/minute")
def join_group(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Rejoindre un groupe par code."""
    from api.database import join_student_group
    code = body.get("code", "").strip().upper()
    if not code or len(code) != 6:
        raise HTTPException(status_code=400, detail="Code invalide (6 caracteres).")
    group = join_student_group(code, current_user["id"])
    if not group:
        raise HTTPException(status_code=404, detail="Groupe introuvable.")
    return group


@app.get("/student/groups")
@limiter.limit("20/minute")
def list_groups(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Liste les groupes de l'utilisateur."""
    from api.database import get_user_groups
    return {"groups": get_user_groups(current_user["id"])}


# ─── LMS Integration Endpoints ─────────────────────────────────────────────────

@app.get("/student/lms/universities")
@limiter.limit("30/minute")
def lms_universities(request: Request):
    """Liste les universités belges connues avec leurs URLs Moodle."""
    from api.features.lms import KNOWN_UNIVERSITIES
    return {"universities": KNOWN_UNIVERSITIES}


@app.post("/student/lms/connect")
@limiter.limit("5/minute")
def lms_connect(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Connecte l'étudiant à son Moodle. Stocke le token."""
    from api.features.lms import moodle_authenticate, get_site_info
    from api.database import save_lms_connection

    site_url = body.get("site_url", "").strip().rstrip("/")
    username = body.get("username", "").strip()
    password = body.get("password", "")
    platform = body.get("platform", "moodle")

    if not site_url or not username or not password:
        raise HTTPException(status_code=400, detail="URL, identifiant et mot de passe requis")

    try:
        token = moodle_authenticate(site_url, username, password)
        info = get_site_info(site_url, token)
        conn_data = save_lms_connection(
            user_id=current_user["id"],
            platform=platform,
            site_url=site_url,
            token=token,
            site_name=info.get("site_name", ""),
            user_fullname=info.get("user_fullname", ""),
            moodle_user_id=info.get("moodle_user_id"),
        )
        return {
            "connected": True,
            "site_name": info.get("site_name", ""),
            "user_fullname": info.get("user_fullname", ""),
            "platform": platform,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/connect error: {e}")
        raise HTTPException(status_code=500, detail="Erreur de connexion à la plateforme")


@app.get("/student/lms/status")
@limiter.limit("20/minute")
def lms_status(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Vérifie si l'étudiant a une connexion LMS active."""
    from api.database import get_lms_connection
    conn = get_lms_connection(current_user["id"])
    if conn:
        return {
            "connected": True,
            "platform": conn["platform"],
            "site_name": conn.get("site_name", ""),
            "user_fullname": conn.get("user_fullname", ""),
            "site_url": conn["site_url"],
        }
    return {"connected": False}


@app.get("/student/lms/courses")
@limiter.limit("10/minute")
def lms_courses(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Récupère les cours Moodle de l'étudiant."""
    from api.database import get_lms_connection, save_lms_course, get_lms_courses
    from api.features.lms import get_courses

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS. Connecte-toi d'abord.")

    try:
        courses = get_courses(conn["site_url"], conn["token"], conn.get("moodle_user_id"))
        # Cache les cours en DB
        for c in courses:
            save_lms_course(
                user_id=current_user["id"],
                connection_id=conn["id"],
                course_id=c["id"],
                course_name=c["name"],
                course_shortname=c.get("shortname", ""),
            )
        return {"courses": courses}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/courses error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des cours")


@app.get("/student/lms/course/{course_id}/content")
@limiter.limit("10/minute")
def lms_course_content(
    request: Request,
    course_id: int,
    current_user: dict = Depends(_get_current_user),
):
    """Récupère le contenu détaillé d'un cours (sections, modules, fichiers)."""
    from api.database import get_lms_connection
    from api.features.lms import get_course_content

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS")

    try:
        content = get_course_content(conn["site_url"], conn["token"], course_id)
        return {"course_id": course_id, "sections": content}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/student/lms/import")
@limiter.limit("5/minute")
def lms_import_content(
    request: Request,
    body: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Importe et extrait le texte d'un fichier Moodle pour alimenter les quiz/flashcards."""
    from api.database import get_lms_connection, save_lms_course
    from api.features.lms import download_and_extract

    conn = get_lms_connection(current_user["id"])
    if not conn:
        raise HTTPException(status_code=400, detail="Aucune connexion LMS")

    file_url = body.get("file_url", "")
    course_id = body.get("course_id")
    course_name = body.get("course_name", "Cours importé")

    if not file_url:
        raise HTTPException(status_code=400, detail="URL du fichier requise")

    try:
        text = download_and_extract(conn["site_url"], conn["token"], file_url)
        if course_id:
            save_lms_course(
                user_id=current_user["id"],
                connection_id=conn["id"],
                course_id=course_id,
                course_name=course_name,
                imported_content=text,
            )
        return {"imported": True, "content_length": len(text), "preview": text[:500]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"/student/lms/import error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'import")


@app.delete("/student/lms/disconnect")
@limiter.limit("5/minute")
def lms_disconnect(
    request: Request,
    current_user: dict = Depends(_get_current_user),
):
    """Déconnecte l'étudiant de son LMS."""
    from api.database import delete_lms_connection
    delete_lms_connection(current_user["id"])
    return {"disconnected": True}


# ─── SEO Routes ────────────────────────────────────────────────────────────────
from fastapi.templating import Jinja2Templates  # noqa: E402
from api.seo import router as seo_router
app.include_router(seo_router, tags=["SEO"])


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
