# Deployment Guide — Render

This document describes the **expected Render configuration** for Health AI Platform Pro. It is **documentation only** and does **not** change the current live Render service automatically. Apply any changes manually in the Render dashboard after review.

## Repository Root

The Git repository root for deployment is `backend/`. Render build and start commands assume the working directory is the backend project root.

## Expected Render Web Service Settings

| Setting | Recommended value |
|---|---|
| **Runtime** | Python 3.12 |
| **Build command** | `pip install -r requirements.txt` |
| **Pre-deploy command** | `bash scripts/run_migrations.sh` |
| **Start command** | `bash scripts/start_production.sh` |
| **Health check path (liveness)** | `/api/v1/health` |
| **Readiness path (optional)** | `/api/v1/ready` |

### Why migrations run separately

`scripts/run_migrations.sh` runs `alembic upgrade head` and exits with a non-zero status on failure. Render should execute this as a **pre-deploy** step so schema changes complete before the new web process starts. The start script does **not** run migrations; if migrations fail, the API must not start with an outdated schema.

### Start command behavior

`scripts/start_production.sh` binds Uvicorn to:

- `HOST` (default `0.0.0.0`)
- `PORT` (Render injects this automatically)

Application import path: `app.main:app`

## Required Environment Variables

Set these in the Render dashboard (never commit real values):

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Must be `production` for live deployment |
| `DATABASE_URL` | Linked Render PostgreSQL URL |
| `JWT_SECRET_KEY` | Unique secret, minimum 32 characters |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `AUTH_RATE_LIMIT_BACKEND` | `memory` (default) or `redis` for shared rate limiting |
| `REDIS_URL` | Required when `AUTH_RATE_LIMIT_BACKEND=redis` in production |

### DATABASE_URL normalization

Render often provides:

- `postgres://...`
- `postgresql://...`

The application normalizes these to `postgresql+asyncpg://...` for the async SQLAlchemy engine. Credentials and query parameters (for example `?sslmode=require`) are preserved unchanged. Alembic uses the equivalent sync `postgresql+psycopg://...` URL via `database_url_sync`.

## Health and Readiness Endpoints

| Endpoint | Purpose | Expected status |
|---|---|---|
| `GET /api/v1/health` | Liveness — process is running | `200` while the app is alive |
| `GET /api/v1/ready` | Readiness — dependencies available | `200` when ready; `503` when PostgreSQL is unavailable |

Configure Render's primary health check to **`/api/v1/health`** so transient database issues do not cause unnecessary process restarts. Use `/api/v1/ready` for load-balancer readiness routing when supported.

When observability/readiness probing is enabled, `/api/v1/ready` performs a database connectivity check and returns `503` if PostgreSQL cannot be reached.

## Root Route Behavior

| Environment | `GET /` behavior |
|---|---|
| `development` | Redirects to `/docs` (Swagger UI) |
| `production` / `staging` | Returns JSON with service name, version, and health endpoint paths |

Production does **not** redirect to `/docs` because OpenAPI documentation is disabled outside development.

## Rollback Procedure

1. **Application rollback:** In Render, redeploy the previous successful release. No repository file changes the live service automatically.
2. **Migration rollback:** Only run `alembic downgrade <revision>` manually when you have confirmed the target revision is safe for existing production data. Destructive downgrades require explicit approval.
3. **Secrets:** If `JWT_SECRET_KEY` is rotated, all existing tokens become invalid. Plan client impact before rotating.

## Local Production-Like Verification

```bash
cd backend
pip install -r requirements.txt
export ENVIRONMENT=production
export JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_platform"
bash scripts/run_migrations.sh
bash scripts/start_production.sh
```

## What This Document Does Not Do

- Does not create or modify Render services
- Does not deploy code
- Does not run migrations against production
- Does not replace dashboard settings already in use

Review existing Render dashboard values before changing build, start, or health-check configuration. Match documented commands to the live service to avoid deployment disruption.

### PDF reports

Patient health PDF reports require the bundled Unicode font at `app/assets/fonts/NotoSans-Regular.ttf` (see [FONTS.md](FONTS.md)). Ensure production deployments use a full repository checkout that includes this file and `OFL.txt`.

## Related Documentation

- [TOKEN_REVOCATION.md](TOKEN_REVOCATION.md) — token lifecycle and future revocation options
- [FONTS.md](FONTS.md) — bundled PDF Unicode font requirements
- [../README.md](../README.md) — backend quick start and deployment summary
- [../.env.example](../.env.example) — environment variable reference
