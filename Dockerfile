# =============================================================================
# Dockerfile — Lexavo FastAPI Backend
# Optimized for Railway 4GB image limit: ONNX Runtime instead of PyTorch
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

# Install sentence-transformers WITHOUT PyTorch (saves ~1.5GB)
# Use onnxruntime as backend instead (~50MB)
RUN pip install --no-cache-dir --prefix=/install \
        onnxruntime && \
    pip install --no-cache-dir --prefix=/install \
        --no-deps sentence-transformers && \
    pip install --no-cache-dir --prefix=/install \
        huggingface-hub tokenizers transformers tqdm numpy scipy scikit-learn Pillow && \
    pip install --no-cache-dir --prefix=/install \
        -r requirements.txt 2>&1 | tail -5

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean production image (~2.5GB vs 6.5GB)
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
COPY start.sh ./start.sh

# Download ChromaDB legal index from GitHub Releases
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    mkdir -p /app/output && \
    wget -q --show-progress \
      https://github.com/Mamadou12-n/lexavo-api/releases/download/v1.0-chroma/chroma_db.tar.gz \
      -O /tmp/chroma_db.tar.gz && \
    tar -xzf /tmp/chroma_db.tar.gz -C /app/output/ && \
    if [ -d "/app/output/chroma_db_new" ]; then mv /app/output/chroma_db_new /app/output/chroma_db; fi && \
    rm /tmp/chroma_db.tar.gz && \
    apt-get remove -y wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Runtime lib for psycopg2 + non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /app/start.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health')" || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
