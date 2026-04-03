# =============================================================================
# Dockerfile — Lexavo FastAPI Backend
# Railway Hobby plan (8GB limit) — PyTorch CPU + ChromaDB + FastAPI
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build deps for psycopg2 and C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU-only first (~800MB vs ~2GB CUDA), then all deps
RUN pip install --no-cache-dir --prefix=/install \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --prefix=/install \
        sentence-transformers && \
    pip install --no-cache-dir --prefix=/install \
        -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Lexavo API" \
      org.opencontainers.image.description="RAG API for Belgian legal documents" \
      org.opencontainers.image.source="https://github.com/Mamadou12-n/lexavo-api"

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY api/ ./api/
COPY rag/ ./rag/
COPY processors/ ./processors/
COPY config.py ./config.py

# Download ChromaDB v2.0.1 legal index from GitHub Releases
# 47,047 chunks — 8 sources officielles, 28 codes belges complets, vérifié 5x
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    mkdir -p /app/output && \
    wget -q --show-progress \
      https://github.com/Mamadou12-n/lexavo-api/releases/download/v2.0-chroma/chroma_db_v2.tar.gz \
      -O /tmp/chroma_db.tar.gz && \
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/ && \
    echo "2.0.1" > /app/output/chroma_db/.version && \
    rm /tmp/chroma_db.tar.gz && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Note: embedding model telecharge au premier /ask (~60s) — retrait du pre-download
# pour respecter la limite disque Railway (8GB build layer)

# Runtime lib for psycopg2 + non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health')" || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
