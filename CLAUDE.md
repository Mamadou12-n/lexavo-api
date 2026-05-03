# CLAUDE.md — Lexavo "Le droit pour tous"

## Identité

- **Nom** : Lexavo — assistant juridique belge (SRL en cours d'immatriculation)
- **Auteur** : Mamadou BAH
- **Langue** : toujours répondre en français
- **Scope** : droit belge et europen  — 3 régions (Bruxelles, Wallonie, Flandre)

## Architecture

```
LEXAVO
├── Backend FastAPI   → api/main.py (28 endpoints, 19 features)
├── RAG Pipeline      → rag/pipeline.py (Qdrant prod, 3 490 000+ chunks, 28 codes belges)
├── Retriever         → rag/retriever.py (9 alternatives de recherche mutuellement correctives)
├── Mobile Expo       → mobile/ (React Native, Expo SDK 54, 33 écrans, 6 composants)
├── Scrapers          → scrapers/ (20 scrapers : JUSTEL, HUDOC, EUR-Lex, SPF Finances, SPF Emploi, etc.)
├── Prototype HTML    → App Droit/prototype.html
└── Déploiement       → Railway (Dockerfile multi-stage, PostgreSQL prod, Qdrant cloud)
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
5. **Humanizer** — intégré dans toutes l'application toutes les reponses  (shield, audit, diagnostic, decode, fiscal, legal_response)
6. **Retriever 9 alternatives** — le RAG utilise 9 mécanismes de recherche qui se corrigent mutuellement :
   - Alt.1 Vecteurs sémantiques | Alt.2 Mots-clés articles (Art. X) | Alt.3 Termes juridiques ($contains)
   - Alt.4 Chunks voisins (contexte ±1) | Alt.5 Vote majoritaire | Alt.6 Filtre source détectée
   - Alt.7 Re-ranking Claude Haiku | Alt.8 Index articles séparé | Alt.9 Reformulation automatique
   - Si l'info n'est pas dans la base → dire "je ne sais pas", **jamais inventer**
   - Chaque erreur d'une alternative est corrigée par les autres automatiquement
7. **Skill add-legal-source** — toute nouvelle source juridique DOIT passer par la skill
   `claude-skills/add-legal-source/SKILL.md` (8 étapes obligatoires, zéro invention à chaque étape)
8. **Vérifier 2 fois minimum** — chaque donnée (NUMAC, URL, contenu) est vérifiée sur la source officielle avant utilisation
9. **Complétude obligatoire avant indexation** — JAMAIS indexer ou normaliser des docs incomplets (métadonnées seules, abstracts seuls, full_text < 500 chars pour doctrine académique) sans accord explicite de l'utilisateur. Audit obligatoire avant indexation : char_count distribution + sample 5 docs. Si majorité < seuil → STOP + demander confirmation. Vaut pour TOUTES sources (HAL, DIAL, ORBI, UGENT, ISIDORE, KULEUVEN, mais aussi tout nouveau scraper).

## Stack technique

- **Backend** : FastAPI 0.111, Python 3.11, Anthropic Claude API (Haiku/Sonnet/Opus automatique)
- **DB** : PostgreSQL (Railway prod), SQLite (dev local), 15 tables
- **RAG** : Qdrant (3 490 000+ chunks, 28 codes belges), sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 dims) — migration BGE-M3 planifiée
- **Auth** : JWT bcrypt 12 rounds, refresh tokens 30 jours, 8 langues
- **Paiement** : Stripe live (7 plans : free → enterprise), beta gratuit jusqu'au 2026-10-01
- **Mobile** : React Native 0.81, Expo SDK 54, React Navigation 7.x
- **Deploy** : Railway (Dockerfile multi-stage, PyTorch CPU-only, Qdrant cloud)
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

---

## Audit exhaustif multi-angles (2026-05-02)

**6 sous-agents spécialisés ont audité le projet en parallèle.** Score moyen pondéré : **6.6/10** — production-acceptable mais NON release-ready sans correctifs.

### Scores par angle

| Angle | Score | Statut | Auditeur |
|-------|-------|--------|----------|
| Sécurité | 7.0/10 | NEEDS-WORK | security-auditor |
| Performance | 6.5/10 | À optimiser | performance-engineer |
| Architecture/Code | 6.0/10 | MVP avancé / Beta précoce | architect-reviewer |
| UX/UI/A11y | 7.2/10 | GOOD | accessibility-tester |
| Produit/Business | Pre-PMF + early signals | À focaliser | product-manager |
| RAG/IA | 6.5/10 | Decent | ai-engineer |

### Top 15 risques bloquants (par criticité)

| # | Risque | Sévérité | Effort fix |
|---|--------|----------|------------|
| 1 | Secrets `.env` live en clair (Stripe live, Anthropic, JWT) sur disque Windows | CRITICAL CVSS 9.1 | 30 min (rotation + Railway env) |
| 2 | SSRF via `/student/lms/connect` — site_url non whitelisté (cloud metadata exposable) | HIGH CVSS 8.2 | 1h (validation URL) |
| 3 | Quota beta = illimité — DoS coût Claude API (1000€/jour possible) | CRITICAL business | 30 min (cap dur 50q/mois free) |
| 4 | 0 prompt caching Anthropic — perte sèche 30-80€/mois maintenant, scaling linéaire | Important | 2h |
| 5 | `api/main.py` monolithique 3045 lignes — vélocité chute à mesure que features s'ajoutent | Important | 3-5j (split en routers) |
| 6 | Aucun test RAG sur les 9 alternatives (cœur métier 673 L) | Critique réputation | 4-5j |
| 7 | Aucun eval set Q/A juridique — "80% top-1" non mesuré, juste estimé | Risque légal | 2j |
| 8 | Pas de pool DB PostgreSQL — 50-100ms/requête perdues sur Railway | Perf | 30 min |
| 9 | Streaming `/ask` absent — UX 12s d'attente muette | UX critique | 1j (SSE) |
| 10 | Embeddings obsolètes (MiniLM 2021, 384D) vs BGE-M3 (1024D) | Qualité retrieval | 1j + ré-indexation |
| 11 | `StudentScreen.js` 2451 L — god component, perfs mobile dégradées | UX/Perf | 1 sem |
| 12 | i18n incomplète — 7 outils écrans en FR hardcodés (Defend, Shield, Diagnostic...) | Marketing 8 langues | 2-3j |
| 13 | Mobile en JS pur (pas TypeScript) sur 15K LOC | Maintenabilité | 2-3 sem (incrémental) |
| 14 | 0 observabilité IA (Sentry, Langfuse, Langsmith absents) | Risque légal RGPD | 1j |
| 15 | 19 features → 3 personas viables réels — message produit dispersé | PMF | Décision stratégique |

### Findings sécurité détaillés

- **API1 BOLA** : OK (pattern `obj.user_id == current_user.id` cohérent)
- **API2 Auth** : OK avec réserve — password min 6 chars (sous-standard NIST), pas de check HIBP
- **API4 Rate limiting** : partiel — slowapi par IP mais pas par user_id, quota beta bypassé
- **API6 SSRF** : KO sur `/student/lms/connect`, exposable à `169.254.169.254` (cloud metadata)
- **API7 Misconfig** : OK (CORS strict, security headers complets)
- **API10 Stripe webhook** : OK (signature + idempotence DB)

### Findings performance détaillés

- Latence p50 `/ask` : ~12s, p95 ~22s. Cible : 5s / 10s
- Hotspots : génération Sonnet (60-80%), Alt.2/3 sériels (300-1200ms), Alt.4 voisins sériels (150-400ms)
- Dockerfile télécharge 500 MB ChromaDB **inutilisé** (le code utilise Qdrant)
- 95 routes en `def` sync → saturent threadpool 40 workers global
- Économies API potentielles avec quick wins : ~50€/mois actuel, scaling linéaire

### Findings architecture détaillés

- `api/main.py` : 3045 L, 112 décorateurs `@app.*`, **0 APIRouter** (sauf seo_router)
- 14 duplications du pattern `json.loads(json_match.group())` dans 8 features
- 1 seule migration Alembic (schéma figé)
- Mobile : god components (StudentScreen 2436 L, Subscription 661, Shield 603)
- Pas de Sentry, pas de TypeScript, pas de linter/formatter, pas d'ADR
- 30 fichiers de tests backend mais **0 test RAG**

### Findings UX/A11y détaillés

- WCAG 2.1 AA : 65-70% conforme
- Critique : SafeAreaProvider importé mais non wrappé → notch overlap
- Critique : TextInput sans focus ring (Auth + Ask)
- Caption font 11pt + tabBar 10pt = sous WCAG AA
- BCE/VAT placeholder `[NUMÉRO BCE À COMPLÉTER]` non remplacé !
- 7 écrans outils avec strings FR hardcodés (i18n incomplète)
- Dark mode non supporté

### Findings business/PMF détaillés

- **Verdict : Pre-PMF avec early signals techniques forts**
- 19 features = dispersion → 3 personas viables (Particulier 9.99€, Indépendant/TPE 29.99€, PME 99€)
- 7 plans = 4 de trop. Tuer firm_s/firm_m (positionnement avocats faible vs Doctrine)
- Risque #1 : pas de funnel de conversion beta→paid défini
- Coût Claude API par user : 0,30-0,80€ (casual) / 2-5€ (moyen) / 8-20€ (power)
- LTV/CAC tendu : LTV ~300€, CAC Google Ads juridique BE 80-200€

### Findings RAG/IA détaillés

- Embeddings MiniLM-L12-v2 (384D) obsolète pour juridique → migrer BGE-M3 (1024D)
- Aucun eval set Q/A gold standard, aucun nDCG/MRR/recall@K mesuré
- `verify_citations` ne vérifie que ECLI + `[n]`, **pas les numéros d'articles ni dates de lois**
- Détection branche par keyword matching naïf (faux positifs garantis)
- Doublon massif `indexer.py` (ChromaDB) + `indexer_qdrant.py` (Qdrant) — drift silencieux
- Humanizer regex fragile sur citations légales (pas de test unitaire dédié)
- 0 observabilité (Langfuse/Langsmith/Phoenix absents)

### 3 priorités absolues 30 jours

1. **Sécurité + cash control (J1-J2)** : rotation secrets, cap quota beta, SSRF fix
2. **Observabilité + eval set (J3-J7)** : Sentry + Langfuse + 50 Q/A gold
3. **Focalisation produit (J8-J30)** : 20 interviews users, 1 persona prioritaire, tuer 8-10 features, simplifier pricing à 5 plans

**Le risque #1 n'est pas technique, c'est la dispersion produit + l'absence de funnel de conversion.**

### Quick wins 1 semaine (cibles 8.0/10)

1. Rotation secrets + suppression `.env` disque (30 min)
2. Cap quota beta dur (30 min)
3. SSRF whitelist (1h)
4. Prompt caching `ephemeral` (2h)
5. Pool DB PostgreSQL (30 min)
6. Pre-warm SentenceTransformer + Qdrant (2h)
7. Streaming SSE sur `/ask` (1j)
8. Payload index Qdrant + TextIndexParams (2h)
9. Sentry SDK Python + RN (4h)
10. Helper `extract_json_from_claude()` (4h)
11. Fix safe area iOS notch (30 min)
12. TextInput focus ring (45 min)
13. Cap quota free + paywall progressif (1j)
14. CI GitHub Actions bloquante (1j)
15. Eval set 50 Q/A gold + script `eval.py` (2j)

**Total : 7-8 jours dev concentré → 6.6/10 → 8.0/10 = RELEASE-READY**

---

## Historique sessions récentes (2026-05-02 → 2026-05-03)

### Ce qui a été fait

- **Lecture exhaustive** : backend (3045 L main.py, 28 endpoints, 19 features), mobile (33 écrans, 15K LOC), RAG (9 alternatives, 3,49M chunks Qdrant), scrapers (20 sources), Stripe (7 plans).
- **6 bugs P0 vérifiés** : tous déjà corrigés dans la branche WIP `wip/2026-05-02-avant-fixes-p0` (hash 49db384). Aucun fix supplémentaire nécessaire.
- **Audit exhaustif 6 angles** : security-auditor, performance-engineer, architect-reviewer, accessibility-tester, product-manager, ai-engineer — score moyen 6.6/10.
- **CLAUDE.md enrichi** : audit complet ajouté (commit 35bb755), ChromaDB → Qdrant corrigé partout, historique sessions ajouté.
- **CLAUDE.md global enrichi** : Règle 9 "commit après chaque modif" ajoutée.
- **Hook Règle 9** : PostToolUse hook ajouté dans `~/.claude/settings.json` — rappel automatique git commit après Edit/Write.

### État Git

- Branche principale : `main`
- Branche WIP sauvegarde : `wip/2026-05-02-avant-fixes-p0` (138 fichiers modifiés, ~16K lignes)
- Dernier commit audit : 35bb755 (`docs: audit exhaustif multi-angles 2026-05-02`)

### Vrai DB vectorielle en prod

**Qdrant** (pas ChromaDB). `rag/indexer_qdrant.py` est le fichier actif. `rag/indexer.py` (ChromaDB) = legacy non utilisé → à supprimer ou archiver.

### Prochaines actions prioritaires (dans l'ordre)

1. Rotation secrets `.env` (Stripe live + Anthropic + JWT) → Railway env vars
2. Cap quota beta dur (50 req/mois free)
3. SSRF whitelist sur `/student/lms/connect`
4. Prompt caching `ephemeral` Anthropic (économie 30-80€/mois)
5. Pool DB PostgreSQL (asyncpg ou `pool_size` SQLAlchemy)
6. Streaming SSE `/ask` (UX 12s → <3s perceived)
7. Sentry SDK Python + React Native
8. Eval set 50 Q/A gold standard + `eval.py`
