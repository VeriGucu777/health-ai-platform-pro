#!/usr/bin/env bash
# Start the FastAPI application for production (Render/Linux).
# Run scripts/run_migrations.sh separately before this command.
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"

echo "Starting ${APP_NAME:-Health AI Platform Pro} on ${HOST}:${PORT}..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"
