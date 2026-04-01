#!/bin/bash
# =============================================================================
# start.sh — Lexavo startup script for Railway (Nixpacks)
# Downloads ChromaDB on first run, then starts the API
# =============================================================================

set -e

# Download ChromaDB if not already present (persisted via Railway volume)
if [ ! -d "/app/output/chroma_db" ]; then
    echo ">>> Downloading ChromaDB legal index..."
    mkdir -p /app/output
    wget -q --show-progress \
        https://github.com/Mamadou12-n/lexavo-api/releases/download/v1.0-chroma/chroma_db.tar.gz \
        -O /tmp/chroma_db.tar.gz
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/
    # Handle both possible directory names
    if [ -d "/app/output/chroma_db_new" ]; then
        mv /app/output/chroma_db_new /app/output/chroma_db
    fi
    rm -f /tmp/chroma_db.tar.gz
    echo ">>> ChromaDB ready ($(ls /app/output/chroma_db/ | wc -l) files)"
else
    echo ">>> ChromaDB already present, skipping download"
fi

# Start FastAPI
echo ">>> Starting Lexavo API on port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
