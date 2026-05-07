# Lexavo — Déploiement production

## 🔐 Secrets GitHub Actions à configurer

Aller sur **GitHub → Settings → Secrets and variables → Actions** puis ajouter :

| Secret | Valeur | Utilisé par |
|--------|--------|-------------|
| `QDRANT_URL` | `https://xxx.cloud.qdrant.io` | weekly-legal-update.yml |
| `QDRANT_API_KEY` | `eyJhbGc...` (clé Qdrant cloud) | weekly-legal-update.yml |
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` (Lexavo dédiée) | weekly-legal-update.yml + ci.yml |
| `APIFY_API_TOKEN` | `apify_api_...` | weekly-legal-update.yml (juridat scraper) |
| `SENTRY_DSN` | `https://xxx@sentry.io/yyy` | weekly-legal-update.yml |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/...` (optionnel) | Notifs run weekly |

### Commandes CLI (alternative)

```bash
gh secret set QDRANT_URL --body "https://xxx.cloud.qdrant.io"
gh secret set QDRANT_API_KEY --body "eyJhbGc..."
gh secret set ANTHROPIC_API_KEY --body "sk-ant-api03-..."
gh secret set APIFY_API_TOKEN --body "apify_api_..."
gh secret set SENTRY_DSN --body "https://xxx@sentry.io/yyy"
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/..."
```

## 🔐 Variables d'env Railway (backend prod)

Aller sur **Railway → Lexavo Backend → Variables** :

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL Railway (auto-injecté) |
| `ANTHROPIC_API_KEY` | Clé Claude (sk-ant-api03-...) |
| `LEXAVO_JWT_SECRET` | Secret JWT (`openssl rand -hex 32`) |
| `STRIPE_SECRET_KEY` | `sk_live_...` (Stripe live) |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_PRICE_BASIC` | `price_xxxxx` |
| `STRIPE_PRICE_BASIC_ANNUAL` | `price_xxxxx` |
| `QDRANT_URL` | `https://xxx.cloud.qdrant.io` |
| `QDRANT_API_KEY` | clé Qdrant cloud |
| `SENTRY_DSN` | DSN Sentry backend |
| `SENTRY_ENV` | `production` |
| `LEXAVO_ALLOWED_ORIGINS` | `https://lexavo.be,https://app.lexavo.be` |
| `LEXAVO_FRONTEND_URL` | `https://app.lexavo.be` |
| `RAILWAY_GIT_COMMIT_SHA` | (auto-injecté Railway) |
| `LEXAVO_BETA_FREE_CAP` | `50` (par défaut) |
| `LEXAVO_DAILY_BUDGET_USD` | `1.50` (cap journalier Anthropic, optionnel) |
| `DB_POOL_MIN` | `2` |
| `DB_POOL_MAX` | `10` |

## 🔐 Variables d'env Mobile (Expo build)

```bash
# .env (Expo lit via process.env.EXPO_PUBLIC_*)
EXPO_PUBLIC_API_URL=https://api.lexavo.be
EXPO_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/yyy
EXPO_PUBLIC_PROJECT_ID=xxxxx-xxxx-xxxx
EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

## 🔄 Mise à jour automatique de la base juridique

### Cron principal — chaque lundi 03h UTC

Le workflow `.github/workflows/weekly-legal-update.yml` :

1. Scrape **17 sources** (HUDOC, EUR-Lex, Justel, Moniteur, JURIDAT, etc.)
2. Skip les docs déjà indexés (logique incrémentale dans `rag/indexer_qdrant.py`)
3. Indexe les nouveaux dans **Qdrant cloud**
4. Notifie Slack (si configuré) + Job summary GitHub
5. Upload logs en artifact (rétention 30 jours)

### Lancer manuellement

```bash
# Via CLI
gh workflow run weekly-legal-update.yml \
  -f max_docs=100 \
  -f sources="moniteur,justel,hudoc"

# Via UI
# GitHub → Actions → Weekly Legal Database Update → Run workflow
```

### Sources scrapées (17 actives)

| Source | Type | Doc/semaine estimé |
|--------|------|--------------------|
| Moniteur belge (ETAAMB) | Lois publiées | 50-150 |
| JUSTEL (SPF Justice) | Codes coordonnés | 5-15 (refonte) |
| HUDOC (CEDH) | Jurisprudence européenne | 10-30 |
| EUR-Lex | Réglementation UE | 20-50 |
| JURIDAT (Cassation) | Jurisprudence belge | 15-40 (via Apify) |
| Conseil d'État | Arrêts admin | 10-25 |
| Cour constitutionnelle | Arrêts | 2-5 |
| CCE | Étrangers | 5-15 |
| CNT | Conventions collectives | 1-3 |
| Codex Vlaanderen | Droit flamand | 5-15 |
| Wallex | Droit wallon | 5-15 |
| GalliLex | Droit FWB | 3-10 |
| APD | RGPD/données | 1-3 |
| FSMA | Régulateur financier | 2-5 |
| Bruxelles | Droit bruxellois | 5-10 |
| CCREK | Cour des comptes | 1-3 |
| Chambre | Documents parlementaires | 10-20 |

**Total estimé** : 150-450 nouveaux docs/semaine.

## 🚀 Premier déploiement

```bash
# 1. Configurer tous les secrets GitHub + Railway (cf. tableaux)

# 2. Tester le workflow weekly en local mode
gh workflow run weekly-legal-update.yml -f max_docs=10 -f sources="moniteur"

# 3. Verifier que ca passe
gh run list --workflow weekly-legal-update.yml --limit 1
gh run watch

# 4. Deployer backend Railway
git push origin main  # Railway auto-deploy

# 5. Verifier health backend
curl https://api.lexavo.be/health

# 6. Verifier mobile build
cd mobile && npx expo build --platform android --release-channel production
```

## 🚨 Monitoring post-déploiement

### Quotidien
- **Sentry** : https://sentry.io/organizations/lexavo/issues/ (errors)
- **Anthropic billing** : https://console.anthropic.com/settings/usage
- **Stripe dashboard** : webhooks idempotents reçus
- **Railway logs** : `railway logs --tail`

### Hebdomadaire
- **GitHub Actions** : status weekly-legal-update.yml
- **Qdrant cloud** : nb chunks total (doit augmenter ~150-450/semaine)
- **PostgreSQL Railway** : taille DB, conversations/messages count

### Mensuel
- **pip-audit** : `pip-audit -r requirements.txt`
- **npm audit** : `cd mobile && npm audit`
- **Backup PostgreSQL** : Railway snapshots auto

## 📋 Checklist pré-mise en production

- [ ] Tous les secrets GitHub configurés (cf. tableau)
- [ ] Toutes les variables Railway configurées
- [ ] EXPO_PUBLIC_PROJECT_ID remplacé (placeholder)
- [ ] BCE/VAT mentions complétées (4 fichiers : ConsentModal, CGU, MentionsLegales, Privacy)
- [ ] Stripe live keys + webhook signature vérifiés
- [ ] Branch protection main activée (required CI green)
- [ ] CODEOWNERS défini
- [ ] Sentry alerts configurées (>5 errors/min, /ask 500)
- [ ] Anthropic budget alert configuré (<5$ remaining)
- [ ] Premier run weekly-legal-update.yml validé
- [ ] Test E2E mobile sur device réel (signup → ask → paywall)
- [ ] Disclaimer "ne constitue pas un avis juridique" présent dans toutes les features
- [ ] RGPD : ConsentModal affiché avant première utilisation
- [ ] Mentions légales BCE/TVA complètes (post-immatriculation SRL)

## 🛡 Rollback en cas de problème

```bash
# Backend Railway
railway rollback  # rollback au dernier deploy

# Mobile : OTA update via expo-updates (si configuré)
eas update --branch production --message "rollback"

# Cron weekly désactiver
gh workflow disable weekly-legal-update.yml

# Qdrant : pas de rollback automatique, mais collection reste consistante
# (les docs déjà indexés ne sont jamais supprimés)
```

---

*Dernière mise à jour : 2026-05-07. Pour questions : Mamadou BAH.*
