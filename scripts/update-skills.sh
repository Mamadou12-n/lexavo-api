#!/usr/bin/env bash
# =============================================================================
# update-skills.sh — Mise à jour automatique de tous les skills Lexavo
# À lancer chaque lundi depuis la racine du projet :
#   bash scripts/update-skills.sh
# Ou via le cron système (crontab -e) :
#   3 9 * * 1 cd /chemin/vers/base-juridique-app && bash scripts/update-skills.sh
# =============================================================================

set -e

echo "🔄 Mise à jour des skills — $(date)"
echo ""

# ─── Skills Railway ───────────────────────────────────────────────────────────
echo "📦 Railway skills..."
RAILWAY_SKILLS=(use-railway railway-docs service central-station deployment database projects status)
for skill in "${RAILWAY_SKILLS[@]}"; do
  npx skills add https://github.com/railwayapp/railway-skills --skill "$skill" --yes 2>/dev/null \
    && echo "  ✓ $skill" || echo "  - $skill (non disponible)"
done

# ─── Skills Expo (officiels) ──────────────────────────────────────────────────
echo ""
echo "📦 Expo skills..."
EXPO_SKILLS=(expo-deployment expo-dev-client)
for skill in "${EXPO_SKILLS[@]}"; do
  npx skills add expo/skills --skill "$skill" --yes 2>/dev/null \
    && echo "  ✓ $skill" || echo "  - $skill (non disponible)"
done

# ─── Skills Remotion ─────────────────────────────────────────────────────────
echo ""
echo "📦 Remotion skills..."
npx skills add https://github.com/inferen-sh/skills --skill remotion-render --yes 2>/dev/null \
  && echo "  ✓ remotion-render" || echo "  - remotion-render (non disponible)"

echo ""
echo "✅ Terminé."
