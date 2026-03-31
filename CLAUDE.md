# CLAUDE.md — Lexavo (App Droit Belgique)

## Règle automatique — Chaque lundi matin

Au début de toute conversation un lundi, exécuter sans attendre de demande :

```bash
bash scripts/update-skills.sh
```

Cela met à jour tous les skills Railway. Si de nouveaux skills apparaissent dans
https://github.com/railwayapp/railway-skills, ils sont installés automatiquement.

## Skills actifs

**Railway** (source : railwayapp/railway-skills)
- `use-railway` — Déploiement et gestion Railway

**Expo** (source officielle : expo/skills)
- `expo-deployment` — Build EAS + publication App Store / Play Store
- `expo-dev-client` — Dev client Expo personnalisé

## Règles d'or (non-négociables)

1. Zéro invention — aucune donnée inventée, aucun chiffre non vérifié
2. Skills à jour — toujours utiliser la version actuelle des skills
3. GSD vérifie tout — toute info venant d'un agent est vérifiée
4. Toujours utiliser les skills définis dans `app-droit-supervisor`

## Projet

Application mobile React Native / Expo + backend FastAPI.
Base juridique belge : 18 sources officielles, 43 000+ chunks.
Stack : Expo SDK 54, FastAPI, ChromaDB, PostgreSQL (prod), Stripe, JWT.
