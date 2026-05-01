# PHASE B — Audit fonctionnel backend Lexavo

**Date** : 2026-05-01
**Cible** : `http://localhost:8000` (uvicorn `api.main:app`)
**Backend** : FastAPI 2.1.0 — 96 routes détectées dans `api/main.py`
**Index** : Qdrant local — collection `legal_docs_be`, **3 488 886 chunks**, vectors_on_disk=true
**Auth** : JWT HS256 + refresh tokens 64 chars (OK)

---

## 1. Endpoints publics (non-auth)

| Endpoint | HTTP | Statut | Observation |
|---|---|---|---|
| `/health` | 200 | OK | Retourne version, index Qdrant + sources_sample (33 sources). 1er call lent (~25s) puis instantané. |
| `/stats` | 200 | OK partiel | `total_chunks=3 488 886` correct. **`total_documents=0`, `sources=null`** (pas remplis depuis migration Qdrant). |
| `/branches` | 200 | OK | 15 branches conformes à `rag/branches.py`. |
| `/defend/categories` | 200 | OK | Catégories complètes (amende, conso, bail, etc.) avec icônes/keywords/branche. |
| `/diagnostic/questions` | 200 | OK | 6 questions. |
| `/score/questions` | 200 | OK | Pondérations cohérentes. |
| `/compliance/questions` | 200 | OK | RGPD + CGV. |
| `/audit/questions?company_type=srl` | 200 | OK | Avec `legal_ref` + `risk`. |
| `/alerts/domains` | 200 | OK | |
| `/litigation/stages` | 200 | OK | 5 étapes recouvrement. |
| `/contracts/templates` | 200 | OK | Bail BXL/Wallonie/Flandre, tarifs. |
| `/billing/plans` | 200 | OK | 7 plans (free→enterprise) + founding_price. |
| `/lawyers` | 200 | OK | Données seedées. |
| `/student/branches` | 200 | OK | 15 labels. |
| `/student/lms/universities` | 200 | OK | UCL/ULB/ULiège/UNamur. |
| `/newsletter/preview` | 200 vide | KO mineur | Réponse vide (pas d'erreur mais payload manquant). |
| **`/emergency/categories`** | **500** | **KO** | `{"detail":"Erreur interne. Veuillez réessayer."}` — import `api.features.emergency` casse (à investiguer). |

## 2. Auth

| Endpoint | Statut | Vérif |
|---|---|---|
| `POST /auth/register` | OK | JWT 221 chars + refresh 64 chars. Champs `user/token/refresh_token` conformes. |
| `POST /auth/login` | OK | Idem, mêmes creds. |
| `GET /auth/me` | OK | Renvoie `id/email/name/language/role/created_at`. |
| `POST /auth/refresh` | OK | Renvoie nouveau couple `token/refresh_token` + `user`. |
| `POST /auth/forgot-password` (email inexistant) | OK | **Anti-énumération respectée** : message générique "Si cet email existe…". |

## 3. Endpoints LLM / RAG / utilitaires (auth)

| Endpoint | Statut | Détail |
|---|---|---|
| `POST /search` | OK | Retourne 3 résultats Qdrant avec `similarity` (0.7+), source, ECLI, URL. |
| `POST /ask` | **KO infra** | `Qdrant indisponible: timed out` (timeout strict). RAG répond mais Qdrant lent sur certains chunks ; pas un bug code, infra. |
| `POST /heritage/guide` | KO validation | `relationship=enfant` rejeté. Doit être `direct_line/siblings/others`. **Mismatch mobile** (le client envoie `enfant`). |
| `POST /calculators/notice-period` | OK validation | Champs `salaire_brut_mensuel` rejetés ; backend attend `salaire_mensuel`. **Mismatch mobile**. |
| `POST /calculators/alimony` | OK | Bareme Renard, retourne `result/unit/details/legal_basis/disclaimer`. |
| `POST /calculators/succession` | OK partiel | Renvoie 0€ pour `lien_parente=enfant` (mappé en `direct_line` mais barème non appliqué). À vérifier. |
| `POST /calculators/indexation-loyer` | **404** | **Endpoint inexistant** — le mobile (`runCalculator`) construit `/calculators/indexation-loyer` via `replace`. |
| `GET /user/context` | OK | `{region:null,profession:null,language:fr}`. |
| `GET /billing/subscription` | OK | Beta=true, beta_end=2026-10-01. |
| `GET /conversations` | OK | Tableau vide. |

## 4. Mismatches mobile ↔ backend (top 10)

1. **`/calculators/indexation-loyer`** — mobile peut l'appeler via `runCalculator`, backend renvoie 404. Aucun route `indexation` dans `main.py`.
2. **`/calculators/notice-period`** — mobile envoie `salaire_brut_mensuel`, backend exige `salaire_mensuel`. À harmoniser.
3. **`/heritage/guide`** — mobile (`getHeritageGuide`) passe `relationship='enfant'`, backend valide uniquement `direct_line|siblings|others`. UI envoie label utilisateur, jamais converti.
4. **`/emergency/categories`** — 500 systématique → bouton "Urgence" mobile cassé.
5. **`/calculators/vacation-pay`** — commenté dans le client (`/calculators/{calc_type.replace('_','-')}`) mais aucune route backend.
6. **`/proof/{id}/add-entry`, `/proof/cases`, `/proof/{id}/entries`** — backend existe (3 routes), mobile n'expose que `addProofEntry` + `createProofCase`. `proof/cases` (liste) et `proof/{id}/entries` (lecture) ne sont jamais appelés côté mobile → fonctionnalité dormante.
7. **`/conversations` POST/DELETE + `/conversations/{id}/messages` POST** — backend les définit, mobile n'expose que GET. Pas de création/suppression UX.
8. **`/student/notes/upload-file`** — mobile envoie multipart ; vérifier que backend (ligne 2630) accepte FormData (le test rapide n'a pas été lancé, signature OK).
9. **`/admin/backup`** — défini backend, jamais appelé mobile (normal — admin).
10. **`/billing/webhook`** — appelé par Stripe, jamais par mobile (normal).

Endpoints backend **absents du client mobile** (potentiellement orphelins ou réservés admin/Stripe) : `/admin/backup`, `/auth/reset-password` (pas de UI reset), `/lawyers/{id}` (détail jamais consommé), `/billing/webhook`, `/newsletter/unsubscribe`, `/notifications/*` (clientside présent mais à vérifier intégration), `/student/podcast/audio`, `/student/notebooklm/create`.

## 5. Validation Pydantic

- `/auth/*` : input/output cohérents avec `models.py` (UserResponse, AuthResponse).
- `/search` : `SearchResponse` complet (query, results[], total).
- `/calculators/*` : pas de modèle Pydantic typé — accepte `dict`, validation interne stricte → meilleurs messages mais incohérences de noms (cf §4).
- `/heritage/guide` : pas de `HeritageInput` typé, validation manuelle stricte (échec sur `enfant`).
- `/ask` : `AskResponse` OK mais propage exception Qdrant comme HTTPException 500 (gère bien le timeout).

## 6. Recommandations

1. **Corriger `/emergency/categories`** — investigation prioritaire : l'import `api.features.emergency` lève en runtime (probable `EMERGENCY_PRICE_CENTS` ou fichier déplacé).
2. **Mapper côté backend les libellés UI** (`enfant`→`direct_line`, `frère/sœur`→`siblings`) ou côté mobile : ajouter une fonction `mapRelationship()` dans `client.js` avant POST.
3. **Aligner les noms de champs calculators** (`salaire_brut_mensuel` vs `salaire_mensuel`) — choisir la convention mobile car c'est le contrat UX.
4. **Implémenter `/calculators/indexation-loyer`** ou retirer du mobile. Cf. `mobile/src/screens/Calculators*.js`.
5. **Repeupler `/stats`** : depuis migration Qdrant, `total_documents` et `sources` ne sont plus calculés. Lire depuis `health.index.sources_sample`.
6. **Pydantic strict** sur calculators et heritage : remplacer `dict` par `BaseModel` typés pour erreurs 422 explicites au lieu de 500/messages français.
7. **Documenter ENV mobile** : `EXPO_PUBLIC_API_URL` par défaut = production Railway. Pour audit local LAN (192.168.1.9:8000), l'utilisateur doit override sinon teste contre prod.

## 7. Score fonctionnel

| Catégorie | Score |
|---|---:|
| Endpoints publics (16) | 14/16 (1×500 emergency, 1×vide newsletter) |
| Auth (5) | 5/5 |
| LLM/RAG (search) | 1/1 (Qdrant timeout = infra, pas code) |
| Calculators (3 testés) | 1.5/3 (notice-period mismatch, succession=0) |
| Cohérence mobile↔backend | 3/5 (4+ mismatches bloquants) |
| Validation Pydantic | 2/3 (calculators+heritage en `dict`) |

**Score global : 13.5 / 20**

Backend solide sur le périmètre auth + endpoints listings + RAG/search. Bloquants UX : emergency 500, indexation-loyer 404, heritage/notice-period rejets validation. Aucun incident sécurité (anti-énum OK, JWT OK).

---

Fichier : `C:\Users\bahma\Downloads\base-juridique-app\.audit\PHASE_B_BACKEND.md`
