#!/bin/bash
# =============================================================================
# start.sh — Lexavo startup script for Railway (Nixpacks)
# Downloads ChromaDB on first run, then starts the API
# =============================================================================

set -e

# Download ChromaDB if not already present (persisted via Railway volume)
# Force re-download if old v1.0 data (less than 6000 chunks)
FORCE_UPDATE=false
if [ -d "/app/output/chroma_db" ]; then
    FILE_COUNT=$(ls /app/output/chroma_db/ 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -lt 3 ]; then
        echo ">>> Old ChromaDB detected, forcing update to v2.0..."
        rm -rf /app/output/chroma_db
        FORCE_UPDATE=true
    fi
fi

if [ ! -d "/app/output/chroma_db" ] || [ "$FORCE_UPDATE" = true ]; then
    echo ">>> Downloading ChromaDB v2.0 legal index (6821 chunks, 28 codes belges)..."
    mkdir -p /app/output
    wget -q --show-progress \
        https://github.com/Mamadou12-n/lexavo-api/releases/download/v2.0-chroma/chroma_db_v2.tar.gz \
        -O /tmp/chroma_db.tar.gz
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/
    rm -f /tmp/chroma_db.tar.gz
    echo ">>> ChromaDB v2.0 ready ($(ls /app/output/chroma_db/ | wc -l) files)"
else
    echo ">>> ChromaDB v2.0 already present, skipping download"
fi

# Start FastAPI
echo ">>> Starting Lexavo API on port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
