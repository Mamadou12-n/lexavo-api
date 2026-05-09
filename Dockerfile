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
        -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install \
        edge-tts || true

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

# RAG actif en prod : Qdrant cloud (env vars QDRANT_URL + QDRANT_API_KEY).
# ChromaDB legacy local (chroma_db.tar.gz 600 MB) retire 2026-05-08 :
#   - empechait Qdrant de prendre la main au runtime (collision /app/output/chroma_db)
#   - ajoutait 600 MB inutile a l'image (image 3.1 GB -> ~2.5 GB)
#   - faisait crasher le healthcheck Railway au boot (workers init trop lents)

# Runtime lib for psycopg2 + non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    mkdir -p /app/output && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Healthcheck Railway : start-period 240s pour laisser le pre-warm
# SentenceTransformer (~60s premier dl + load) + Qdrant client init.
HEALTHCHECK --interval=30s --timeout=10s --start-period=240s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health')" || exit 1

# Workers default 2 sur Railway Hobby (8 GB RAM).
# - 1 worker  = ~1.5 GB (sentence-transformers 512 MB + Python 1 GB)
# - 2 workers = ~3 GB (marge OK)
# - 4 workers = ~6 GB (limite, override via UVICORN_WORKERS=4 si RAM stable)
# Combine avec DB_POOL_MAX=20 (database.py) : 4 workers x 20 = 80 connexions Postgres (limite Railway 100).
# Capacite estimee : ~50 users actifs simultanes par worker.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2}"]
