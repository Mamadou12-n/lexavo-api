# Lexavo — Plan d'implémentation des 15+ features

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter les 15 fonctionnalités Lexavo + optimisations (model-recommendation, SEO programmatique, NotebookLM) sur la base technique existante (RAG + FastAPI + Expo).

**Architecture:** Chaque feature ajoute : (1) endpoint(s) FastAPI dans un module dédié, (2) modèles Pydantic, (3) table(s) SQLite si nécessaire, (4) écran React Native, (5) tests pytest. Les features réutilisent le pipeline RAG existant (43 429 chunks, ChromaDB, Claude Sonnet 4.6) et le système auth/billing Stripe en place.

**Tech Stack:** FastAPI, SQLite, ChromaDB, Anthropic Claude API, pytesseract (OCR), WeasyPrint (PDF), Stripe, React Native/Expo, pytest.

**Disclaimer légal obligatoire sur chaque feature:** *"Outil d'information juridique. Ne remplace pas un avis professionnel. En cas de doute, consultez un avocat."*

---

## Structure des fichiers — Vue d'ensemble

```
base-juridique-app/
├── api/
│   ├── main.py                    # Modifier: importer les nouveaux routers
│   ├── models.py                  # Modifier: ajouter les nouveaux modèles
│   ├── database.py                # Modifier: ajouter les nouvelles tables
│   ├── features/                  # NOUVEAU: un module par feature
│   │   ├── __init__.py
│   │   ├── shield.py              # Feature #1: analyse de contrats
│   │   ├── calculators.py         # Feature #2: calculateurs de droits
│   │   ├── contracts.py           # Feature #3: bibliothèque de contrats
│   │   ├── legal_response.py      # Feature #4: générateur de réponses
│   │   ├── diagnostic.py          # Feature #5: diagnostic juridique
│   │   ├── score.py               # Feature #6: score de santé juridique
│   │   ├── compliance.py          # Feature #7: audit compliance B2B
│   │   ├── alerts.py              # Feature #8: alertes législatives
│   │   ├── decode.py              # Feature #9: traducteur documents État
│   │   ├── litigation.py          # Feature #10: recouvrement impayés
│   │   ├── match.py               # Feature #11: mise en relation avocats
│   │   ├── emergency.py           # Feature #12: bouton rouge urgence
│   │   ├── proof.py               # Feature #13: construire son dossier
│   │   ├── heritage.py            # Feature #14: guide succession
│   │   └── fiscal.py              # Feature #15: copilote fiscal
│   └── utils/
│       ├── __init__.py
│       ├── ocr.py                 # OCR partagé (Shield + Decode)
│       ├── pdf_gen.py             # Génération PDF (Contrats + Rapports)
│       └── model_router.py        # model-recommendation (Haiku/Sonnet/Opus)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures pytest (client, auth, db)
│   ├── test_shield.py
│   ├── test_calculators.py
│   ├── test_contracts.py
│   ├── test_diagnostic.py
│   ├── test_score.py
│   ├── test_compliance.py
│   ├── test_alerts.py
│   ├── test_decode.py
│   ├── test_litigation.py
│   ├── test_match.py
│   ├── test_emergency.py
│   ├── test_proof.py
│   ├── test_heritage.py
│   └── test_fiscal.py
├── mobile/src/screens/
│   ├── ShieldScreen.js
│   ├── CalculatorScreen.js
│   ├── ContractsScreen.js
│   ├── DiagnosticScreen.js
│   ├── ScoreScreen.js
│   ├── ComplianceScreen.js
│   ├── DecodeScreen.js
│   ├── ProofScreen.js
│   └── HeritageScreen.js
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-03-31-lexavo-master-plan.md  # Ce fichier
```

---

## Vagues d'implémentation

### WAVE 1 — Moteur OCR + RAG (Feature #1, #9)
Shield et Decode partagent le même pipeline : OCR → texte → RAG → analyse Claude.
Construire Shield d'abord, Decode est une variation du même code.

### WAVE 2 — Logique pure, zéro API (Feature #2, #6)
Calculateurs et Score sont des formules mathématiques + scoring pondéré.
Aucun appel API Anthropic → 100% gratuit en fonctionnement.

### WAVE 3 — Questionnaires + RAG (Feature #5, #7, #14)
Diagnostic, Compliance et Héritage suivent le pattern : questionnaire → prompt → rapport.

### WAVE 4 — Documents + PDF (Feature #3, #4, #10)
Contrats, Réponses juridiques et Litiges Pro génèrent des documents PDF.

### WAVE 5 — Écosystème (Feature #8, #11, #12, #13, #15)
Alertes, Match, Emergency, Proof, Fiscal — fonctionnalités de rétention.

---

## Pré-requis : Fondations communes

### Task 0: Fixtures de test + module features + utilitaires partagés

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `api/features/__init__.py`
- Create: `api/utils/__init__.py`
- Create: `api/utils/ocr.py`
- Create: `api/utils/pdf_gen.py`
- Create: `api/utils/model_router.py`

- [ ] **Step 1: Créer le fichier de fixtures pytest**

```python
# tests/conftest.py
import pytest
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api.database import init_db, create_user
from api.auth import create_token


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialise la DB de test."""
    os.environ.setdefault("LEXAVO_JWT_SECRET", "test-secret-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    init_db()
    yield


@pytest.fixture
def client():
    """Client FastAPI pour les tests."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers avec JWT valide pour un utilisateur de test."""
    user = create_user(
        email=f"test_{os.urandom(4).hex()}@lexavo.be",
        password_hash="fakehash",
        name="Test User",
        language="fr",
    )
    token = create_token(user["id"])
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Créer le module utilitaire OCR**

```python
# api/utils/ocr.py
"""OCR partagé pour Shield et Decode — pytesseract."""

import io
from typing import Optional


def extract_text_from_image(image_bytes: bytes, lang: str = "fra+nld") -> str:
    """Extrait le texte d'une image via pytesseract.

    Args:
        image_bytes: Contenu binaire de l'image
        lang: Langues Tesseract (fra+nld pour français+néerlandais)

    Returns:
        Texte extrait, nettoyé
    """
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "pytesseract et Pillow sont requis. "
            "Installez : pip install pytesseract Pillow"
        )

    image = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(image, lang=lang)
    # Nettoyer : supprimer lignes vides multiples
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    return "\n".join(lines)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF.

    Tente d'abord l'extraction directe (PDF texte),
    puis OCR si le PDF est scanné (images).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF est requis. Installez : pip install PyMuPDF")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []

    for page in doc:
        text = page.get_text().strip()
        if text:
            text_parts.append(text)
        else:
            # Page scannée → OCR
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            text_parts.append(extract_text_from_image(img_bytes))

    doc.close()
    return "\n\n".join(text_parts)
```

- [ ] **Step 3: Créer le module PDF generator**

```python
# api/utils/pdf_gen.py
"""Génération de PDF pour contrats et rapports — WeasyPrint."""

from typing import Optional


def generate_pdf(html_content: str, title: str = "Lexavo") -> bytes:
    """Génère un PDF à partir de HTML.

    Args:
        html_content: Contenu HTML à convertir
        title: Titre du document

    Returns:
        Contenu binaire du PDF
    """
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint est requis. Installez : pip install weasyprint")

    styled_html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Helvetica', 'Arial', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #1C2B3A;
                margin: 40px;
            }}
            h1 {{ color: #E85D26; font-size: 18pt; }}
            h2 {{ color: #1C2B3A; font-size: 14pt; border-bottom: 1px solid #E4E4E7; padding-bottom: 4px; }}
            .disclaimer {{
                background: #FFF3EE;
                border-left: 3px solid #E85D26;
                padding: 12px 16px;
                font-size: 9pt;
                color: #71717A;
                margin-top: 30px;
            }}
            .footer {{
                text-align: center;
                font-size: 8pt;
                color: #A1A1AA;
                margin-top: 40px;
            }}
        </style>
    </head>
    <body>
        {html_content}
        <div class="disclaimer">
            Outil d'information juridique. Ne remplace pas un avis professionnel.
            En cas de doute, consultez un avocat.
        </div>
        <div class="footer">Généré par Lexavo — lexavo.be</div>
    </body>
    </html>
    """
    pdf_bytes = HTML(string=styled_html).write_pdf()
    return pdf_bytes
```

- [ ] **Step 4: Créer le model router (Haiku/Sonnet/Opus)**

```python
# api/utils/model_router.py
"""Routage intelligent des modèles Claude — optimisation coûts.

Haiku  → questions simples, calculateurs (80% moins cher)
Sonnet → analyses, diagnostics, RAG standard
Opus   → cas complexes, contrats multi-clauses
"""


def select_model(task_type: str, text_length: int = 0) -> str:
    """Sélectionne le modèle optimal selon la tâche.

    Args:
        task_type: Type de tâche (calculator, simple_qa, analysis,
                   contract, diagnostic, complex)
        text_length: Longueur du texte à analyser (en caractères)

    Returns:
        ID du modèle Claude à utiliser
    """
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-6"
    OPUS = "claude-opus-4-6"

    routing = {
        "calculator": HAIKU,      # Formules mathématiques
        "simple_qa": HAIKU,       # Questions courtes
        "translation": HAIKU,     # Decode documents simples
        "analysis": SONNET,       # Analyse juridique standard
        "diagnostic": SONNET,     # Diagnostic complet
        "contract": SONNET,       # Analyse de contrat
        "complex": OPUS,          # Cas multi-branches complexes
    }

    model = routing.get(task_type, SONNET)

    # Upgrader si le texte est très long (contrat > 5000 chars)
    if task_type == "contract" and text_length > 15000:
        model = OPUS

    return model
```

- [ ] **Step 5: Créer les __init__.py**

```python
# api/features/__init__.py
"""Modules features Lexavo — un fichier par fonctionnalité."""

# api/utils/__init__.py
"""Utilitaires partagés entre features."""

# tests/__init__.py
```

- [ ] **Step 6: Vérifier que les tests de base passent**

Run: `cd C:/Users/bahma/Downloads/base-juridique-app && pip install pytest httpx && python -m pytest tests/ -v --tb=short 2>&1 | head -30`
Expected: Session collected, 0 tests (pas encore de tests)

- [ ] **Step 7: Commit fondations**

```bash
git add tests/ api/features/ api/utils/
git commit -m "feat: add test fixtures, features module, and shared utilities (OCR, PDF, model router)"
```

---

## WAVE 1 — Feature #1 : Lexavo Shield

### Task 1: Modèles Pydantic Shield

**Files:**
- Modify: `api/models.py` (ajouter en fin de fichier)

- [ ] **Step 1: Ajouter les modèles Shield à models.py**

```python
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
```

- [ ] **Step 2: Commit modèles**

```bash
git add api/models.py
git commit -m "feat(shield): add Pydantic models for contract analysis"
```

### Task 2: Table shield_analyses en DB

**Files:**
- Modify: `api/database.py`

- [ ] **Step 1: Ajouter la table shield_analyses dans init_db()**

Ajouter après la création de la table `subscriptions` :

```python
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shield_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contract_type TEXT,
                verdict TEXT NOT NULL,
                summary TEXT NOT NULL,
                clauses_json TEXT NOT NULL DEFAULT '[]',
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shield_user
            ON shield_analyses(user_id)
        """)
```

- [ ] **Step 2: Ajouter les fonctions CRUD Shield**

```python
def save_shield_analysis(user_id: int, contract_type: str, verdict: str,
                         summary: str, clauses_json: str, sources_json: str) -> dict:
    """Sauvegarde une analyse Shield."""
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO shield_analyses (user_id, contract_type, verdict, summary, clauses_json, sources_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, contract_type, verdict, summary, clauses_json, sources_json),
    )
    conn.commit()
    row_id = cursor.lastrowid
    return get_shield_analysis(row_id)


def get_shield_analysis(analysis_id: int) -> Optional[dict]:
    """Récupère une analyse Shield par ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM shield_analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def list_shield_analyses(user_id: int, limit: int = 20) -> list:
    """Liste les analyses Shield d'un utilisateur."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM shield_analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 3: Commit DB**

```bash
git add api/database.py
git commit -m "feat(shield): add shield_analyses table and CRUD functions"
```

### Task 3: Logique métier Shield

**Files:**
- Create: `api/features/shield.py`

- [ ] **Step 1: Écrire le test Shield**

```python
# tests/test_shield.py
import pytest
from api.features.shield import analyze_contract_text


def test_analyze_contract_returns_verdict():
    """Shield retourne un verdict (green/orange/red)."""
    # Texte minimal d'un bail belge
    text = """
    CONTRAT DE BAIL DE RÉSIDENCE PRINCIPALE

    Entre les soussignés :
    Le bailleur : M. Dupont, domicilié à 1000 Bruxelles
    Le preneur : M. Martin, domicilié à 1050 Ixelles

    Article 1 - Objet
    Le bailleur donne en location l'appartement situé au
    Rue de la Loi 15, 1000 Bruxelles.

    Article 2 - Durée
    Le bail est conclu pour une durée de 9 ans.

    Article 3 - Loyer
    Le loyer mensuel est fixé à 850 euros.
    """
    # Ne teste que la structure, pas le contenu exact
    # (dépend de l'API Claude qui ne tourne pas en test)
    # On mocke l'appel Claude
    result = analyze_contract_text(text, mock=True)
    assert result["verdict"] in ("green", "orange", "red")
    assert len(result["summary"]) > 10
    assert isinstance(result["clauses"], list)


def test_analyze_detects_contract_type():
    """Shield détecte le type de contrat (bail, travail, etc.)."""
    text = "CONTRAT DE TRAVAIL à durée indéterminée entre l'employeur..."
    result = analyze_contract_text(text, mock=True)
    assert result["contract_type_detected"] in (
        "travail", "bail", "vente", "general", None
    )


def test_analyze_rejects_short_text():
    """Shield rejette un texte trop court."""
    with pytest.raises(ValueError, match="trop court"):
        analyze_contract_text("texte court", mock=True)
```

- [ ] **Step 2: Vérifier que les tests échouent**

Run: `cd C:/Users/bahma/Downloads/base-juridique-app && python -m pytest tests/test_shield.py -v`
Expected: FAIL (module api.features.shield n'existe pas encore)

- [ ] **Step 3: Implémenter shield.py**

```python
# api/features/shield.py
"""Lexavo Shield — Analyse de contrats avant signature.

Feu tricolore : vert (signe) / orange (attention) / rouge (clause illégale).
Pipeline : texte → détection type → RAG (lois applicables) → Claude → verdict.
"""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("shield")

# Patterns pour détecter le type de contrat
CONTRACT_PATTERNS = {
    "bail": r"(?i)\b(bail|bailleur|preneur|loyer|locataire|résidence principale)\b",
    "travail": r"(?i)\b(contrat de travail|employeur|travailleur|salaire|licenciement|préavis)\b",
    "vente": r"(?i)\b(contrat de vente|vendeur|acheteur|prix de vente|bien vendu)\b",
}


def detect_contract_type(text: str) -> str:
    """Détecte le type de contrat par mots-clés."""
    scores = {}
    for ctype, pattern in CONTRACT_PATTERNS.items():
        matches = re.findall(pattern, text)
        scores[ctype] = len(matches)
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


# Mapping type → branche du droit pour le RAG
TYPE_TO_BRANCH = {
    "bail": "droit_immobilier",
    "travail": "droit_travail",
    "vente": "droit_civil",
    "general": None,
}


SHIELD_SYSTEM_PROMPT = """Tu es Lexavo Shield, un outil d'analyse de contrats belges.

MISSION : Analyser chaque clause du contrat et attribuer un feu tricolore :
- 🟢 VERT : La clause est conforme au droit belge
- 🟠 ORANGE : La clause mérite attention (ambiguë, inhabituelle, désavantageuse)
- 🔴 ROUGE : La clause contient un élément contraire à une disposition légale impérative

RÈGLES STRICTES :
1. Tu fournis de l'INFORMATION JURIDIQUE, pas un conseil juridique
2. Cite TOUJOURS l'article de loi applicable quand tu identifies un problème
3. Formule : "L'article X prévoit que..." et NON "vous devez..." ou "je vous conseille..."
4. Si tu n'es pas sûr, classe en ORANGE avec explication
5. Réponds UNIQUEMENT en JSON valide

FORMAT DE RÉPONSE (JSON strict) :
{
  "verdict": "green|orange|red",
  "summary": "Résumé en 2-3 phrases du contrat",
  "clauses": [
    {
      "clause_text": "Le texte exact de la clause",
      "status": "green|orange|red",
      "explanation": "Explication claire en langage simple",
      "legal_basis": "Article X de la Loi du DD/MM/YYYY"
    }
  ]
}

Le verdict global est : ROUGE si au moins une clause est rouge, ORANGE si au moins une est orange, VERT si toutes sont vertes."""


def analyze_contract_text(
    text: str,
    contract_type: Optional[str] = None,
    mock: bool = False,
) -> dict:
    """Analyse un contrat et retourne le verdict Shield.

    Args:
        text: Texte du contrat
        contract_type: Type forcé (bail, travail, vente, general)
        mock: Si True, retourne un résultat factice (pour tests)

    Returns:
        Dict avec verdict, summary, clauses, contract_type_detected, sources
    """
    if len(text.strip()) < 50:
        raise ValueError("Le texte du contrat est trop court (minimum 50 caractères)")

    # Détecter le type
    detected_type = contract_type or detect_contract_type(text)

    if mock:
        return {
            "verdict": "orange",
            "summary": "Contrat analysé en mode test.",
            "clauses": [
                {
                    "clause_text": "Clause de test",
                    "status": "green",
                    "explanation": "Clause conforme (test)",
                    "legal_basis": None,
                }
            ],
            "contract_type_detected": detected_type,
            "sources": [],
        }

    # RAG : récupérer les lois pertinentes
    from rag.retriever import retrieve
    branch = TYPE_TO_BRANCH.get(detected_type)
    source_filter = None
    if branch:
        from rag.branches import BRANCHES
        branch_config = BRANCHES.get(branch, {})
        source_filter = branch_config.get("source_filter")

    chunks = retrieve(
        query=f"clauses illégales contrat {detected_type} droit belge",
        top_k=8,
        source_filter=source_filter,
    )

    context = "\n\n---\n\n".join(
        f"[{c.get('source', '')} — {c.get('title', '')}]\n{c.get('chunk_text', '')}"
        for c in chunks
    )

    # Appel Claude
    from api.utils.model_router import select_model
    import anthropic

    model = select_model("contract", len(text))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SHIELD_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"CONTRAT À ANALYSER (type détecté : {detected_type}) :\n\n"
                    f"{text}\n\n"
                    f"---\n\nSOURCES JURIDIQUES BELGES PERTINENTES :\n\n{context}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Extraire le JSON de la réponse
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = {
            "verdict": "orange",
            "summary": raw[:200],
            "clauses": [],
        }

    result["contract_type_detected"] = detected_type
    result["sources"] = [
        {
            "doc_id": c.get("doc_id", ""),
            "source": c.get("source", ""),
            "title": c.get("title", ""),
            "date": c.get("date", ""),
            "ecli": c.get("ecli", ""),
            "url": c.get("url", ""),
            "similarity": c.get("similarity", 0.0),
        }
        for c in chunks[:5]
    ]

    return result
```

- [ ] **Step 4: Vérifier que les tests passent**

Run: `cd C:/Users/bahma/Downloads/base-juridique-app && python -m pytest tests/test_shield.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit logique Shield**

```bash
git add api/features/shield.py tests/test_shield.py
git commit -m "feat(shield): implement contract analysis with RAG + Claude + traffic light verdict"
```

### Task 4: Endpoints API Shield

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Écrire les tests endpoint**

```python
# tests/test_shield_endpoint.py
import pytest
from fastapi.testclient import TestClient


def test_shield_analyze_text(client, auth_headers):
    """POST /shield/analyze retourne une analyse."""
    resp = client.post(
        "/shield/analyze",
        json={
            "contract_text": "CONTRAT DE BAIL DE RÉSIDENCE PRINCIPALE. "
                "Le bailleur donne en location l'appartement situé au "
                "Rue de la Loi 15, 1000 Bruxelles. Le bail est conclu "
                "pour une durée de 9 ans. Le loyer mensuel est fixé à 850 euros.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("green", "orange", "red")
    assert "clauses" in data
    assert "disclaimer" in data


def test_shield_requires_auth(client):
    """POST /shield/analyze sans auth → 401/403."""
    resp = client.post(
        "/shield/analyze",
        json={"contract_text": "Contrat de test " * 10},
    )
    assert resp.status_code in (401, 403)


def test_shield_history(client, auth_headers):
    """GET /shield/history retourne les analyses précédentes."""
    resp = client.get("/shield/history", headers=auth_headers)
    assert resp.status_code == 200
    assert "analyses" in resp.json()
```

- [ ] **Step 2: Ajouter les endpoints dans main.py**

Ajouter après les Billing Endpoints :

```python
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
    import json

    check_quota(current_user["id"])

    result = analyze_contract_text(
        text=request.contract_text,
        contract_type=request.contract_type,
    )

    increment_question_count(current_user["id"])

    save_shield_analysis(
        user_id=current_user["id"],
        contract_type=result.get("contract_type_detected", "general"),
        verdict=result["verdict"],
        summary=result["summary"],
        clauses_json=json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=json.dumps(result.get("sources", []), ensure_ascii=False),
    )

    sources = [SourceDoc(**s) for s in result.get("sources", [])]

    return ShieldAnalyzeResponse(
        verdict=result["verdict"],
        summary=result["summary"],
        clauses=[ShieldClause(**c) for c in result.get("clauses", [])],
        contract_type_detected=result.get("contract_type_detected"),
        legal_sources=sources,
    )


@app.get("/shield/history")
def shield_history(current_user: dict = Depends(_get_current_user)):
    """Historique des analyses Shield de l'utilisateur."""
    from api.database import list_shield_analyses
    import json

    analyses = list_shield_analyses(current_user["id"])
    for a in analyses:
        a["clauses"] = json.loads(a.get("clauses_json", "[]"))
        a["sources"] = json.loads(a.get("sources_json", "[]"))
    return {"analyses": analyses, "total": len(analyses)}
```

- [ ] **Step 3: Ajouter les imports ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldClause dans main.py**

Modifier la section d'imports en haut de main.py pour inclure :
```python
from api.models import (
    # ... imports existants ...
    ShieldAnalyzeRequest, ShieldAnalyzeResponse, ShieldClause, ShieldUploadResponse,
)
```

- [ ] **Step 4: Tester les endpoints**

Run: `cd C:/Users/bahma/Downloads/base-juridique-app && python -m pytest tests/test_shield_endpoint.py -v`

- [ ] **Step 5: Commit endpoints**

```bash
git add api/main.py tests/test_shield_endpoint.py
git commit -m "feat(shield): add /shield/analyze and /shield/history endpoints"
```

### Task 5: Upload fichier Shield (OCR)

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Ajouter l'endpoint upload**

```python
from fastapi import UploadFile, File

@app.post("/shield/upload", response_model=ShieldUploadResponse)
async def shield_upload(
    file: UploadFile = File(..., description="Contrat PDF ou image (JPG/PNG)"),
    api_key: str = Depends(get_api_key),
    current_user: dict = Depends(_get_current_user),
):
    """Upload un contrat (PDF/image) → OCR → analyse Shield."""
    from api.utils.ocr import extract_text_from_image, extract_text_from_pdf
    from api.features.shield import analyze_contract_text
    from api.database import save_shield_analysis, increment_question_count
    from api.stripe_billing import check_quota
    import json

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
        clauses_json=json.dumps(result.get("clauses", []), ensure_ascii=False),
        sources_json=json.dumps(result.get("sources", []), ensure_ascii=False),
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
```

- [ ] **Step 2: Commit upload endpoint**

```bash
git add api/main.py
git commit -m "feat(shield): add /shield/upload endpoint with OCR (PDF + image)"
```

---

## WAVE 1 — Feature #9 : Lexavo Decode

### Task 6: Decode (réutilise le pipeline Shield)

**Files:**
- Create: `api/features/decode.py`
- Create: `tests/test_decode.py`
- Modify: `api/main.py`

- [ ] **Step 1: Écrire le test**

```python
# tests/test_decode.py
import pytest
from api.features.decode import decode_document


def test_decode_returns_plain_language():
    """Decode traduit un document admin en langage clair."""
    text = """
    AVIS D'IMPOSITION - EXERCICE D'IMPOSITION 2025
    SPF FINANCES - Administration générale de la Fiscalité

    Conformément aux articles 359 et suivants du CIR 1992,
    le revenu imposable globalement s'élève à 45.000,00 EUR.
    La quotité exemptée d'impôt est fixée à 10.160,00 EUR
    (art. 131 CIR 1992).
    """
    result = decode_document(text, mock=True)
    assert "plain_language" in result
    assert len(result["plain_language"]) > 20
    assert "key_points" in result


def test_decode_rejects_empty():
    with pytest.raises(ValueError):
        decode_document("", mock=True)
```

- [ ] **Step 2: Implémenter decode.py**

```python
# api/features/decode.py
"""Lexavo Decode — Traducteur de documents d'État en langage clair."""

import json
import os
import re
import logging
from typing import Optional

log = logging.getLogger("decode")

DECODE_PROMPT = """Tu es Lexavo Decode, un traducteur de documents administratifs belges.

MISSION : Traduire un document officiel (SPF, ONSS, commune, CPAS, etc.)
en langage simple qu'un citoyen belge sans formation juridique peut comprendre.

FORMAT DE RÉPONSE (JSON strict) :
{
  "plain_language": "Explication claire du document en 3-5 paragraphes",
  "key_points": ["Point clé 1", "Point clé 2", "Point clé 3"],
  "actions_required": ["Action à faire 1 avec deadline", "Action 2"],
  "deadlines": ["Date limite 1", "Date limite 2"],
  "document_type": "avis_imposition|decision_spf|courrier_onss|notification_commune|autre"
}

RÈGLES :
1. Explique CHAQUE terme technique entre parenthèses
2. Mentionne les deadlines en gras
3. Liste les actions que le citoyen doit entreprendre
4. Ne donne aucun conseil juridique — informe uniquement"""


def decode_document(text: str, mock: bool = False) -> dict:
    """Traduit un document administratif en langage clair."""
    if len(text.strip()) < 20:
        raise ValueError("Le document est trop court")

    if mock:
        return {
            "plain_language": "Ce document est un avis d'imposition (test).",
            "key_points": ["Revenu imposable déterminé", "Quotité exemptée appliquée"],
            "actions_required": [],
            "deadlines": [],
            "document_type": "avis_imposition",
        }

    from api.utils.model_router import select_model
    import anthropic

    model = select_model("translation", len(text))
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=DECODE_PROMPT,
        messages=[{"role": "user", "content": f"DOCUMENT À TRADUIRE :\n\n{text}"}],
    )

    raw = response.content[0].text.strip()
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        return json.loads(json_match.group())
    return {"plain_language": raw, "key_points": [], "actions_required": [], "deadlines": []}
```

- [ ] **Step 3: Ajouter les endpoints Decode dans main.py**

```python
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

    text = request.get("document_text", "")
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
    """Upload un document admin (PDF/image) → OCR → traduction."""
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
```

- [ ] **Step 4: Tests + Commit**

Run: `python -m pytest tests/test_decode.py -v`

```bash
git add api/features/decode.py tests/test_decode.py api/main.py
git commit -m "feat(decode): add document translation to plain language with OCR support"
```

---

## WAVE 2 — Feature #2 : Calculateurs de droits

### Task 7: Calculateurs purs (zéro API)

**Files:**
- Create: `api/features/calculators.py`
- Create: `tests/test_calculators.py`
- Modify: `api/main.py`

- [ ] **Step 1: Écrire les tests calculateurs**

```python
# tests/test_calculators.py
import pytest
from api.features.calculators import (
    calculate_notice_period,
    calculate_alimony_renard,
    calculate_succession_duties,
)


class TestNoticePeriod:
    """Tests préavis de licenciement (CCT n°109 + Loi Peeters)."""

    def test_basic_notice(self):
        result = calculate_notice_period(years=5, monthly_salary=3000)
        assert result["weeks"] == 18
        assert result["legal_basis"] == "CCT n°109"

    def test_zero_years(self):
        result = calculate_notice_period(years=0, monthly_salary=2500)
        assert result["weeks"] >= 1

    def test_long_service(self):
        result = calculate_notice_period(years=25, monthly_salary=4000)
        assert result["weeks"] >= 60


class TestAlimonyRenard:
    """Tests pension alimentaire barème Renard."""

    def test_basic_alimony(self):
        result = calculate_alimony_renard(
            income_high=4000, income_low=1500, children=2
        )
        assert result["monthly_amount"] > 0
        assert "formula" in result

    def test_no_children(self):
        result = calculate_alimony_renard(
            income_high=3000, income_low=1000, children=0
        )
        assert result["monthly_amount"] > 0


class TestSuccessionDuties:
    """Tests droits de succession par région."""

    def test_brussels_direct_line(self):
        result = calculate_succession_duties(
            region="bruxelles", amount=200000, relationship="direct_line"
        )
        assert result["total_duty"] > 0
        assert result["region"] == "bruxelles"

    def test_wallonia_direct_line(self):
        result = calculate_succession_duties(
            region="wallonie", amount=200000, relationship="direct_line"
        )
        assert result["total_duty"] > 0

    def test_flanders_direct_line(self):
        result = calculate_succession_duties(
            region="flandre", amount=200000, relationship="direct_line"
        )
        assert result["total_duty"] > 0
```

- [ ] **Step 2: Implémenter les calculateurs**

```python
# api/features/calculators.py
"""Calculateurs de droits belges — logique mathématique pure (zéro API).

Sources légales :
- Préavis : CCT n°109 du CNT (30/01/2014) + Loi Peeters (26/12/2013)
- Pension alimentaire : Barème Renard (méthode doctrinale de référence)
- Succession : Code des droits de succession (3 régions)
"""


def calculate_notice_period(years: int, monthly_salary: float) -> dict:
    """Calcule le préavis de licenciement.

    Barème CCT n°109 : tableau progressif par trimestres d'ancienneté.
    Depuis le 01/01/2014 (statut unique ouvriers/employés).
    """
    # Barème simplifié CCT n°109 (semaines par année d'ancienneté)
    # Années 0-5 : +3 semaines/an en moyenne
    # Années 5-10 : +3 semaines/an
    # Années 10-15 : +3 semaines/an
    # Années 15-20 : +3 semaines/an
    # Au-delà : +3 semaines/an

    if years < 0:
        raise ValueError("L'ancienneté ne peut pas être négative")

    # Calcul par tranches (CCT n°109 art. 2 §1)
    if years == 0:
        weeks = 1
    elif years <= 3:
        weeks = 2 + (years * 4)  # ~4 semaines par an (premiers mois)
    elif years <= 4:
        weeks = 15
    elif years <= 5:
        weeks = 18
    elif years <= 6:
        weeks = 21
    elif years <= 7:
        weeks = 24
    elif years <= 8:
        weeks = 27
    elif years <= 9:
        weeks = 30
    elif years <= 10:
        weeks = 33
    elif years <= 15:
        weeks = 33 + (years - 10) * 3
    elif years <= 20:
        weeks = 48 + (years - 15) * 3
    else:
        weeks = 63 + (years - 20) * 3

    # Indemnité = salaire × (weeks / 4.33)
    indemnity = round(monthly_salary * (weeks / 4.33), 2)

    return {
        "weeks": weeks,
        "months": round(weeks / 4.33, 1),
        "indemnity_euros": indemnity,
        "monthly_salary": monthly_salary,
        "years_service": years,
        "legal_basis": "CCT n°109",
        "disclaimer": "Calcul indicatif basé sur le barème légal. Des exceptions existent (motif grave, contre-préavis).",
    }


def calculate_alimony_renard(
    income_high: float, income_low: float, children: int = 0
) -> dict:
    """Calcule la pension alimentaire selon le barème Renard.

    Méthode Renard : la pension vise à maintenir le niveau de vie
    du conjoint le moins favorisé.
    """
    if income_high < income_low:
        income_high, income_low = income_low, income_high

    total_income = income_high + income_low

    # Formule Renard simplifiée :
    # Pension = (Revenus élevés - Revenus faibles) / 3
    # Avec correction pour enfants : +10% par enfant à charge

    base = (income_high - income_low) / 3
    child_supplement = base * 0.10 * children
    monthly_amount = round(base + child_supplement, 2)

    # Plafonner à 1/3 du revenu du débiteur
    cap = income_high / 3
    if monthly_amount > cap:
        monthly_amount = round(cap, 2)

    return {
        "monthly_amount": monthly_amount,
        "annual_amount": round(monthly_amount * 12, 2),
        "income_high": income_high,
        "income_low": income_low,
        "children": children,
        "formula": "Barème Renard : (revenus élevés - revenus faibles) / 3",
        "legal_basis": "Art. 301 §3 Code civil (critères de fixation)",
        "disclaimer": "Calcul indicatif. Le juge fixe le montant selon les circonstances.",
    }


# Barèmes droits de succession par région (tranches 2025)
SUCCESSION_RATES = {
    "bruxelles": {
        "direct_line": [
            (50000, 0.03),
            (100000, 0.08),
            (175000, 0.09),
            (250000, 0.18),
            (500000, 0.24),
            (float("inf"), 0.30),
        ],
        "siblings": [
            (12500, 0.20),
            (25000, 0.25),
            (50000, 0.30),
            (100000, 0.40),
            (175000, 0.55),
            (250000, 0.60),
            (float("inf"), 0.65),
        ],
        "others": [
            (50000, 0.40),
            (75000, 0.55),
            (175000, 0.65),
            (float("inf"), 0.80),
        ],
    },
    "wallonie": {
        "direct_line": [
            (12500, 0.03),
            (25000, 0.04),
            (50000, 0.05),
            (100000, 0.07),
            (150000, 0.10),
            (200000, 0.14),
            (250000, 0.18),
            (500000, 0.24),
            (float("inf"), 0.30),
        ],
        "siblings": [
            (12500, 0.20),
            (25000, 0.25),
            (75000, 0.35),
            (175000, 0.50),
            (float("inf"), 0.65),
        ],
        "others": [
            (12500, 0.25),
            (25000, 0.30),
            (75000, 0.40),
            (175000, 0.55),
            (float("inf"), 0.70),
        ],
    },
    "flandre": {
        "direct_line": [
            (50000, 0.03),
            (250000, 0.09),
            (float("inf"), 0.27),
        ],
        "siblings": [
            (35000, 0.25),
            (75000, 0.30),
            (float("inf"), 0.55),
        ],
        "others": [
            (35000, 0.25),
            (75000, 0.45),
            (float("inf"), 0.55),
        ],
    },
}


def calculate_succession_duties(
    region: str, amount: float, relationship: str = "direct_line"
) -> dict:
    """Calcule les droits de succession par région belge.

    Args:
        region: bruxelles, wallonie, flandre
        amount: Montant de la part successorale en euros
        relationship: direct_line, siblings, others
    """
    region = region.lower().replace("è", "e").replace("ê", "e")
    if region not in SUCCESSION_RATES:
        raise ValueError(f"Région inconnue : {region}. Utilisez bruxelles, wallonie ou flandre.")
    if relationship not in ("direct_line", "siblings", "others"):
        raise ValueError("Relation : direct_line, siblings, others")

    rates = SUCCESSION_RATES[region][relationship]

    total_duty = 0.0
    remaining = amount
    breakdown = []

    prev_limit = 0
    for limit, rate in rates:
        taxable = min(remaining, limit - prev_limit)
        if taxable <= 0:
            break
        duty = taxable * rate
        total_duty += duty
        breakdown.append({
            "from": prev_limit,
            "to": prev_limit + taxable,
            "rate": f"{rate*100:.0f}%",
            "duty": round(duty, 2),
        })
        remaining -= taxable
        prev_limit = limit

    effective_rate = (total_duty / amount * 100) if amount > 0 else 0

    return {
        "total_duty": round(total_duty, 2),
        "net_amount": round(amount - total_duty, 2),
        "effective_rate": f"{effective_rate:.1f}%",
        "region": region,
        "relationship": relationship,
        "amount": amount,
        "breakdown": breakdown,
        "legal_basis": f"Code des droits de succession — Région de {region.capitalize()}",
        "disclaimer": "Calcul indicatif. Des exemptions et réductions peuvent s'appliquer.",
    }
```

- [ ] **Step 3: Ajouter les endpoints calculateurs dans main.py**

```python
# ─── Calculator Endpoints ──────────────────────────────────────────────────

@app.post("/calculators/notice-period")
def calc_notice(
    years: int = Query(..., ge=0, description="Années d'ancienneté"),
    monthly_salary: float = Query(..., gt=0, description="Salaire mensuel brut"),
):
    """Calculateur de préavis de licenciement (CCT n°109)."""
    from api.features.calculators import calculate_notice_period
    return calculate_notice_period(years=years, monthly_salary=monthly_salary)


@app.post("/calculators/alimony")
def calc_alimony(
    income_high: float = Query(..., gt=0),
    income_low: float = Query(..., ge=0),
    children: int = Query(default=0, ge=0),
):
    """Calculateur de pension alimentaire (barème Renard)."""
    from api.features.calculators import calculate_alimony_renard
    return calculate_alimony_renard(
        income_high=income_high, income_low=income_low, children=children
    )


@app.post("/calculators/succession")
def calc_succession(
    region: str = Query(..., description="bruxelles, wallonie, flandre"),
    amount: float = Query(..., gt=0, description="Montant en euros"),
    relationship: str = Query(default="direct_line", description="direct_line, siblings, others"),
):
    """Calculateur de droits de succession par région."""
    from api.features.calculators import calculate_succession_duties
    return calculate_succession_duties(
        region=region, amount=amount, relationship=relationship
    )
```

- [ ] **Step 4: Tests + Commit**

Run: `python -m pytest tests/test_calculators.py -v`

```bash
git add api/features/calculators.py tests/test_calculators.py api/main.py
git commit -m "feat(calculators): add notice period, alimony, and succession duty calculators"
```

---

## WAVES 3-5 — Features #3 à #15 (résumé)

Les features suivantes suivent le même pattern. Chacune sera détaillée dans son propre plan quand on y arrive.

### Feature #3: Bibliothèque de contrats
- `api/features/contracts.py` — Templates HTML → WeasyPrint PDF
- Endpoints: `GET /contracts/templates`, `GET /contracts/{id}/download`
- Templates: bail (3 régions), contrat de travail, vente, prêt, mise en demeure, CGV

### Feature #4: Générateur de réponses juridiques
- `api/features/legal_response.py` — OCR courrier reçu → RAG → lettre type
- Endpoints: `POST /response/generate`, `POST /response/upload`

### Feature #5: Diagnostic juridique
- `api/features/diagnostic.py` — 6 questions → rapport personnalisé
- Endpoints: `POST /diagnostic/start`, `POST /diagnostic/answer`, `GET /diagnostic/{id}/report`

### Feature #6: Lexavo Score
- `api/features/score.py` — 10 questions → score /100 + rapport
- Endpoints: `POST /score/evaluate`, `GET /score/history`

### Feature #7: Compliance B2B
- `api/features/compliance.py` — 15 questions → audit RGPD/légal
- Endpoints: `POST /compliance/audit`, `GET /compliance/{id}/report`

### Feature #8: Alertes législatives
- `api/features/alerts.py` — Préférences + cron + push Expo
- Endpoints: `POST /alerts/preferences`, `GET /alerts/feed`

### Feature #10: Litiges Pro
- `api/features/litigation.py` — Séquence rappel → mise en demeure → recommandation
- Endpoints: `POST /litigation/start`, `GET /litigation/{id}/status`

### Feature #11: Match avocats
- `api/features/match.py` — Matching par branche/budget/ville/langue
- Endpoints: `POST /match/find`, `POST /match/{lawyer_id}/contact`

### Feature #12: Emergency
- `api/features/emergency.py` — Formulaire urgence + notif avocat + Stripe
- Endpoints: `POST /emergency/request`

### Feature #13: Proof
- `api/features/proof.py` — CRUD dossier + pièces + timestamps
- Endpoints: `POST /proof/create`, `POST /proof/{id}/add-entry`, `GET /proof/{id}`

### Feature #14: Héritage
- `api/features/heritage.py` — Questionnaire → guide étape par étape
- Endpoints: `POST /heritage/guide`

### Feature #15: Fiscal
- `api/features/fiscal.py` — Questions TVA/impôts → RAG sources fiscales
- Endpoints: `POST /fiscal/ask`

---

## Ordre d'exécution final

```
Task 0  → Fondations (fixtures, utils, OCR, PDF, model router)
Task 1-5 → Shield complet (modèles, DB, logique, endpoints, upload)
Task 6   → Decode (réutilise Shield pipeline)
Task 7   → Calculateurs (pure math)
Task 8+  → Features #3-#15 (plans détaillés à chaque wave)
```

Chaque task = commit autonome. Chaque feature = testable indépendamment.
