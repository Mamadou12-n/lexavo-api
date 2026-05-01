# Phase A — Audit Performance + Dépendances Lexavo

Date : 2026-05-01 | Auditeur : Claude Opus 4.7

## Métriques mesurées

| Métrique | Valeur | Cible |
|---|---|---|
| Bundle Android (compilé) | 11.55 MB | < 12 MB OK |
| StudentScreen.js | **2 451 lignes** | < 800 |
| api/main.py | 2 837 lignes | < 1500 |
| api/database.py | 1 901 lignes (139 execute) | refactor |
| ScrollView+map total | **293 occurrences / 33 écrans** | majoritaire vs FlatList |
| useMemo/useCallback/memo | 30 occurrences / 10 écrans seulement | < 30% écrans memoïsés |
| Embedding model | Singleton OK (`_model` cache, [retriever.py:105](../rag/retriever.py)) | OK |
| Cache RAG (Redis/lru) | **0 hits** sur `/ask` | absent — coût Anthropic x10 inutile |
| Prompt caching Anthropic | **0 fichiers** utilisent `cache_control` | manquant |
| Top_k Qdrant | top_k×5 = 50 candidats puis rerank Haiku | OK |
| /ask latence estimée | 8–14s (embed 60s cold + Claude 4–8s + 9 alts) | viser < 5s |

## Top 10 quick wins perf

1. **Prompt caching Anthropic** sur system prompt RAG (~6k tokens stables) → -90% coût input répété. Skill `claude-api`.
2. **Cache résultats /ask** (Redis/SQLite LRU) sur hash(question+source). 30%+ requêtes dupliquées attendues.
3. **Splitter StudentScreen.js (2 451 L)** en 4 sous-écrans (Quiz, Flashcards, Résumé, Stats). Réduit TTI initial.
4. **Remplacer ScrollView+map par FlatList** dans HomeScreen (grille 16 outils + 15 branches), HistoryScreen, AlertesScreen. Économise mémoire + fenêtrage virtuel.
5. **React.memo** sur ToolCard, BranchCard, MessageBubble (rendus en boucle).
6. **Lazy loading écrans outils** via `React.lazy` ou `createStackNavigator` lazy : 16 écrans outils chargés à la demande.
7. **Embedding model** : pré-chauffer au boot (`/health`) pour éviter +60s cold-start premier `/ask`.
8. **Qdrant `top_k * 5 = 50`** trop généreux ; descendre à `top_k * 3` pour /ask non-rerank.
9. **Anthropic models périmés** : `claude-sonnet-4-20250514` (audit_entreprise), `claude-haiku-4-5-20251001`, `claude-sonnet-4-6` → migrer vers 4.7 (skill `claude-api`).
10. **Dockerfile** : ChromaDB 47k chunks téléchargée à chaque build → COPY depuis volume Railway, ou build cache layer dédié.

## CVE / Vulnérabilités

| Stack | Total | Low | Moderate | High |
|---|---|---|---|---|
| **mobile (npm audit)** | **23** | 4 | 17 | 2 |
| backend (pip-audit) | non exécuté (env Windows) | — | — | — |

Fix proposé npm : `npm audit fix --force` MAIS implique downgrade Expo majeur — refuser. Préférer upgrade Expo SDK 54 → SDK 55 quand stable.

## Dépendances

**À retirer / remplacer :**
- `expo-av` (~16.0.8) — **deprecated SDK 54**, remplacer par `expo-audio` + `expo-video`. Skill `upgrading-expo`.
- `react-native-web` (^0.21.0) — utilisé ? si app mobile-only, retirer.
- `react-dom` 19.1.0 — uniquement utile si web build actif.

**À auditer :**
- `expo-notifications` ~0.32.17 — vérifier compat SDK 55.
- `axios` ^1.14.0 — OK, pas de CVE connue.

**Backend (requirements.txt non lu) :** lancer `pip-audit --strict` en CI Linux.

## Bundles & Build

- `babel.config.js` : OK, `react-native-worklets/plugin` correct pour reanimated 4.x.
- `metro.config.js` : **absent** → tree-shaking et `inlineRequires` non optimisés. Ajouter config avec `transformer.minifierConfig` + `serializer.experimentalSerializerHook`.
- Dockerfile multi-stage : OK builder/runtime, mais `wget` chroma à chaque build = 700MB layer non-cacheable.

## Économies coût Anthropic estimées

| Action | Économie/mois (1k users) |
|---|---|
| Prompt caching system prompt RAG | **-60% à -85% input tokens** = ~150–250 € |
| Cache /ask LRU (top 100 questions) | **-30% calls Claude** = ~100 € |
| Migration Sonnet 4.6 → Haiku 4.7 sur reranking + decode | -40% cost cible | ~60 € |
| **Total estimé** | **~300–400 €/mois** |

## Livrable

Fichier : [PHASE_A_PERF_DEPS.md](C:\Users\bahma\Downloads\base-juridique-app\.audit\PHASE_A_PERF_DEPS.md)

NE PAS FIXER — audit lecture seule, recommandations à valider en Phase B.
