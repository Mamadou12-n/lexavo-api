# CLAUDE.md — Lexavo "Le droit pour tous"

## Identité

- **Nom** : Lexavo — assistant juridique belge (SRL en cours d'immatriculation)
- **Auteur** : Mamadou Diallo, EPHEC Etterbeek, TFE juin 2026
- **Langue** : toujours répondre en français
- **Scope** : droit belge uniquement — 3 régions (Bruxelles, Wallonie, Flandre)

## Architecture

```
LEXAVO
├── Backend FastAPI   → api/main.py (20+ endpoints)
├── RAG Pipeline      → rag/pipeline.py (ChromaDB, 43 429 chunks, 18 sources)
├── Mobile Expo       → mobile/ (React Native, Expo SDK 54)
├── Prototype HTML    → App Droit/prototype.html (14 écrans)
└── Déploiement       → Railway (Dockerfile multi-stage, PostgreSQL prod)
```

## Fichiers critiques

| Fichier | Rôle |
|---------|------|
| `api/main.py` | Tous les endpoints FastAPI |
| `api/database.py` | DB layer (PostgreSQL prod, SQLite dev) |
| `api/models.py` | Modèles Pydantic |
| `api/features/defend.py` | Lexavo Defend (contestation/recours) |
| `api/features/shield.py` | Shield (analyse contrat, score /100) |
| `api/features/audit_entreprise.py` | Audit PME (30 questions, 8 domaines) |
| `api/features/calculators.py` | 3 calculateurs (préavis, succession, pension) |
| `api/features/fiscal.py` | Copilote fiscal |
| `api/features/decode.py` | Traducteur documents administratifs |
| `api/features/diagnostic.py` | Questionnaire juridique personnalisé |
| `api/features/legal_response.py` | Générateur réponse courrier |
| `rag/pipeline.py` | RAG + mémoire conversationnelle (history) |
| `rag/humanizer.py` | Post-traitement ton naturel |
| `mobile/src/api/client.js` | Appels API mobile |

## Règles non-négociables

1. **Zéro invention** — ne jamais inventer d'articles de loi, de chiffres ou de jurisprudence
2. **Droit belge** — CIR 1992, Code civil, CTVA, CCT, lois fédérales/régionales uniquement
3. **Disclaimer obligatoire** — chaque réponse juridique inclut "ne constitue pas un avis juridique"
4. **Helpers existants** — utiliser `_get_conn()`, `USE_PG`, `_execute()`, `_fetchone()`, `_fetchall()` dans database.py (ne PAS inventer `get_connection()` ou `_use_pg()`)
5. **Humanizer** — intégré dans toutes les features (shield, audit, diagnostic, decode, fiscal, legal_response)
6. **Retriever 9 alternatives** — le RAG utilise 9 mécanismes de recherche qui se corrigent mutuellement :
   - Alt.1 Vecteurs sémantiques | Alt.2 Mots-clés articles (Art. X) | Alt.3 Termes juridiques ($contains)
   - Alt.4 Chunks voisins (contexte ±1) | Alt.5 Vote majoritaire | Alt.6 Filtre source détectée
   - Alt.7 Re-ranking Claude Haiku | Alt.8 Index articles séparé | Alt.9 Reformulation automatique
   - Si l'info n'est pas dans la base → dire "je ne sais pas", **jamais inventer**
   - Chaque erreur d'une alternative est corrigée par les autres automatiquement
7. **Skill add-legal-source** — toute nouvelle source juridique DOIT passer par la skill
   `claude-skills/add-legal-source/SKILL.md` (8 étapes obligatoires, zéro invention à chaque étape)

## Stack technique

- **Backend** : FastAPI, Python 3.11, Anthropic Claude API
- **DB** : PostgreSQL (Railway prod), SQLite (dev local)
- **RAG** : ChromaDB, sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Auth** : JWT (bcrypt), refresh tokens
- **Paiement** : Stripe (7 plans : free → enterprise)
- **Mobile** : React Native, Expo SDK 54
- **Deploy** : Railway (Dockerfile multi-stage, PyTorch CPU-only)
- **CI** : GitHub Actions (emails beta)

## Commandes utiles

```bash
# Backend dev
cd base-juridique-app && uvicorn api.main:app --reload --port 8000

# Prototype
cd "App Droit" && python -m http.server 8080

# Tests features (mock)
python -c "from api.features.defend import analyze_and_generate; print(analyze_and_generate('test situation', mock=True))"
```
