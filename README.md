# Health AI Platform Pro — Backend

Production-ready FastAPI backend with Clean Architecture.

## Stack

- Python 3.12+
- FastAPI
- PostgreSQL + SQLAlchemy 2.0 (async)
- Alembic
- JWT Authentication
- Pydantic v2

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
cp .env.example .env          # edit values as needed
uvicorn app.main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

## Production Deployment (Render)

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full runbook.

| Step | Command |
|---|---|
| Build | `pip install -r requirements.txt` |
| Migrations (pre-deploy) | `bash scripts/run_migrations.sh` |
| Start | `bash scripts/start_production.sh` |
| Liveness | `GET /api/v1/health` |
| Readiness | `GET /api/v1/ready` |

Required production environment variables:

- `ENVIRONMENT=production`
- `DATABASE_URL` (Render `postgres://` URLs are normalized automatically)
- `JWT_SECRET_KEY` (unique, at least 32 characters)
- `CORS_ORIGINS` (comma-separated frontend origins)

Readiness may return HTTP 503 when PostgreSQL is unavailable.

## Project Structure

See the architecture explanation in the repository root documentation.
