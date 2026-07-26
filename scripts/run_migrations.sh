#!/usr/bin/env bash
# Apply Alembic migrations before starting the API in production.
# Intended for Render pre-deploy hooks or manual release steps.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed successfully."
