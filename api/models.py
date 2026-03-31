"""Modèles Pydantic pour l'API App Droit Belgique."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ─── Auth models ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Corps de la requête POST /auth/register."""
    email: str = Field(..., description="Adresse email")
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")
    name: str = Field(..., min_length=2, description="Nom complet")
    language: str = Field(default="fr", description="Langue : fr, nl, en")


class LoginRequest(BaseModel):
    """Corps de la requête POST /auth/login."""
    email: str = Field(..., description="Adresse email")
    password: str = Field(..., description="Mot de passe")


class UserResponse(BaseModel):
    """Profil utilisateur (sans mot de passe)."""
    id: int
    email: str
    name: str
    language: str
    created_at: str


class AuthResponse(BaseModel):
    """Réponse d'authentification (register/login)."""
    user: UserResponse
    token: str


# ─── Lawyer models ──────────────────────────────────────────────────────────

class LawyerResponse(BaseModel):
    """Profil d'un avocat."""
    id: int
    name: str
    bar: str
    specialties: List[str]
    email: Optional[str] = None
    phone: Optional[str] = None
    city: str
    description: Optional[str] = None
    rating: float
    verified: bool
    created_at: str


class LawyerListResponse(BaseModel):
    """Liste d'avocats."""
    lawyers: List[LawyerResponse]
    total: int


# ─── Conversation models ────────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    """Corps de la requête POST /conversations."""
    title: str = Field(..., min_length=1, max_length=200, description="Titre de la conversation")


class ConversationResponse(BaseModel):
    """Une conversation."""
    id: int
    user_id: int
    title: str
    created_at: str


class ConversationListResponse(BaseModel):
    """Liste de conversations."""
    conversations: List[ConversationResponse]
    total: int


# ─── Message models ─────────────────────────────────────────────────────────

class CreateMessageRequest(BaseModel):
    """Corps de la requête POST /conversations/{id}/messages."""
    role: str = Field(..., description="Role : user ou assistant")
    content: str = Field(..., min_length=1, description="Contenu du message")
    sources_json: Optional[str] = Field(default="[]", description="Sources JSON (pour les réponses assistant)")


class MessageResponse(BaseModel):
    """Un message dans une conversation."""
    id: int
    conversation_id: int
    role: str
    content: str
    sources_json: Any = []  # parsed JSON (list or dict)
    created_at: str


class MessageListResponse(BaseModel):
    """Liste de messages."""
    messages: List[MessageResponse]
    total: int


class AskRequest(BaseModel):
    """Corps de la requete POST /ask."""
    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Question juridique en francais, neerlandais ou anglais",
        examples=["Quelles sont les conditions d'un licenciement pour motif grave ?"],
    )
    source_filter: Optional[List[str]] = Field(
        default=None,
        description="Filtrer par source : ['HUDOC', 'EUR-Lex', 'Juridat', 'Moniteur belge']",
    )
    top_k: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Nombre de documents sources a consulter",
    )
    model: str = Field(
        default="claude-sonnet-4-6",
        description="Modele Claude a utiliser",
    )
    branch: Optional[str] = Field(
        default=None,
        description="Branche du droit a forcer (ex: droit_travail, droit_fiscal). Si absent, detection automatique.",
    )
    region: Optional[str] = Field(
        default=None,
        description="Region belge de l'utilisateur : bruxelles, wallonie, flandre. Permet de prioriser le droit regional applicable.",
    )


class SourceDoc(BaseModel):
    """Document source cité dans la réponse."""
    doc_id: str
    source: str
    title: str
    date: str
    ecli: str
    url: str
    similarity: float


class AskResponse(BaseModel):
    """Reponse de l'endpoint /ask."""
    answer: str = Field(description="Reponse juridique en langage naturel")
    sources: List[SourceDoc] = Field(description="Documents sources utilises")
    chunks_used: int = Field(description="Nombre de passages contextuels")
    model: str = Field(description="Modele Claude utilise")
    branch: Optional[str] = Field(default=None, description="Branche du droit detectee")
    branch_label: Optional[str] = Field(default=None, description="Label de la branche (ex: Droit du travail)")
    branch_confidence: float = Field(default=0.0, description="Confiance de la detection (0.0 a 1.0)")


class SearchRequest(BaseModel):
    """Corps de la requête POST /search (recherche seule, sans LLM)."""
    query: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    source_filter: Optional[List[str]] = None


class SearchResult(BaseModel):
    """Un résultat de recherche vectorielle."""
    doc_id: str
    source: str
    doc_type: str
    jurisdiction: str
    title: str
    date: str
    url: str
    ecli: str
    chunk_text: str
    similarity: float
    score: float


class SearchResponse(BaseModel):
    """Réponse de l'endpoint /search."""
    query: str
    results: List[SearchResult]
    total: int


class IndexStats(BaseModel):
    """Statistiques de l'index."""
    status: str
    collection: Optional[str] = None
    total_chunks: int
    total_documents: int = 0
    sources: Optional[dict] = None
    chroma_dir: Optional[str] = None
    error: Optional[str] = None


# ─── Billing / Stripe models ──────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    """Corps de la requete POST /billing/checkout."""
    plan: str = Field(..., description="Plan choisi : basic, pro, business, firm_s, firm_m")
    billing: str = Field(default="monthly", description="Frequence : monthly ou annual")


class CheckoutResponse(BaseModel):
    """Reponse du checkout — URL de paiement Stripe."""
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Reponse du portail client Stripe."""
    portal_url: str


class SubscriptionResponse(BaseModel):
    """Etat de l'abonnement utilisateur."""
    plan: str
    status: str
    questions_used: int
    questions_limit: int = Field(description="-1 = illimite")
    questions_remaining: Optional[int] = None
    current_period_end: Optional[str] = None
    beta: bool = Field(default=False, description="True si periode beta active")
    beta_end: Optional[str] = Field(default=None, description="Date de fin de beta (YYYY-MM-DD)")


class PlanInfo(BaseModel):
    """Info sur un plan tarifaire."""
    key: str
    label: str
    subtitle: str = ""
    price_monthly: float = Field(description="-1 = sur devis, 0 = gratuit")
    price_annual: Optional[float] = Field(default=None, description="Prix annuel (2 mois offerts)")
    founding_price: Optional[float] = Field(default=None, description="Prix Founding Member (beta)")
    max_users: int = Field(default=1, description="-1 = illimite")
    questions_per_month: int = Field(description="-1 = illimite")
    features: List[str]


class PlansResponse(BaseModel):
    """Liste des plans disponibles."""
    plans: List[PlanInfo]
    beta_active: bool = False
    beta_end: Optional[str] = None


# ─── Shield models ───────────────────────────────────────────────────────

class ShieldClause(BaseModel):
    """Une clause analysée par Shield."""
    clause_text: str = Field(description="Texte de la clause")
    status: str = Field(description="green, orange, ou red")
    explanation: str = Field(description="Explication en langage clair")
    legal_basis: Optional[str] = Field(default=None, description="Article de loi applicable")


class ShieldAnalyzeRequest(BaseModel):
    """Requête d'analyse Shield (texte brut)."""
    contract_text: str = Field(..., min_length=50, max_length=50000, description="Texte du contrat")
    contract_type: Optional[str] = Field(default=None, description="Type: bail, travail, vente, general")


class ShieldAnalyzeResponse(BaseModel):
    """Résultat d'analyse Shield."""
    verdict: str = Field(description="green, orange, ou red — verdict global")
    summary: str = Field(description="Résumé en 2-3 phrases")
    clauses: List[ShieldClause] = Field(description="Analyse clause par clause")
    contract_type_detected: Optional[str] = Field(default=None, description="Type de contrat détecté")
    legal_sources: List[SourceDoc] = Field(default=[], description="Sources juridiques utilisées")
    disclaimer: str = Field(
        default="Outil d'information juridique. Ne remplace pas un avis professionnel.",
        description="Disclaimer légal obligatoire"
    )


class ShieldUploadResponse(BaseModel):
    """Résultat d'analyse Shield via upload fichier."""
    extracted_text: str = Field(description="Texte extrait du document")
    analysis: ShieldAnalyzeResponse = Field(description="Analyse du contrat")
