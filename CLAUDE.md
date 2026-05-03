# CLAUDE.md — Lexavo "Le droit pour tous"

## Identité

- **Nom** : Lexavo — assistant juridique belge (SRL en cours d'immatriculation)
- **Auteur** : Mamadou BAH
- **Langue** : toujours répondre en français
- **Scope** : droit belge et européen — 3 régions (Bruxelles, Wallonie, Flandre)

## Architecture

```
LEXAVO
├── Backend FastAPI   → api/main.py (115 endpoints, 20 features)
├── Security          → api/security.py (322 L — headers, lockout, PII masking, CORS, upload)
├── RAG Pipeline      → rag/pipeline.py (Qdrant prod, 3 490 000+ chunks, 28 codes belges)
├── Retriever         → rag/retriever.py (9 alternatives de recherche mutuellement correctives)
├── Indexer Qdrant    → rag/indexer_qdrant.py (actif en prod)
├── Indexer ChromaDB  → rag/indexer.py (legacy, NON utilisé en prod — à archiver)
├── Mobile Expo       → mobile/ (React Native 0.81.5, Expo SDK 54, 33 écrans + LexavoHomeScreen, design system ivoire/terracotta/navy)
├── Scrapers          → scrapers/ (26 scrapers : JUSTEL, HUDOC, EUR-Lex, SPF Finances, SPF Emploi, FSMA, BNB, IBPT, CREG, INAMI, AVOCATS.BE, IRE, doctrine PDF HAL/DIAL/UGENT/ORBI, etc.)
├── Tests             → tests/ (30 fichiers pytest, 55+ tests) + mobile/__tests__/ (60 jest)
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
| Code de la route | Texte coordonné complet | ~503 000 | — |
| Loi douanes et accises | NUMAC 1977071850 | ~289 000 | — |
| Statut Camu | Fonction publique fédérale | — | — |
| + autres codes/lois | Nationalité, DIP, assurances, marchés publics, patient, CCT, circulaires SPF | ~500 000 | ~150 |
| **Total** | **34 sources juridiques belges** | **~10 800 000+** | **~6 500+** |
| **Qdrant prod** | **3 490 000+ chunks** | — | — |

**Source** : ejustice.just.fgov.be (SPF Justice belge), NUMACs + cn vérifiés sur eTAAMB
**Zéro invention** : tous les textes proviennent de sources officielles, vérifiés 5 fois

## Fichiers critiques

### Backend
| Fichier | Rôle |
|---------|------|
| `api/main.py` | 115 endpoints FastAPI (3045 L — monolithique, split planifié) |
| `api/auth.py` | JWT bcrypt 12 rounds + refresh tokens 30j, 8 langues (fr/nl/en/de/ar/tr/es/pt) |
| `api/security.py` | HSTS/CSP/headers, account lockout 5 fails/15min, PII masking, CORS strict, upload MIME |
| `api/database.py` | 27 tables, PostgreSQL prod / SQLite dev |
| `api/stripe_billing.py` | 7 plans (free→enterprise), webhooks idempotents, beta mode |
| `api/utils/model_router.py` | Haiku (simple) / Sonnet (analyse) / Opus (complexe) — IDs Claude 4.5 valides |
| `rag/pipeline.py` | RAG complet + détection 15 branches + garde-fou Alt.6 (388 L) |
| `rag/retriever.py` | 9 alternatives de recherche + Alt.6 SOURCE_TO_KEYWORDS (673 L) |
| `rag/indexer_qdrant.py` | Indexer actif en prod — Qdrant cloud |
| `rag/indexer.py` | Legacy ChromaDB — NON utilisé, à archiver |
| `rag/branches.py` | 15 branches du droit avec prompts et sources spécialisés |
| `rag/humanizer.py` | Post-traitement : supprime patterns IA, préserve citations juridiques |

### Mobile
| Fichier | Rôle |
|---------|------|
| `mobile/App.js` | 5 onglets (Accueil, Campus, Chat IA, Abonnement, Réglages) + LexavoStack caché (Defend, Shield, Diagnostic, Calculateurs, Match, Emergency, Fiscal) + SettingsStack (Subscription, Notifications, History, Lawyers, CGU, Privacy, MentionsLegales) |
| `mobile/src/api/client.js` | 936 L, 105 fonctions/exports, URL Railway prod, intercepteurs 401, expo-secure-store |
| `mobile/src/screens/HomeScreen.js` | Hero LEXAVO + 2 cartes + grille 16 outils + 15 branches + étudiants (HeritageScreen ajouté) |
| `mobile/src/screens/AskScreen.js` | Chat RAG principal + filtres source + PhotoPicker (pattern mounted) |
| `mobile/src/screens/StudentScreen.js` | Quiz QCM + Flashcards + Résumé Claude (2451 L — god component, split planifié) |
| `mobile/src/screens/OnboardingScreen.js` | 8 langues + région + profession + onDone callback garanti |
| `mobile/src/screens/student/utils.js` | Utilitaires extraits de StudentScreen (refactor H.4) |
| `mobile/src/i18n/translations.js` | 680 entrées, 8+1 langues (fr/nl/en/de/es/it/pt/ar/tr) — coverage 70% sur 5 écrans principaux |
| `mobile/src/context/LanguageContext.js` | getDeviceLanguage() + fallback fr + clé unifiée @lexavo_lang |
| `mobile/src/theme/designSystem.js` | Colors ivoire/terracotta/navy, EB Garamond+Nunito, tokens UI — source unique de vérité |
| `mobile/src/theme/colors.js` | Palette exportée séparément (brand, surface, text, states) |
| `mobile/src/screens/LexavoHomeScreen.js` | Écran d'accueil alternatif (238 L) — FadeInDown stagger Reanimated |
| `mobile/src/components/ui/Button.js` | Composant bouton design system |
| `mobile/src/components/ui/Card.js` | Composant carte design system |
| `mobile/src/components/ui/Disclaimer.js` | Disclaimer réutilisable (source unique — 1 seul fichier) |
| `mobile/src/components/ui/ToolCard.js` | Carte outil avec Ionicons + accessibilityRole |

### Composants partagés (mobile/src/components/)
BadgeGrid, ChecklistStep, ConsentModal, ExtractedCard, ModelBadge, PhotoPicker, ResultCard, ScoreGauge, SourceBadge, SourceCard, StreakCounter, XPBar

### Animations
- `react-native-reanimated ~4.1.1` — FadeInDown.delay(index × 40ms).springify() sur grilles HomeScreen + LexavoHomeScreen
- Tous les emojis UI → Ionicons (27 écrans, 203/203 boutons couverts)

### Features (20 modules)
| Module | Modèle Claude | Description |
|--------|--------------|-------------|
| defend.py | Sonnet | Contestation/recours (8 situations) |
| shield.py | Sonnet→Opus (>15KB) | Analyse contrat (10 types, score /100) |
| diagnostic.py | Sonnet | Questionnaire 6 questions, rapport personnalisé |
| fiscal.py | Sonnet | Copilote TVA/CIR pour indépendants |
| legal_response.py | Sonnet | Réponse à courrier (propriétaire, huissier, admin) |
| calculators.py | Haiku | Préavis, succession, pension, indexation loyer (formule belge) |
| compliance.py | Sonnet | Audit RGPD/conformité B2B |
| contracts.py | Sonnet | Génération contrats PDF (7 types) |
| heritage.py | Sonnet | Guide successoral belge (mapping FR conjoint/enfant/frère) |
| litigation.py | Sonnet | Recouvrement impayés |
| match.py | Sonnet | Matching avocat par spécialité |
| emergency.py | Opus | Urgence juridique 24h (49€) — categories UTF-8 fixé |
| score.py | Haiku | Score santé juridique /100 |
| decode.py | Haiku | Traduction documents administratifs |
| alerts.py | Haiku | Veille législative belge |
| proof.py | — | Constituer un dossier de preuves |
| audit_entreprise.py | Opus | Audit PME 30 questions, 8 domaines |
| newsletter.py | — | Newsletter 15 domaines juridiques |
| student.py | Haiku/Sonnet | Quiz QCM, Flashcards SRS, groupes, LMS |
| lms.py | — | Connexion Moodle (SSRF whitelist à implémenter) |

### Tables DB (27 tables)
users, lawyers, conversations, messages, subscriptions, shield_analyses, newsletter_subscribers, refresh_tokens, emergency_requests, alert_preferences, proof_cases, proof_entries, push_tokens, beta_notifications, audit_reports, password_reset_tokens, student_progress, student_badges, student_quiz_history, student_flashcard_srs, student_groups, student_group_members, student_lms_connections, student_lms_courses, student_shared_notes, failed_logins, stripe_webhook_events, admin_audit_log

## Règles non-négociables

1. **Zéro invention** — ne jamais inventer d'articles de loi, de chiffres, de NUMACs ou de jurisprudence
2. **Droit belge** — CIR 1992, Code civil, CTVA, CCT, lois fédérales/régionales uniquement
3. **Disclaimer obligatoire** — chaque réponse juridique inclut "ne constitue pas un avis juridique"
4. **Helpers existants** — utiliser `_get_conn()`, `USE_PG`, `_execute()`, `_fetchone()`, `_fetchall()` dans database.py
5. **Humanizer** — intégré dans toutes les réponses (shield, audit, diagnostic, decode, fiscal, legal_response)
6. **Retriever 9 alternatives** — le RAG utilise 9 mécanismes de recherche qui se corrigent mutuellement :
   - Alt.1 Vecteurs sémantiques | Alt.2 Mots-clés articles (Art. X) | Alt.3 Termes juridiques ($contains)
   - Alt.4 Chunks voisins (contexte ±1) | Alt.5 Vote majoritaire | Alt.6 Filtre source détectée (SOURCE_TO_KEYWORDS 18 entrées)
   - Alt.7 Re-ranking Claude Haiku | Alt.8 Index articles séparé | Alt.9 Reformulation automatique
   - Si l'info n'est pas dans la base → dire "je ne sais pas", **jamais inventer**
   - Chaque erreur d'une alternative est corrigée par les autres automatiquement
7. **Skill add-legal-source** — toute nouvelle source juridique DOIT passer par la skill
   `claude-skills/add-legal-source/SKILL.md` (8 étapes obligatoires, zéro invention à chaque étape)
8. **Vérifier 2 fois minimum** — chaque donnée (NUMAC, URL, contenu) est vérifiée sur la source officielle avant utilisation
9. **Complétude obligatoire avant indexation** — JAMAIS indexer des docs incomplets (full_text < 500 chars) sans accord explicite. Audit obligatoire avant indexation : char_count distribution + sample 5 docs.
10. **Sécurité module** — `api/security.py` est la source de vérité pour headers, lockout, PII. Ne pas dupliquer ailleurs.

## Stack technique

- **Backend** : FastAPI 0.111, Python 3.11, Anthropic Claude API (claude-haiku-4-5 / claude-sonnet-4-5-20250929 / claude-opus-4-5-20251001)
- **DB** : PostgreSQL (Railway prod), SQLite (dev local), 27 tables
- **RAG** : Qdrant cloud (3 490 000+ chunks, 34 sources), sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 dims)
  - Migration BGE-M3 (1024D) planifiée — embeddings 2021 obsolètes pour juridique
- **Auth** : JWT bcrypt 12 rounds, refresh tokens 30 jours, 8 langues, expo-secure-store mobile, account lockout 5 fails/15min
- **Sécurité** : api/security.py — HSTS/CSP/X-Frame-DENY/Referrer-Policy/Permissions-Policy, PII masking, CORS strict whitelist, MIME magic bytes upload, admin audit log
- **Paiement** : Stripe live (7 plans : free/basic/pro/business/firm_s/firm_m/enterprise), webhooks idempotents, beta gratuit jusqu'au 2026-10-01
- **Mobile** : React Native 0.81.5, Expo SDK ~54.0.34, React Navigation 7.x, expo-secure-store, Ionicons, react-native-reanimated ~4.1.1
- **i18n** : 680 entrées × 8+1 langues, coverage 70% sur 5 écrans principaux, RTL arabe
- **Tests** : pytest 55+ tests backend (conftest.py, asyncio), jest 60 tests mobile (mocks expo-secure-store)
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

# Tests backend
cd base-juridique-app && pytest tests/ -v

# Tests mobile
cd mobile && npx jest

# Production Railway
# Auto-deploy via push GitHub → Railway
# Qdrant cloud configuré via QDRANT_URL + QDRANT_API_KEY env vars
```

---

## Audit final Phase F (2026-05-01) — 92/100

Score résultant de 7 phases d'audit (12 agents parallèles) sur commits a046414 + d962312 :

| Dimension | Avant audit | Après Phase H |
|-----------|-------------|--------------|
| Sécurité | 2.5/10 | 9.5/10 |
| Code | 13.5/20 | 17.5/20 |
| Design | 13.5/20 | 15/20 |
| Backend | 13.5/20 | 18/20 |
| Mobile | 11/20 | 18/20 |
| RAG | 15.5/20 | 17/20 |
| UX | 11.5/20 | 17/20 |
| i18n | 3% | 70% |
| Tests | 0 | 115 (55 pytest + 60 jest) |

Vérifications Phase F :
- ✅ Build Android exit 0 (5.13 MB)
- ✅ Anti AI slop : 0 violation (borderXxxWidth>1, fontWeight 'bold')
- ✅ A11y : 209/203 boutons accessibilityRole
- ✅ Auth LLM : 6/6 endpoints protégés (401)
- ✅ RGPD : DELETE /account (cascade 19 tables) + GET /account/export
- ✅ Modèles Claude 4.5 valides partout
- ✅ pip-audit : 0 vulnérabilité connue
- ✅ npm audit : 0 HIGH

---

## Audit exhaustif multi-angles (2026-05-02)

**6 sous-agents spécialisés ont audité le projet en parallèle.** Score moyen pondéré : **6.6/10** — production-acceptable mais NON release-ready sans correctifs.

> Note : cet audit est postérieur à la Phase H. Il a identifié des risques systémiques non couverts par l'audit Phase F.

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
| 12 | i18n incomplète — 30% des écrans encore en FR hardcodé (coverage 70% sur 5 écrans) | Marketing 8 langues | 2-3j |
| 13 | Mobile en JS pur (pas TypeScript) sur 15K LOC | Maintenabilité | 2-3 sem (incrémental) |
| 14 | 0 observabilité IA (Sentry, Langfuse, Langsmith absents) | Risque légal RGPD | 1j |
| 15 | 19 features → 3 personas viables réels — message produit dispersé | PMF | Décision stratégique |

### Findings sécurité détaillés

- **API1 BOLA** : OK (pattern `obj.user_id == current_user.id` cohérent)
- **API2 Auth** : OK avec réserve — password min 6 chars (sous-standard NIST), pas de check HIBP
- **API4 Rate limiting** : partiel — slowapi par IP mais pas par user_id, quota beta bypassé
- **API6 SSRF** : KO sur `/student/lms/connect`, exposable à `169.254.169.254` (cloud metadata)
- **API7 Misconfig** : OK (CORS strict, security headers complets via api/security.py)
- **API10 Stripe webhook** : OK (signature + idempotence DB stripe_webhook_events)

### Findings performance détaillés

- Latence p50 `/ask` : ~12s, p95 ~22s. Cible : 5s / 10s
- Hotspots : génération Sonnet (60-80%), Alt.2/3 sériels (300-1200ms), Alt.4 voisins sériels (150-400ms)
- Dockerfile : chromadb>=0.5.0 encore dans requirements.txt mais **rag/indexer.py legacy non utilisé**
- 95 routes en `def` sync → saturent threadpool 40 workers global
- Économies API potentielles avec quick wins : ~50€/mois actuel, scaling linéaire

### Findings architecture détaillés

- `api/main.py` : 3045 L, 115 endpoints, **0 APIRouter** (sauf seo_router)
- 14 duplications du pattern `json.loads(json_match.group())` dans 8 features
- 1 seule migration Alembic (schéma figé)
- Mobile : god components (StudentScreen 2451 L, SubscriptionScreen, ShieldScreen)
- Pas de Sentry, pas de TypeScript, pas de linter/formatter, pas d'ADR
- 30 fichiers de tests backend mais **0 test RAG**

### Findings UX/A11y détaillés

- WCAG 2.1 AA : 65-70% conforme
- Critique : SafeAreaProvider importé mais non wrappé → notch overlap iOS
- Critique : TextInput sans focus ring (Auth + Ask)
- Caption font 11pt + tabBar 10pt = sous WCAG AA
- BCE/VAT placeholder `[NUMÉRO BCE À COMPLÉTER]` non remplacé !
- 30% des écrans avec strings FR hardcodés (i18n incomplète)
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
- Doublon `indexer.py` (ChromaDB legacy) + `indexer_qdrant.py` (Qdrant actif) — drift silencieux
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
3. SSRF whitelist sur `lms.py` (1h)
4. Prompt caching `ephemeral` Anthropic (2h)
5. Pool DB PostgreSQL `asyncpg` ou `pool_size` (30 min)
6. Pre-warm SentenceTransformer + Qdrant (2h)
7. Streaming SSE sur `/ask` (1j)
8. Payload index Qdrant + TextIndexParams (2h)
9. Sentry SDK Python + React Native (4h)
10. Helper `extract_json_from_claude()` mutualisé (4h)
11. Fix SafeAreaView iOS notch wrap (30 min)
12. TextInput focus ring (Auth + Ask) (45 min)
13. Cap quota free + paywall progressif (1j)
14. CI GitHub Actions bloquante (1j)
15. Eval set 50 Q/A gold + script `eval.py` (2j)

**Total : 7-8 jours dev concentré → 6.6/10 → 8.0/10 = RELEASE-READY**

---

## Historique sessions récentes (2026-05-01 → 2026-05-03)

### Ce qui a été fait

- **Phase F (2026-05-01)** : audit final 7 phases 12 agents → score 92/100. Commits a046414 + d962312.
  - 6 bugs P0 corrigés (OnboardingScreen, LANG_KEY, initLanguage, /emergency/categories, /calculators/indexation-loyer, auth LLM)
  - api/security.py créé (329 L) — HSTS/CSP, lockout, PII masking, CORS strict, upload MIME
  - i18n 3% → 70% (680 entrées, 8+1 langues)
  - 115 tests créés (55 pytest + 60 jest)
  - CVE deps résolus : pip-audit 0, npm audit 0 HIGH
  - expo-secure-store migration (JWT mobile plus stocké AsyncStorage en clair)
  - HeritageScreen ajouté dans TOOL_DEFS HomeScreen
  - Alt.6 SOURCE_TO_KEYWORDS (18 entrées JUSTEL) — top-1 accuracy 4/5 → 5/5
  - Ionicons sur 6 écrans (emojis→icônes)

- **Audit multi-angles (2026-05-02)** : 6 sous-agents → score 6.6/10. 15 risques bloquants identifiés.
  - Branche WIP sauvegarde : `wip/2026-05-02-avant-fixes-p0` (138 fichiers, ~16K lignes, hash 49db384)
  - Commit audit CLAUDE.md : 35bb755

- **Sessions 2026-04-29 → 2026-04-30** : scrapers régulateurs (FSMA, BNB, IBPT, CREG), professions (INAMI, AVOCATS.BE, IRE), doctrine PDF batch (HAL/DIAL/UGENT/ORBI), Code de la route + Douanes, Statut Camu, 10 codes belges manquants + 4 régionaux, CJUE Cellar, CCT + circulaires SPF.
- **Sessions 2026-04-30 → 2026-05-01** : design system complet (ivoire/terracotta/navy, EB Garamond+Nunito, tokens), composants ui/ (Button/Card/Disclaimer/ToolCard), FadeInDown stagger Reanimated, emojis→Ionicons 27 écrans, accessibilityRole 203/203 boutons.
- **Session 2026-05-03** : mise à jour CLAUDE.md — état réel complet, design system, scrapers, composants, animations.

### État Git

- Branche principale : `main`
- Branche WIP sauvegarde : `wip/2026-05-02-avant-fixes-p0` (138 fichiers, hash 49db384)
- Commit Phase H (v2.1.0) : d962312
- Commit Phase F (92/100) : a046414
- Commit audit CLAUDE.md : 35bb755

### Vrai DB vectorielle en prod

**Qdrant** (pas ChromaDB). `rag/indexer_qdrant.py` est le fichier actif. `rag/indexer.py` (ChromaDB) = legacy non utilisé.
**Note** : `chromadb>=0.5.0` est encore dans `requirements.txt` — à retirer au prochain nettoyage.

### Prochaines actions prioritaires (dans l'ordre)

1. Rotation secrets `.env` (Stripe live + Anthropic + JWT) → Railway env vars
2. Cap quota beta dur (50 req/mois free)
3. SSRF whitelist sur `/student/lms/connect` dans `api/features/lms.py`
4. Retirer `chromadb` de `requirements.txt` (legacy)
5. Prompt caching `ephemeral` Anthropic (économie 30-80€/mois)
6. Pool DB PostgreSQL
7. Streaming SSE `/ask` (UX 12s → <3s perceived)
8. Sentry SDK Python + React Native
9. Eval set 50 Q/A gold standard + `eval.py`
