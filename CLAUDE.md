# CLAUDE.md — Lexavo "Le droit pour tous"

## Identité

- **Nom** : Lexavo — assistant juridique belge (SRL en cours d'immatriculation)
- **Auteur** : Mamadou Diallo, EPHEC Etterbeek, TFE juin 2026
- **Langue** : toujours répondre en français
- **Scope** : droit belge uniquement — 3 régions (Bruxelles, Wallonie, Flandre)

## Architecture

```
LEXAVO
├── Backend FastAPI   → api/main.py (28 endpoints, 19 features)
├── RAG Pipeline      → rag/pipeline.py (ChromaDB, 6 430 chunks + 3 400 articles, 28 codes belges)
├── Retriever         → rag/retriever.py (9 alternatives de recherche mutuellement correctives)
├── Mobile Expo       → mobile/ (React Native, Expo SDK 54, 33 écrans, 6 composants)
├── Scrapers          → scrapers/ (20 scrapers : JUSTEL, HUDOC, EUR-Lex, SPF Finances, SPF Emploi, etc.)
├── Prototype HTML    → App Droit/prototype.html
└── Déploiement       → Railway (Dockerfile multi-stage, PostgreSQL prod, ChromaDB via GitHub Release v2.0)
```

## Base de données juridique (socle de l'app)

| Source | Contenu | Chars | Articles |
|--------|---------|------:|--------:|
| Code civil (ancien) | Texte coordonné complet | 592 115 | 864 |
| Nouveau Code civil (Livres 1/3/5/8) | Réforme 2022 — obligations, biens, preuve | 20 401 | 18 |
| Code pénal | Texte coordonné complet | 661 744 | 1 043 |
| Code judiciaire | Texte coordonné complet | 1 534 527 | 1 202 |
| CSA 2019 | Code des sociétés et associations | 1 563 557 | 1 754 |
| CDE | Code de droit économique | 3 500 864 | — |
| Loi sur les étrangers 1980 | + Loi accueil asile 2007 + AR CCE | 965 133 | 368 |
| Constitution belge | Texte coordonné | 141 558 | 236 |
| Code TVA + CIR 1992 | Droit fiscal coordonné | 286 563 | 76 |
| Loi contrats de travail | + accidents travail + bien-être + sécu sociale | 793 567 | 480 |
| Code d'instruction criminelle | Procédure pénale | 454 619 | 301 |
| + 8 autres codes/lois | Nationalité, DIP, assurances, marchés publics, patient | ~170 000 | ~95 |
| **Total** | **28 codes/lois complets** | **10 684 623** | **6 437** |

**Source** : ejustice.just.fgov.be (SPF Justice belge), NUMACs + cn vérifiés sur eTAAMB
**Zéro invention** : tous les textes proviennent de sources officielles, vérifiés 5 fois

## Fichiers critiques

### Backend
| Fichier | Rôle |
|---------|------|
| `api/main.py` | 28 endpoints FastAPI (auth, RAG, billing, features) |
| `api/auth.py` | JWT bcrypt + refresh tokens, 8 langues (fr/nl/en/de/ar/tr/es/pt) |
| `api/database.py` | 15 tables, PostgreSQL prod / SQLite dev |
| `api/stripe_billing.py` | 7 plans (free→enterprise), webhooks, beta mode |
| `api/utils/model_router.py` | Haiku (simple) / Sonnet (analyse) / Opus (complexe) |
| `rag/pipeline.py` | RAG complet + détection 15 branches + garde-fou Alt.6 |
| `rag/retriever.py` | 9 alternatives de recherche (vecteurs + mots-clés + Haiku + reformulation) |
| `rag/indexer.py` | ChromaDB + index articles séparé (Alt.8) |
| `rag/branches.py` | 15 branches du droit avec prompts et sources spécialisés |
| `rag/humanizer.py` | Post-traitement : supprime patterns IA, préserve citations juridiques |

### Mobile
| Fichier | Rôle |
|---------|------|
| `mobile/App.js` | 6 onglets (Accueil, Defend, Chat, Avocats, Abonnement, Settings) + 16 outils cachés |
| `mobile/src/api/client.js` | 50 fonctions API, URL Railway production, intercepteurs 401 |
| `mobile/src/screens/HomeScreen.js` | Hero LEXAVO + 2 cartes + grille 16 outils + 15 branches + étudiants |
| `mobile/src/screens/AskScreen.js` | Chat RAG principal + filtres source + PhotoPicker |
| `mobile/src/screens/StudentScreen.js` | Quiz QCM + Flashcards + Résumé (Claude API) |
| `mobile/src/screens/OnboardingScreen.js` | 8 langues + région + profession |
| `mobile/src/components/PhotoPicker.js` | Composant réutilisable (camera + galerie, max 3 photos, base64) |

### Features (19 modules)
| Module | Modèle Claude | Description |
|--------|--------------|-------------|
| defend.py | Sonnet | Contestation/recours (8 situations) |
| shield.py | Sonnet→Opus (>15KB) | Analyse contrat (10 types, score /100) |
| diagnostic.py | Sonnet | Questionnaire 6 questions, rapport personnalisé |
| fiscal.py | Sonnet | Copilote TVA/CIR pour indépendants |
| legal_response.py | Sonnet | Réponse à courrier (propriétaire, huissier, admin) |
| calculators.py | Haiku | Préavis, succession, pension, indexation loyer |
| compliance.py | Sonnet | Audit RGPD/conformité B2B |
| contracts.py | Sonnet | Génération contrats PDF (7 types) |
| heritage.py | Sonnet | Guide successoral belge |
| litigation.py | Sonnet | Recouvrement impayés |
| match.py | Sonnet | Matching avocat par spécialité |
| emergency.py | Opus | Urgence juridique 24h (49€) |
| score.py | Haiku | Score santé juridique /100 |
| decode.py | Haiku | Traduction documents administratifs |
| alerts.py | Haiku | Veille législative belge |
| proof.py | — | Constituer un dossier de preuves |
| audit_entreprise.py | Opus | Audit PME 30 questions, 8 domaines |
| newsletter.py | — | Newsletter 15 domaines juridiques |

## Règles non-négociables

1. **Zéro invention** — ne jamais inventer d'articles de loi, de chiffres, de NUMACs ou de jurisprudence
2. **Droit belge** — CIR 1992, Code civil, CTVA, CCT, lois fédérales/régionales uniquement
3. **Disclaimer obligatoire** — chaque réponse juridique inclut "ne constitue pas un avis juridique"
4. **Helpers existants** — utiliser `_get_conn()`, `USE_PG`, `_execute()`, `_fetchone()`, `_fetchall()` dans database.py
5. **Humanizer** — intégré dans toutes les features (shield, audit, diagnostic, decode, fiscal, legal_response)
6. **Retriever 9 alternatives** — le RAG utilise 9 mécanismes de recherche qui se corrigent mutuellement :
   - Alt.1 Vecteurs sémantiques | Alt.2 Mots-clés articles (Art. X) | Alt.3 Termes juridiques ($contains)
   - Alt.4 Chunks voisins (contexte ±1) | Alt.5 Vote majoritaire | Alt.6 Filtre source détectée
   - Alt.7 Re-ranking Claude Haiku | Alt.8 Index articles séparé | Alt.9 Reformulation automatique
   - Si l'info n'est pas dans la base → dire "je ne sais pas", **jamais inventer**
   - Chaque erreur d'une alternative est corrigée par les autres automatiquement
7. **Skill add-legal-source** — toute nouvelle source juridique DOIT passer par la skill
   `claude-skills/add-legal-source/SKILL.md` (8 étapes obligatoires, zéro invention à chaque étape)
8. **Vérifier 2 fois minimum** — chaque donnée (NUMAC, URL, contenu) est vérifiée sur la source officielle avant utilisation

## Stack technique

- **Backend** : FastAPI 0.111, Python 3.11, Anthropic Claude API (Haiku/Sonnet/Opus automatique)
- **DB** : PostgreSQL (Railway prod), SQLite (dev local), 15 tables
- **RAG** : ChromaDB (6 430 chunks + 3 400 articles), sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 dims)
- **Auth** : JWT bcrypt 12 rounds, refresh tokens 30 jours, 8 langues
- **Paiement** : Stripe live (7 plans : free → enterprise), beta gratuit jusqu'au 2026-10-01
- **Mobile** : React Native 0.81, Expo SDK 54, React Navigation 7.x
- **Deploy** : Railway (Dockerfile multi-stage, PyTorch CPU-only, ChromaDB via GitHub Release v2.0)
- **CI** : GitHub Actions (emails beta), auto-deploy Railway sur push main

## Déploiement

```bash
# Backend dev
cd base-juridique-app && uvicorn api.main:app --reload --port 8000

# Scraping + indexation
python run_all.py --sources justel --phase scraping --max-docs 5000
python run_all.py --phase indexing

# Mobile dev
cd mobile && npx expo start

# Production Railway
# Auto-deploy via push GitHub → Railway
# ChromaDB téléchargée au démarrage depuis GitHub Release v2.0-chroma
# start.sh gère le download automatique
```

## Audit final (2026-04-02)

### Mobile — 33 écrans, 6 composants
- 6 onglets visibles (Accueil, Defend, Chat, Avocats, Abonnement, Settings)
- 16 outils juridiques + StudentScreen (quiz/flashcards/résumé)
- PhotoPicker dans 16/16 écrans outils
- API client : 50 fonctions, URL Railway, intercepteurs 401
- 8 langues dans onboarding

### Backend — 28 endpoints, 19 features
- RAG 9 alternatives opérationnel (test 9/10 exact, 10/10 bonne source)
- 28 codes belges complets (Constitution, Code civil, Code pénal, Code judiciaire, CSA, CDE, Loi étrangers...)
- Stripe live avec 7 plans
- JWT + refresh tokens
- 15 branches du droit avec détection automatique
