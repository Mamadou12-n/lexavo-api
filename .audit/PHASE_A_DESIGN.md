# PHASE_A_DESIGN — Audit design Lexavo Mobile (2026-05-01)

## Score design : 13.5 / 20

| Dimension | Score | Notes |
|---|---|---|
| Accessibilité | 2 / 4 | Seulement ~204 `accessibilityRole` pour ~456 `Pressable/TouchableOpacity` (45%). Le commit `8f1d3b5` "100% accessibilityRole" est faux. |
| Performance | 3 / 4 | Reanimated/spring OK, pas de re-renders évidents. Élévations cohérentes via tokens. |
| Theming | 2 / 4 | designSystem.js exemplaire, MAIS ~550 hex hardcodés dans 32 écrans (`#1F2937`, `#F3F4F6`, `LEXAVO_ORANGE` dans AuthScreen:387, T.border dans StudentScreen, etc.). |
| Responsive | 3 / 4 | Spacing 4pt OK, touch ≥44px sur Button. Non vérifié sur Pressables custom (StudentScreen tab bar paddingBottom 28). |
| Anti-patterns | 3.5 / 4 | Aucun gradient text / BlurView / fontWeight 'bold' / shadowColor #000. 274 emojis encore présents dans 27 écrans (DefendScreen 44, StudentScreen 67) malgré commit "100% emojis→Ionicons". Bordures restantes = séparateurs 1-2px légitimes. |

## Score Nielsen heuristics : 31 / 40

- Visibilité statut système : 4/5 (loaders ActivityIndicator OK)
- Correspondance monde réel : 4/5 (FR correct, vocabulaire juridique)
- Contrôle utilisateur : 3/5 (peu d'undo, pas de back custom)
- Cohérence/standards : 3/5 (palette violée par hex hardcodés)
- Prévention erreurs : 4/5 (disabled states, Disclaimer composant)
- Reconnaissance : 3/5 (Ionicons sur tabs, mais emojis subsistent inline)
- Flexibilité : 3/5 (pas de raccourcis clavier, OK mobile)
- Esthétique minimaliste : 4/5 (designSystem propre)
- Récupération erreurs : 3/5
- Aide/documentation : 0/5 (aucune help bubble visible)

## Findings critiques

- [HIGH] `mobile/src/screens/StudentScreen.js` — 67 emojis comme icônes UI, 123 Pressables/TouchableOpacity pour 61 accessibilityRole (50%). Tab bar `paddingBottom:28` (l.2394) sans SafeArea.
- [HIGH] `mobile/src/screens/DefendScreen.js` — 44 emojis, 25 Pressables / 12 a11yRole.
- [HIGH] `mobile/src/screens/AuthScreen.js:387` — `shadowColor: LEXAVO_ORANGE` (hex local hardcodé, hors designSystem).
- [MED] `mobile/src/screens/SubscriptionScreen.js` — 11 emojis, 11 Pressables sans accessibilityRole.
- [MED] `mobile/src/screens/SettingsScreen.js` — 12 emojis, 7 Pressables / 3 a11yRole.
- [LOW] `mobile/src/screens/LegalScreen.js:291` — `borderBottomWidth: 2` (séparateur OK mais à confirmer).
- [LOW] `App.js:13-17` — JSDoc utilise emojis pour décrire onglets (cosmétique).

## 5 actions prioritaires

1. **Remplacer les 274 emojis restants par Ionicons** — DefendScreen, StudentScreen, SubscriptionScreen, SettingsScreen en priorité.
2. **Ajouter `accessibilityRole`+`accessibilityLabel` sur les ~250 Pressables manquants** (55% non couverts).
3. **Migrer les ~550 hex hardcodés vers `colors.X`** (T.border, #1F2937, #F3F4F6, LEXAVO_ORANGE → tokens).
4. **Vérifier `minHeight: 44` sur tous Pressables custom** (touch targets WCAG 2.5.8) — Button OK, le reste à auditer.
5. **Audit contraste WCAG AA** sur `colors.textMuted #9CA3AF` sur `surface #FFFFFF` (ratio 2.85:1 — ÉCHEC pour texte normal). Foncer à `#6B7280` minimum.

Fichier : `C:\Users\bahma\Downloads\base-juridique-app\.audit\PHASE_A_DESIGN.md`
