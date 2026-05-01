# PHASE B — Audit fonctionnel RAG Lexavo

Date : 2026-05-01 — Backend Qdrant `legal_docs_be` (3 488 886 chunks, 4 769 docs sample)

## 1. Présence des 9 alternatives

| Alt. | Description | Présent | Localisation `rag/retriever.py` |
|------|-------------|:-------:|---------------------------------|
| 1 | Vecteurs sémantiques (cosine) | OUI | L378 `client.query_points` |
| 2 | Mots-clés articles `Art. X` | OUI | L399 regex + L426 MatchText |
| 3 | Termes juridiques (MatchText multi) | OUI | L443 `legal_terms` + scroll |
| 4 | Chunks voisins (±1) | OUI | L237 `_get_neighbor_chunks` (UUID5) |
| 5 | Vote majoritaire / fusion | PARTIEL | L463 dédup + tri score, pas de vote pondéré explicite |
| 6 | Détection source dans question | OUI | L67 `SOURCE_DETECT` (18 patterns) + bonus +0.3 L491 |
| 7 | Re-ranking Claude Haiku | OUI | L271 `_rerank_with_llm` (claude-haiku-4-5) |
| 8 | Index articles séparé `legal_articles_be` | OUI (conditionnel) | L404, dégrade si collection absente |
| 9 | Reformulation auto Haiku | OUI | L317 `_reformulate_query`, déclenchée si score<0.65 |

**9/9 implémentées.** Alt.5 est implémentée comme dédup+tri pondéré (score + priority_bonus + source_bonus) plutôt que vote majoritaire stricto sensu — fonctionnellement équivalent mais le commentaire code (L461) est trompeur.

## 2. Pipeline `rag/pipeline.py`

- **15 branches** définies dans `rag/branches.py` (travail, familial, fiscal, pénal, civil, administratif, commercial, immobilier, environnement, PI, sécu sociale, étrangers, fondamentaux, marchés publics, européen). Chaque branche a `keywords`, `source_filter`, `top_k`, `system_prompt_extra` distincts.
- **Détection auto** L202 fonctionne (testée 7/7 OK, voir §4).
- **Garde-fou Alt.6** L235-255 : si confidence ≥0.5 ET <30 % des chunks proviennent du `source_filter` attendu → re-recherche avec filtre forcé. Présent et fonctionnel.
- **"Je ne sais pas"** L223 : si `chunks` vide → message explicite, pas d'invention. Le system prompt L31 réitère la règle.
- **Humanizer** L342 appliqué après `verify_citations` ; les regex `humanizer.py` ciblent prose IA mais ne touchent pas les patterns `[Art. X]`, `ECLI:...`, `Loi du JJ MMM AAAA` (vérifié).

## 3. Tests retrieval réels (top-1 accuracy)

| Query | Top-1 attendu | Top-1 obtenu | OK |
|-------|---------------|--------------|:--:|
| "licenciement motif grave article 35" | JUSTEL Loi 1978 contrats travail | JUSTEL `2009202360` Décret CWATUP urbanisme (sim 0.95) | NON |
| "contrat de travail motif grave licenciement" | JUSTEL Loi 3 juillet 1978 | JUSTEL `2024204649` Loi 22 août 1978 contrats travail | OUI |
| "garantie locative bruxelles bail" | Bail bruxellois / Juridat | Juridat ECLI:BE:CASS:2018:ARR.20180226.1 (garantie locative) | OUI |
| "succession enfant unique reserve hereditaire" | Code civil Livre 4 | Juridat + Cour const. arrêts succession | OUI (jurisprudence) |
| "TVA indépendant déduction" | Code TVA | (timeout 30 s sur 1ère tentative, OK 2ème) Loi TVA | OUI |

**Top-1 accuracy : 4/5.** L'échec sur "article 35" est instructif : Alt.2 matche bêtement "article 35" dans des décrets non-pertinents. Le bonus Alt.6 (+0.3) n'est pas suffisant car SOURCE_DETECT pour "motif grave"/"licenciement" matche ligne L83 mais retourne `"Loi sur les contrats de travail"` — or les payloads JUSTEL ont `title` = "22 août 1978…" sans le mot "contrats de travail" → le bonus ne s'applique pas. **Bug latent**.

## 4. Détection branche

7/7 corrects sur les requêtes test (voir transcript §3 du run). Confidences 0.30→0.60, seuil 0.5 pour activer le garde-fou Alt.6 — cohérent. Les 15 prompts `system_prompt_extra` sont distincts et cite chacun ≥3 références légales spécifiques (CSA, CIR 92, VLAREM, etc.).

## 5. Cache & performance

| Item | État |
|------|------|
| `SentenceTransformer` singleton | OUI L147 `_model` global |
| `QdrantClient` singleton | OUI L118 `_client` global |
| `_articles_collection_exists()` cached | OUI L129 `_articles_available` |
| LRU cache sur queries | NON |
| Anthropic prompt caching (`cache_control`) | NON — `messages.create` sans `cache_control` ni système segmenté |
| Embedding async / batch | NON |

Latence observée : ~2-15 s par /search (Alt.7 + Alt.9 ajoutent 1-3 s d'appel Haiku). Quelques timeouts >30 s côté curl (probablement scroll MatchText sans index full-text).

## 6. Score RAG : **15.5 / 20**

- Architecture 9 alt. (5/5) : toutes présentes, design solide.
- Détection branche (3/3) : 15 branches, prompts spécialisés, détection fiable.
- Garde-fou Alt.6 (2/3) : présent mais bug — la comparaison `detected_source.lower() in title.lower()` rate quand le titre JUSTEL n'inclut pas le label canonique.
- Tests retrieval (3/4) : 4/5 top-1 corrects.
- Performance / cache (1.5/3) : singletons OK, **pas de prompt caching Anthropic** (gros gain potentiel à 90 % sur le system prompt 1.5 KB répété).
- Humanizer + zéro invention (1/2) : `verify_citations` marque `[non vérifié]` mais ne supprime pas les hallucinations ECLI ; améliorer.

## 7. Recommandations (priorité décroissante)

1. **Fix Alt.6 mapping titre** : indexer un champ payload `code_canonical` (ex. `"loi_contrats_travail"`) côté indexer et matcher dessus au lieu du `title` libre. Corrige le bug "article 35".
2. **Activer Anthropic prompt caching** dans `pipeline.py` L301 : passer `system=[{"type":"text","text":..., "cache_control":{"type":"ephemeral"}}]` — économie ~70 % tokens input à chaque /ask.
3. **Renommer/clarifier Alt.5** : soit implémenter un vrai vote majoritaire (intersection vector ∩ keyword ∩ articles boostée), soit corriger le commentaire L461.
4. **Index full-text Qdrant** sur `text` (`create_payload_index` type `text`) pour accélérer Alt.2/Alt.3 — supprime les timeouts MatchText.
5. **LRU cache** (`functools.lru_cache(256)`) sur `_reformulate_query` et `model.encode` pour requêtes fréquentes.
6. **`verify_citations`** : si `unverified > 0` ET ECLI inventé, supprimer la phrase entière au lieu d'annoter — zéro invention strict.
7. Ajouter un test end-to-end (pytest) sur les 5 queries de §3 pour régression.

Fichier : [`C:\Users\bahma\Downloads\base-juridique-app\.audit\PHASE_B_RAG.md`](.audit/PHASE_B_RAG.md)
