# PHASE A — Audit Code Lexavo

Auditeur : Claude (Opus 4.7) — Date : 2026-05-01
Scope : `api/`, `rag/`, `scrapers/`, `mobile/src/`
Score global : **13.5 / 20**

---

## P0 — BLOQUANTS RELEASE (corriger avant publication)

### P0-1. Modèles Claude inexistants (RAG + features)
- `api/utils/model_router.py:9-10` — `SONNET = "claude-sonnet-4-6"`, `OPUS = "claude-opus-4-6"`.
- `rag/pipeline.py:22` — `DEFAULT_MODEL = "claude-sonnet-4-6"`.
- `api/models.py:139` — défaut `"claude-sonnet-4-6"` exposé à l’API.
- **Cause** : ces IDs n’existent pas dans la nomenclature Anthropic (les versions publiées sont `claude-sonnet-4-5-20250929`, `claude-opus-4-5-20251001`, etc.). Tout appel `/ask`, `/shield/analyze`, `/defend/analyze`, `/audit/generate` lèvera une 400 « invalid model » dès la prod.
- **Fix** : remplacer par les IDs valides actuels (`claude-sonnet-4-5-20250929`, `claude-opus-4-5-20251001`) ou centraliser via une constante unique.

### P0-2. Modèle hardcodé obsolète dans audit_entreprise
- `api/features/audit_entreprise.py:314` — `model="claude-sonnet-4-20250514"` (pré-Sonnet 4.5).
- N’utilise pas `select_model("audit")` du router → contourne tout le routage Opus prévu.
- **Fix** : remplacer par `select_model("audit", text_length=...)`.

### P0-3. `expo-av` deprecated SDK 54 — fonctionnel mais à risque
- `mobile/package.json:24` — `"expo-av": "~16.0.8"` toujours déclaré.
- `mobile/src/screens/StudentScreen.js:394` — utilise `require('expo-av')` pour Audio. expo-av est marqué deprecated dans SDK 54, à supprimer en SDK 55 — le lazy require évite le crash mais la dépendance casse les builds futurs.
- **Fix** : migrer vers `expo-audio` (`npx expo install expo-audio`) avant SDK 55.

### P0-4. `process.env.EXPO_PUBLIC_PROJECT_ID` avec fallback factice
- `mobile/src/utils/notifications.js:96` — `projectId: process.env.EXPO_PUBLIC_PROJECT_ID ?? 'lexavo-app'`.
- Le fallback `'lexavo-app'` n’est pas un UUID Expo valide → `getExpoPushTokenAsync` lève en prod si la var n’est pas définie.
- **Fix** : retirer le fallback et logger une erreur claire si non défini.

---

## P1 — HAUTE PRIORITÉ

### P1-1. `useEffect` avec dep `loadDashboard` manquante
- `mobile/src/screens/StudentScreen.js:199` — `useEffect(() => { ... loadDashboard(); }, [view])` ; `loadDashboard` est un `useCallback` mais n’est pas dans les deps → warning React et re-création possible non-déclenchée.
- **Fix** : ajouter `loadDashboard` à deps array.

### P1-2. `/billing/webhook` sans signature optimale + try/except non-borné
- `api/main.py:747-756` — accepte un webhook ; vérification de signature faite par `handle_webhook` mais aucun guard ici contre payload énorme. `request.body()` non bornée → DOS possible.
- **Fix** : ajouter `Content-Length` check à 1 MB max.

### P1-3. Try/except trop larges dans le pipeline RAG
- `rag/retriever.py:230, 263, 310, 342, 386, 420` — `except Exception` qui retournent `[]`/`None` silencieusement. Une panne réseau Qdrant est avalée et apparaît comme « pas de résultat » → l’IA répond « je ne sais pas » au lieu de signaler une indisponibilité.
- **Fix** : log `error` avec stack et propager les erreurs critiques (HTTP timeouts vs MatchText non-indexé sont des cas distincts).

### P1-4. Endpoints calculateurs non-protégés
- `api/main.py:952, 966, 981` — `/calculators/notice-period`, `/alimony`, `/succession` ouverts sans `current_user`. Pas Claude donc pas cher, mais permet scraping sans quota et abus rate-limit (pas de `@limiter.limit`).
- **Fix** : ajouter au minimum un rate limit `@limiter.limit("30/minute")`.

### P1-5. Endpoints defend ouverts (`/defend/checklist`, `/defend/regenerate-letter`, `/defend/scan-amende`)
- `api/main.py:1297, 1319, 1338` — appellent Claude (Vision dans scan-amende) mais aucun `current_user` → coût illimité par IP. Rate limit présent mais aucun quota Stripe.
- **Fix** : ajouter `current_user: dict = Depends(_get_current_user)` + `check_quota`.

### P1-6. `/heritage/guide` ouvert
- `api/main.py:1591` — appelle Claude Sonnet sans auth ni quota. Coûts non contrôlés.
- **Fix** : ajouter auth + quota.

### P1-7. Long ScrollView avec maps dans HomeScreen / AskScreen
- `mobile/src/screens/HomeScreen.js:75-260` — ScrollView avec 16 outils + 15 branches en map → ré-render complet à chaque update.
- `mobile/src/screens/AskScreen.js:102-275` — historique chat dans ScrollView (devrait être FlatList avec `keyExtractor`).
- **Fix** : migrer vers FlatList + `React.memo` sur cartes.

### P1-8. CORS production permissif si var oubliée
- `api/main.py:114-116` — fallback prod restreint à `lexavo.be` mais log juste un warning. Sur Railway sans `LEXAVO_ALLOWED_ORIGINS`, ça passe silencieusement. Pas critique mais à durcir : `raise` au démarrage si `DATABASE_URL` set et origins absent.

---

## P2 — MOYENNE PRIORITÉ

### P2-1. Logique `_reduce_em_dashes` casse la sémantique
- `rag/humanizer.py:175-183` — si `dash_count > 1`, transforme `A — B — C` en `A — B, C` ce qui change le sens d’une énumération juridique. Risque de réécriture de citations.
- **Fix** : ne pas appliquer dans des paragraphes contenant un placeholder `__LEGAL_REF_*__`.

### P2-2. Code dupliqué entre features
- `api/features/shield.py`, `decode.py`, `defend.py` — pattern identique : `client.messages.create` + parse JSON + `try/except json.JSONDecodeError`. À factoriser dans `api/utils/claude_json.py`.

### P2-3. Variable d’env hardcodée
- `rag/indexer_qdrant.py:35` — `QDRANT_URL = "http://localhost:6333"` hardcodé alors que `retriever.py:39` utilise `os.getenv("QDRANT_URL")`. Incohérence.

### P2-4. Endpoints `/auth/forgot-password` log le token en clair
- `api/main.py:522` — `log.info("Password reset token pour %s : %s", body.email, token)`. Token de reset visible dans les logs Railway → fuite si logs partagés.
- **Fix** : retirer le token du log, ne logger que l’email.

### P2-5. `STUDENT_BRANCHES` dupliqué côté backend
- `api/main.py:1780-1785` — liste codée en dur. `rag/branches.py` contient déjà 15 branches. Source de vérité dédoublée.

### P2-6. Reformulation Claude Haiku appelée sur faible score sans budget
- `rag/retriever.py:551` — appel Haiku additionnel à chaque requête « difficile ». Pas de garde-fou si Anthropic 429.

### P2-7. `_articles_collection_exists()` cache global
- `rag/retriever.py:104,127` — variable globale, pas thread-safe sous gunicorn workers. Côté FastAPI/uvicorn workers fork : faible risque mais à connaître.

### P2-8. `verify_citations` trop permissive
- `rag/pipeline.py:88-97` — compte `[1]/[2]` comme « vérifiées » dès qu’elles pointent dans `len(sources)`. Ne valide pas que la citation correspond au contenu réel — donne un faux signal de fiabilité.

---

## P3 — BASSE PRIORITÉ / DETTE

- `_tmp_*.py` (10 fichiers à la racine) + `Dockerfile.bak` + `pipeline.py` (root) → dead code à supprimer.
- `api/main.py` (2837 lignes) → splitter en routers FastAPI par domaine (`student.py`, `billing.py`, `defend.py`, `student_lms.py`).
- `mobile/src/screens/StudentScreen.js` (2451 lignes, 40+ states) → god component, à splitter par mode (Quiz, Flashcards, Podcast, Exam, Notes, LMS).
- `_tmp_audit_qdrant.py`, `audit_sources.py`, `audit_regles_or.py` à déplacer dans `scripts/`.
- Strings magiques `'@lexavo_*'` dans plusieurs écrans → centraliser dans `mobile/src/constants/storage.js`.
- `STOPWORDS_FR` dans `retriever.py:94` est très court, manque "comment", "lorsque", "selon".

---

## Score Code Quality : 13.5 / 20

| Axe | Note | Justification |
|---|---:|---|
| Correctness | 2 / 4 | Modèles Claude inexistants (P0-1/2) = bloquant |
| Sécurité | 2.5 / 4 | Endpoints calculateurs/heritage/defend ouverts ; reset token loggé |
| Architecture | 3 / 4 | RAG 9 alternatives bien conçu ; humanizer protège refs ; main.py monolithe |
| Performance | 2 / 4 | ScrollView au lieu de FlatList ; reformulation systématique sans budget |
| Lisibilité | 4 / 4 | Bonne docstring, conventions FR cohérentes, séparation features/utils |

---

## 5 ACTIONS PRIORITAIRES

1. **Corriger les IDs de modèles Claude** (`model_router.py`, `pipeline.py`, `models.py`, `audit_entreprise.py:314`) — sinon **tous les endpoints LLM échouent en prod**.
2. **Auth + quota sur `/calculators/*`, `/heritage/guide`, `/defend/checklist`, `/defend/scan-amende`, `/defend/regenerate-letter`** — coûts illimités actuellement.
3. **Retirer le fallback `'lexavo-app'` du `EXPO_PUBLIC_PROJECT_ID`** + définir la var dans `app.json/extra` ou `eas.json`.
4. **Ne plus logger le reset token** (`api/main.py:522`) — fuite RGPD.
5. **Migrer expo-av → expo-audio** avant SDK 55, et FlatList sur HomeScreen/AskScreen pour fluidité.
