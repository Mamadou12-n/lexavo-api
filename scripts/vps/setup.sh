#!/bin/bash
# setup.sh — Déploiement Caddy + Qdrant sur VPS Hostinger
# Exécuter en root sur 46.202.168.185 :
#   scp -r scripts/vps/ root@46.202.168.185:/root/lexavo-vps/
#   ssh root@46.202.168.185 "cd /root/lexavo-vps && bash setup.sh"

set -euo pipefail

echo "=== Lexavo VPS Setup — Caddy + Qdrant ==="

# 1. Vérifier que QDRANT_API_KEY est défini
if [ -z "${QDRANT_API_KEY:-}" ]; then
  echo "ERREUR : variable QDRANT_API_KEY manquante."
  echo "Lance : export QDRANT_API_KEY=ta_clef && bash setup.sh"
  exit 1
fi

# 2. Ouvrir les ports 80 et 443 dans le firewall
echo "[1/5] Configuration firewall..."
if command -v ufw &>/dev/null; then
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw allow 443/udp
  echo "  ufw : ports 80/443 ouverts"
elif command -v firewall-cmd &>/dev/null; then
  firewall-cmd --permanent --add-service=http
  firewall-cmd --permanent --add-service=https
  firewall-cmd --reload
  echo "  firewalld : ports 80/443 ouverts"
else
  echo "  ATTENTION : aucun firewall détecté, vérifie manuellement"
fi

# 3. Vérifier que le volume Qdrant existe
echo "[2/5] Vérification volume Qdrant..."
if ! docker volume inspect lexavo-qdrant_qdrant_data &>/dev/null; then
  echo "ERREUR : volume lexavo-qdrant_qdrant_data introuvable."
  echo "Le conteneur Qdrant doit avoir tourné au moins une fois avec ce nom."
  echo "Volumes existants :"
  docker volume ls
  exit 1
fi
echo "  Volume trouvé : lexavo-qdrant_qdrant_data"

# 4. Arrêter l'ancien conteneur Qdrant standalone si présent
echo "[3/5] Arrêt conteneur Qdrant standalone..."
if docker ps -q --filter "name=lexavo-qdrant" | grep -q .; then
  docker stop lexavo-qdrant
  docker rm lexavo-qdrant
  echo "  Ancien conteneur supprimé"
else
  echo "  Aucun conteneur standalone actif"
fi

# 5. Lancer Qdrant + Caddy via docker compose
echo "[4/5] Démarrage Qdrant + Caddy..."
docker compose -f docker-compose.vps.yml up -d

# 6. Vérification santé
echo "[5/5] Vérification..."
sleep 10

if docker ps --filter "name=lexavo-qdrant" --filter "status=running" | grep -q lexavo-qdrant; then
  echo "  ✓ Qdrant en cours d'exécution"
else
  echo "  ✗ Qdrant non démarré — vérifie : docker logs lexavo-qdrant"
fi

if docker ps --filter "name=lexavo-caddy" --filter "status=running" | grep -q lexavo-caddy; then
  echo "  ✓ Caddy en cours d'exécution"
else
  echo "  ✗ Caddy non démarré — vérifie : docker logs lexavo-caddy"
fi

echo ""
echo "=== Prochaines étapes ==="
echo "1. Ajoute le DNS A record : qdrant.lexavo.be → 46.202.168.185"
echo "2. Attends 5-10 min (propagation DNS + cert Let's Encrypt auto)"
echo "3. Teste : curl -H 'api-key: \$QDRANT_API_KEY' https://qdrant.lexavo.be/healthz"
echo "4. Mets à jour Railway env var : QDRANT_URL=https://qdrant.lexavo.be"
echo "5. Mets à jour GitHub Actions secret : QDRANT_URL=https://qdrant.lexavo.be"
