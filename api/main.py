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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
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
_ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _CORS_ORIGINS_ENV.split(",") if o.strip()]
    if _CORS_ORIGINS_ENV
    else [
        "http://localhost:8081",   # Expo web (dev)
        "http://localhost:19000",  # Expo Go (dev)
        "http://localhost:3000",   # Éventuel front web
        "exp://localhost:8081",    # Expo Go mobile (dev)
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
    if current_user["id"] != 1:
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
    """
    from rag.pipeline import ask
    from rag.indexer import CHROMA_DIR
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    # Vérifier que l'index est disponible avant de charger le modèle
    if not CHROMA_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail="Index ChromaDB non disponible sur ce serveur. Utilisez l'API locale avec l'index chargé.",
        )

    # Verifier le quota avant d'appeler Claude
    check_quota(current_user["id"])

    try:
        result = ask(
            question=body.question,
            top_k=body.top_k,
            source_filter=body.source_filter,
            model=body.model,
            anthropic_api_key=api_key,
            branch=body.branch,
            region=body.region,
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
        for s in result.get("sources", [])
    ]

    return AskResponse(
        answer=result["answer"],
        sources=sources,
        chunks_used=result["chunks_used"],
        model=result["model"],
        branch=result.get("branch"),
        branch_label=result.get("branch_label"),
        branch_confidence=result.get("branch_confidence", 0.0),
    )


@app.get("/branches")
def branches_list():
    """Liste les 15 branches du droit disponibles avec detection automatique."""
    from rag.branches import list_branches
    branches = list_branches()
    return {"branches": branches, "total": len(branches)}


@app.post("/search", response_model=SearchResponse)
def search_endpoint(request: SearchRequest):
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
            query=request.query,
            top_k=request.top_k,
            source_filter=request.source_filter,
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
        query=request.query,
        results=results,
        total=len(results),
    )


# ─── Auth Endpoints ──────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    """Inscription d'un nouvel utilisateur."""
    from api.auth import register_user
    result = register_user(
        email=request.email,
        password=request.password,
        name=request.name,
        language=request.language,
    )
    return AuthResponse(
        user=UserResponse(**result["user"]),
        token=result["token"],
        refresh_token=result.get("refresh_token"),
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest):
    """Connexion — retourne un JWT + refresh token."""
    from api.auth import login_user
    result = login_user(email=request.email, password=request.password)
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
def refresh_token_endpoint(request: dict):
    """Echange un refresh token contre un nouveau access token + nouveau refresh token."""
    from api.database import get_refresh_token, delete_refresh_token, save_refresh_token, get_user_by_id
    from api.auth import create_token, create_refresh_token, REFRESH_TOKEN_EXPIRY_DAYS

    rt = request.get("refresh_token", "")
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
    result = handle_webhook(payload, sig)
    return result


# ─── Shield Endpoints ─────────────────────────────────────────────────────

@app.post("/shield/analyze", response_model=ShieldAnalyzeResponse)
def shield_analyze(
    request: ShieldAnalyzeRequest,
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
            text=request.contract_text,
            contract_type=request.contract_type,
            region=request.region,
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
async def shield_upload(
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
def decode_analyze(
    request: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Traduit un document administratif en langage clair."""
    from api.features.decode import decode_document
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    text = request.get("document_text") or request.get("text", "")
    if len(text.strip()) < 20:
        raise HTTPException(400, "Le document est trop court.")

    check_quota(current_user["id"])
    result = decode_document(text=text)
    increment_question_count(current_user["id"])
    return result


@app.post("/decode/upload")
async def decode_upload(
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
def calc_notice(request: dict):
    """Calculateur de préavis de licenciement (CCT n 109)."""
    from api.features.calculators import calculate_notice_period
    years = int(request.get("years", 0))
    monthly_salary = float(request.get("monthly_salary", 0))
    if monthly_salary <= 0:
        raise HTTPException(400, "Salaire mensuel requis (> 0)")
    return calculate_notice_period(years=years, monthly_salary=monthly_salary)


@app.post("/calculators/alimony")
def calc_alimony(request: dict):
    """Calculateur de pension alimentaire (barème Renard)."""
    from api.features.calculators import calculate_alimony_renard
    income_high = float(request.get("income_high", 0))
    income_low = float(request.get("income_low", 0))
    children = int(request.get("children", 0))
    return calculate_alimony_renard(
        income_high=income_high, income_low=income_low, children=children
    )


@app.post("/calculators/succession")
def calc_succession(request: dict):
    """Calculateur de droits de succession par région."""
    from api.features.calculators import calculate_succession_duties
    region = request.get("region", "bruxelles")
    amount = float(request.get("amount", 0))
    relationship = request.get("relationship", "direct_line")
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
def diagnostic_analyze(
    request: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere un diagnostic personnalise a partir des reponses."""
    from api.features.diagnostic import generate_diagnostic
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    answers = request.get("answers", [])
    check_quota(current_user["id"])
    result = generate_diagnostic(answers=answers)
    increment_question_count(current_user["id"])
    return result


# ─── Score Endpoints ───────────────────────────────────────────────────────

@app.get("/score/questions")
def score_questions():
    """Retourne les 10 questions du Score de sante juridique."""
    from api.features.score import get_score_questions
    return {"questions": get_score_questions()}


@app.post("/score/evaluate")
def score_evaluate(request: dict):
    """Calcule le score de sante juridique."""
    from api.features.score import calculate_score
    answers = request.get("answers", [])
    return calculate_score(answers=answers)


# ─── Legal Response Endpoints ──────────────────────────────────────────────

@app.post("/response/generate")
def response_generate(
    request: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Genere une reponse a un courrier juridique recu."""
    from api.features.legal_response import generate_response
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    received_text = request.get("received_text", "")
    user_context = request.get("user_context")

    check_quota(current_user["id"])
    result = generate_response(received_text=received_text, user_context=user_context)
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
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Genere un contrat HTML rempli."""
    from api.features.contracts import generate_contract_html
    variables = request.get("variables", {})
    html = generate_contract_html(template_id=template_id, variables=variables)
    return {"html": html, "template_id": template_id}


# ─── Compliance Endpoints ──────────────────────────────────────────────────

@app.get("/compliance/questions")
def compliance_questions():
    """Retourne les 15 questions d'audit compliance."""
    from api.features.compliance import get_compliance_questions
    return {"questions": get_compliance_questions()}


@app.post("/compliance/audit")
def compliance_audit(
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Genere un rapport d'audit de conformite."""
    from api.features.compliance import generate_compliance_audit
    answers = request.get("answers", [])
    company_type = request.get("company_type", "independant")
    return generate_compliance_audit(answers=answers, company_type=company_type)


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
def audit_generate(
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
def defend_detect(request: dict):
    """Detecte automatiquement le type de situation."""
    from api.features.defend import detect_situation_type
    description = request.get("description", "")
    if len(description.strip()) < 10:
        raise HTTPException(400, "Description trop courte")
    return detect_situation_type(description)


@app.post("/defend/analyze", response_model=DefendResponse)
def defend_analyze(
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


# ─── Alerts Endpoints ─────────────────────────────────────────────────────

@app.get("/alerts/domains")
def alerts_domains():
    """Liste les domaines juridiques disponibles pour les alertes."""
    from api.features.alerts import get_alert_domains
    return {"domains": get_alert_domains()}


@app.post("/alerts/preferences")
def alerts_save_preferences(
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Sauvegarde les preferences d'alertes de l'utilisateur (persistees en DB)."""
    from api.database import update_alert_preferences
    domains = request.get("domains", [])
    frequency = request.get("frequency")
    enabled = request.get("enabled")
    prefs = update_alert_preferences(
        user_id=current_user["id"], domains=domains, frequency=frequency, enabled=enabled,
    )
    return prefs


@app.get("/alerts/feed")
def alerts_feed(
    current_user: dict = Depends(_get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Retourne le fil d'alertes legislatives personnalise selon les preferences DB."""
    from api.features.alerts import get_alert_feed
    from api.database import get_alert_preferences
    prefs = get_alert_preferences(current_user["id"])
    domains = prefs.get("domains", [])
    feed = get_alert_feed(domains=domains, limit=limit)
    return {"alerts": feed, "total": len(feed), "preferences": prefs}


# ─── Litigation Endpoints ─────────────────────────────────────────────────

@app.get("/litigation/stages")
def litigation_stages():
    """Liste les etapes du recouvrement d'impayes."""
    from api.features.litigation import get_stages
    return {"stages": get_stages()}


@app.post("/litigation/start")
def litigation_start(
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Demarre une procedure de recouvrement d'impaye."""
    from api.features.litigation import start_litigation
    try:
        result = start_litigation(
            creditor_name=request.get("creditor_name", ""),
            debtor_name=request.get("debtor_name", ""),
            amount=request.get("amount", 0),
            invoice_number=request.get("invoice_number", ""),
            due_date=request.get("due_date", ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Match Endpoints ─────────────────────────────────────────────────────

@app.post("/match/find")
def match_find(
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Trouve les avocats les mieux adaptes a la situation."""
    from api.features.match import find_matching_lawyers
    try:
        result = find_matching_lawyers(
            description=request.get("description", ""),
            city=request.get("city"),
            language=request.get("language", "fr"),
            budget=request.get("budget"),
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
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Cree une demande d'assistance juridique urgente (49 EUR)."""
    from api.features.emergency import create_emergency_request
    try:
        result = create_emergency_request(
            user_id=current_user["id"],
            category=request.get("category", "autre"),
            description=request.get("description", ""),
            phone=request.get("phone", ""),
            city=request.get("city", ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Proof Endpoints ─────────────────────────────────────────────────────

@app.post("/proof/create")
def proof_create(
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """Cree un nouveau dossier de preuves (persiste en DB)."""
    from api.database import create_proof_case
    title = request.get("title", "")
    if not title or len(title.strip()) < 3:
        raise HTTPException(400, "Le titre du dossier doit contenir au moins 3 caracteres.")
    result = create_proof_case(
        user_id=current_user["id"],
        title=title.strip(),
        description=request.get("description", ""),
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
    request: dict,
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
        entry_type=request.get("type", "note"),
        content=request.get("content", ""),
        metadata=request.get("metadata"),
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
def heritage_guide(request: dict):
    """Genere un guide succession personnalise par region."""
    from api.features.heritage import generate_heritage_guide
    try:
        result = generate_heritage_guide(
            region=request.get("region", ""),
            relationship=request.get("relationship", "direct_line"),
            has_testament=request.get("has_testament", False),
            has_real_estate=request.get("has_real_estate", False),
            estimated_value=request.get("estimated_value", 0),
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Fiscal Endpoints ────────────────────────────────────────────────────

@app.post("/fiscal/ask")
def fiscal_ask(
    request: dict,
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Copilote fiscal — repond aux questions TVA et impots."""
    from api.features.fiscal import ask_fiscal
    from api.stripe_billing import check_quota
    from api.database import increment_question_count

    question = request.get("question", "")
    check_quota(current_user["id"])
    try:
        result = ask_fiscal(question=question)
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
def newsletter_subscribe(request: dict):
    """
    POST /newsletter/subscribe
    Body : { "email": "...", "domains": ["travail", "fiscal"] }
    Inscrit l'email à la newsletter hebdomadaire.
    """
    from api.database import subscribe_newsletter
    import re

    email = request.get("email", "").strip().lower()
    domains = request.get("domains", [])

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
    request: dict,
    current_user: dict = Depends(_get_current_user),
):
    """
    POST /notifications/register
    Enregistre le token push Expo d'un appareil.
    Body : { "token": "ExponentPushToken[...]" }
    """
    from api.database import save_push_token

    token = request.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token push manquant.")

    save_push_token(user_id=current_user["id"], token=token)
    return {"status": "registered", "token": token}


@app.post("/notifications/preferences")
def notifications_preferences(
    request: dict,
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

    token       = request.get("token", "").strip()
    preferences = request.get("preferences", {})

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
