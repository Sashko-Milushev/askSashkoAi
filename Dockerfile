# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps for psycopg2-binary and faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (knowledge PDFs are included to build the vector index on startup)
COPY . .

# Remove dev/local artefacts that must not ship
RUN rm -rf .env vector_store __pycache__ tests .github \
    && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000

# Run Alembic migrations then start the server
CMD alembic upgrade head && \
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

