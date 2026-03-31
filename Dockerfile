# =============================================================================
# Dockerfile — Lexavo FastAPI Backend
# Multi-stage build for the Belgian legal RAG API
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies needed by some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Metadata
LABEL org.opencontainers.image.title="Lexavo API" \
      org.opencontainers.image.description="RAG API for Belgian legal documents" \
      org.opencontainers.image.source="https://github.com/Mamadou12-n/lexavo-api"

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY api/ ./api/
COPY rag/ ./rag/
COPY processors/ ./processors/
COPY config.py ./config.py

# Download ChromaDB legal index from GitHub Releases
# 43 005 chunks — droit belge FR/NL/EN/DE — chromadb 0.5.x compatible
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    mkdir -p /app/output && \
    wget -q --show-progress \
      https://github.com/Mamadou12-n/lexavo-api/releases/download/v1.0-chroma/chroma_db.tar.gz \
      -O /tmp/chroma_db.tar.gz && \
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/ && \
    mv /app/output/chroma_db_new /app/output/chroma_db && \
    rm /tmp/chroma_db.tar.gz && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    mkdir -p /app/db && \
    chown -R appuser:appuser /app

USER appuser

# Expose the API port
EXPOSE 8000

# Healthcheck — hits the /health endpoint (Railway uses $PORT, local uses 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health')" || exit 1

# Start the FastAPI server — $PORT injected by Railway, fallback to 8000 locally
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
