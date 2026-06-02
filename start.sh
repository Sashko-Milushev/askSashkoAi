#!/bin/sh
# Startup script for Railway deployment.
# Runs alembic with a timeout — uvicorn starts regardless of migration result.

set -e

PORT="${PORT:-8000}"

echo "==> Attempting database migrations..."
# timeout 30s so alembic never hangs indefinitely
if timeout 30 alembic upgrade head; then
    echo "==> Migrations applied successfully."
else
    echo "==> WARNING: Migration failed or timed out — starting server anyway."
fi

echo "==> Starting uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --workers 1

