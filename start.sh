#!/bin/bash
# =============================================================================
# start.sh — Lexavo startup script for Railway (Nixpacks)
# Downloads ChromaDB v2.0 (47 047 chunks, 8 sources officielles vérifiées)
# =============================================================================

set -e

# Marqueur de version — force le re-téléchargement quand la version change
CHROMA_VERSION="2.0.1"
VERSION_FILE="/app/output/chroma_db/.version"

FORCE_UPDATE=false
if [ -d "/app/output/chroma_db" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
    if [ "$CURRENT_VERSION" != "$CHROMA_VERSION" ]; then
        echo ">>> ChromaDB obsolète ($CURRENT_VERSION → $CHROMA_VERSION), mise à jour forcée..."
        rm -rf /app/output/chroma_db
        FORCE_UPDATE=true
    fi
fi

if [ ! -d "/app/output/chroma_db" ] || [ "$FORCE_UPDATE" = true ]; then
    echo ">>> Téléchargement ChromaDB v${CHROMA_VERSION} (47 047 chunks, 8 sources officielles)..."
    mkdir -p /app/output
    wget -q --show-progress \
        https://github.com/Mamadou12-n/lexavo-api/releases/download/v2.0-chroma/chroma_db_v2.tar.gz \
        -O /tmp/chroma_db.tar.gz
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/
    rm -f /tmp/chroma_db.tar.gz
    echo "$CHROMA_VERSION" > "/app/output/chroma_db/.version"
    echo ">>> ChromaDB v${CHROMA_VERSION} prête ($(ls /app/output/chroma_db/ | wc -l) fichiers)"
else
    echo ">>> ChromaDB v${CHROMA_VERSION} déjà présente"
fi

# Start FastAPI
echo ">>> Démarrage API Lexavo sur port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
