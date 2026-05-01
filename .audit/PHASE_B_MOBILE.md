# PHASE B — Audit FONCTIONNEL mobile Lexavo

**Date** : 2026-05-01
**Path** : `mobile/`
**Stack** : RN 0.81 + Expo SDK 54 + react-navigation 7 + axios + AsyncStorage
**Périmètre** : 33 écrans, 12 composants (4 dans `ui/`), 1 context (LanguageContext), 50 endpoints API client, 8 langues annoncées.

---

## Score fonctionnel : **11 / 20**

| Axe | Note | Commentaire |
|-----|-----:|-------------|
| Navigation flow (App.js) | 3/4 | Flow boot correct (onboarding→consent→auth→main). Mais OnboardingScreen incompatible avec son render context (cf. Bug #1). Pas de deep linking déclaré. |
| Gestion auth + 401 + refresh | 4/4 | Refresh token + queue + logout fallback bien implémentés (`client.js:62-116`). Excellent. |
| Gestion erreurs API écrans | 2/4 | Pattern `e.response?.data?.detail \|\| e.message` correct, mais zéro distinction réseau / 5xx / quota dans 80% des écrans. |
| Cohérence states / hooks | 2/4 | Plusieurs race conditions et fuites mémoire potentielles (cf. Bug #4, #6). |
| i18n coverage | 0/4 | **Catastrophique** : seul HomeScreen consomme `useLanguage()`. ~3 % de couverture réelle. |

---

## i18n coverage estimée : **~3 %**

- 8 langues annoncées dans `OnboardingScreen.js` (fr/nl/en/de/ar/tr/es/pt) et translations.js fournit ~150 clés FR.
- Seul `HomeScreen` consomme `t()` via `useLanguage()` (cf. `Grep useLanguage` → 1 fichier).
- `OnboardingScreen` / `StudentScreen` / `SubscriptionScreen` importent `useLanguage` mais n'utilisent **pas `t()`** dans le JSX (textes hardcodés FR).
- 32 écrans sur 33 ont 100 % de strings hardcodées en français (Alert, Text, errors, labels, placeholders).
- `t()` n'est pas exporté depuis `i18n/translations.js` au format global — seul `LanguageContext.t()` existe, mais OnboardingScreen importe `t` depuis `../i18n/translations` (signature différente, prend `(key, lang)` en 2 args) → **2 systèmes i18n parallèles incohérents**.

---

## Top 10 bugs / incohérences logiques

1. **[CRITIQUE] OnboardingScreen ne termine jamais le flow.**
   `App.js:344-357` rend `<OnboardingScreen onDone={...} />` en standalone (hors NavigationContainer). Or `OnboardingScreen.js:80-90` ignore `onDone` et fait `navigation.reset({ routes:[{name:'Home'}] })` — `navigation` est `undefined` → crash silencieux ou no-op. L'utilisateur ne sort de l'onboarding qu'après kill+restart de l'app (AsyncStorage `@lexavo_onboarding_done` est tout de même écrit).

2. **[CRITIQUE] Clés AsyncStorage langue désynchronisées (3 sources différentes).**
   - `client.js:25` : `LANG_KEY = 'lexavo_lang'` (sans `@`)
   - `LanguageContext.js:5` : `LANG_KEY = 'lexavo_lang'` (sans `@`)
   - `OnboardingScreen.js:16` : `LANGUAGE: '@lexavo_language'` (avec `@`, autre nom)
   - Conséquence : la langue choisie pendant l'onboarding n'est **jamais lue** au démarrage par `LanguageProvider` ni par `client.js initLanguage()`. Le flag `selectedLang` est perdu.

3. **[HAUT] `initLanguage()` n'est jamais appelé.**
   `client.js:37 initLanguage()` existe mais n'est invoquée nulle part dans `App.js bootstrap()` → la langue côté API client reste `'fr'` par défaut, même si l'utilisateur a choisi NL/EN.

4. **[HAUT] Race condition AskScreen + quota.**
   `AskScreen.js:42-45` charge `getSubscriptionStatus()` sans gérer `unmount`. Si l'utilisateur quitte avant la réponse → setState sur composant démonté (warning RN). Pas de `AbortController`.

5. **[HAUT] StudentScreen — leak Audio session.**
   Header de fichier mentionne `expo-av` chargé via `require()` lazy, mais aucun `unloadAsync()` visible dans cleanup — risque de fuite audio quand l'utilisateur quitte le mode podcast.

6. **[HAUT] HistoryScreen — pas de limite de pagination.**
   `getConversations()` charge **toute** la liste, tri en mémoire (`HistoryScreen.js:30-37`). Si user a 500 conversations → freeze UI.

7. **[MOYEN] Détection 401 manquante dans certains catch.**
   `setUnauthHandler` est OK (App.js:326), mais plusieurs écrans interceptent l'erreur eux-mêmes et l'affichent au user (`AuthScreen.js:75-80`, `DefendScreen.js:252`) avant que l'intercepteur ait pu rediriger → comportements incohérents en cas de session expirée.

8. **[MOYEN] Pas de fallback UI loading > 30 s.**
   Aucun timeout côté UI sur `askQuestion`, `shieldAnalyze`, `defendAnalyze`. Axios timeout = 60 s mais aucun spinner avec message "ça prend du temps", pas de bouton annuler. Mauvais UX en réseau lent (3G).

9. **[MOYEN] Quota Free hard-codé en français.**
   `AskScreen.js:51-55` Alert "Quota atteint", "Passez au plan Pro" — chaîne brute. Idem dans 12 autres écrans.

10. **[BAS] `app.json` — pas de `scheme` deep linking.**
    Aucun `"scheme": "lexavo"` dans `app.json` → impossible d'ouvrir l'app via lien (Stripe checkout return, magic link forgot-password, share intent) sans rebuild. À ajouter avant prod iOS/Android.

---

## Storage — keys consistency

| Clé | Définition | Usage |
|-----|-----------|-------|
| `@lexavo_api_url` | client.js | OK |
| `@lexavo_auth_token` | client.js | OK |
| `@lexavo_auth_user` | client.js | OK |
| `@lexavo_refresh_token` | client.js | OK |
| `@lexavo_region` | client.js (`REGION_KEY`) | OK — réutilisé par OnboardingScreen, SettingsScreen, ShieldScreen, DefendScreen |
| `@lexavo_onboarding_done` | App.js (`ONBOARDING_KEY`) **et** OnboardingScreen.js (`STORAGE_KEYS.ONBOARDING_DONE`) | Doublon par chance même valeur |
| `lexavo_lang` (sans `@`) | client.js, LanguageContext.js | Incohérent avec convention |
| `@lexavo_language` (avec `@`) | OnboardingScreen.js | **Orphelin — jamais relu** |
| `@lexavo_push_token` / `@lexavo_notif_prefs` | utils/notifications.js | OK |
| `@lexavo_analytics` | utils/analytics.js | OK |
| `@lexavo_shield_history` | ShieldScreen.js | OK (pas de limite de taille — risque de bloat) |

Tests `__tests__/api/client.test.js:42` réfèrent encore `@jurisbe_api_url` — vestige avant rebrand.

---

## Composants partagés — diagnostic rapide

| Composant | Réutilisable | Props typées | Remarque |
|-----------|:-:|:-:|---|
| `ui/Card` / `ui/ToolCard` / `ui/Button` / `ui/Disclaimer` | Oui | Non (pas de PropTypes/JSDoc) | Bons composants design system mais zéro doc props. |
| `PhotoPicker` | Oui (16/16 écrans outils) | Non | OK fonctionnel. |
| `ChecklistStep` / `ScoreGauge` / `SourceBadge` / `SourceCard` / `ResultCard` / `ExtractedCard` / `ModelBadge` / `BadgeGrid` / `XPBar` / `StreakCounter` / `ConsentModal` | Oui | Non | Aucune annotation JSDoc — onboarding nouveau dev pénible. |

---

## Actions prioritaires (ordre)

1. **Fix Bug #1 + #2 + #3** (1h) : OnboardingScreen.handleComplete → appeler `props.onDone?.()` au lieu de `navigation.reset`. Unifier `LANG_KEY = '@lexavo_lang'` partout. Appeler `initLanguage()` dans `App.bootstrap()`.
2. **Brancher i18n sur les 32 écrans restants** (1-2 jours) : rechercher chaque string FR hardcodée → clé `t('xxx')`. Compléter `translations.js` (8 langues × ~400 clés). Sans ça, "8 langues" est marketing-only.
3. **Cleanup unmount** dans AskScreen / StudentScreen / SubscriptionScreen via `useRef(active=true)` ou `AbortController`.
4. **Ajouter `"scheme": "lexavo"` + linking config** à `app.json` avant la prochaine release prod.
5. **Pagination HistoryScreen** (`limit=20`, infinite scroll).
6. **JSDoc/PropTypes** sur les 12 composants partagés (30 min de polish).
7. **Centraliser les Alert.alert** dans un helper `showError(e)` qui sait classer (réseau / 401 / 5xx / quota / inconnu).

---

## Fichier
[PHASE_B_MOBILE.md](.audit/PHASE_B_MOBILE.md)
