#!/usr/bin/env bash
# Start the FastAPI application for production (Render/Linux).
# Run scripts/run_migrations.sh separately before this command.
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
# Pilot: AuthRateLimiter and clinical narrative limits are process-local — use one worker.
WORKERS="${UVICORN_WORKERS:-1}"

if [ "${WORKERS}" != "1" ]; then
  echo "WARNING: UVICORN_WORKERS=${WORKERS} — per-user rate limits are not global across workers." >&2
  echo "Set UVICORN_WORKERS=1 for pilot/production unless shared rate-limit storage is added." >&2
fi

echo "Starting ${APP_NAME:-Health AI Platform Pro} on ${HOST}:${PORT} (workers=${WORKERS})..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}"
