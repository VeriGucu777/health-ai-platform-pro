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
- `AUTH_RATE_LIMIT_BACKEND=redis` and `REDIS_URL` for production rate limiting across instances

Readiness may return HTTP 503 when PostgreSQL is unavailable.

## Testing

```powershell
pytest tests/ -v
```

| Suite | Tests |
|---|---|
| Full suite | 277 |
| API + unit (CI job 1) | 245 |
| Integration (CI job 2) | 32 |

API + unit tests use in-memory repositories and do not require PostgreSQL. Integration tests require Docker (Testcontainers).

## Documentation

| Document | Description |
|---|---|
| [docs/FONTS.md](docs/FONTS.md) | Bundled PDF Unicode font requirements |
| [docs/API_INVENTORY.md](docs/API_INVENTORY.md) | Complete route inventory (37 HTTP routes) |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Render deployment runbook |
| [docs/TOKEN_REVOCATION.md](docs/TOKEN_REVOCATION.md) | Deferred token revocation design |
| [../PROJECT_STATUS.md](../PROJECT_STATUS.md) | Feature matrix, schema, roadmap |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Architecture reference |

## Project Structure

See the architecture explanation in the repository root documentation.

## Frontend

The `frontend/` folder contains a Phase 1A Next.js scaffold (TypeScript, App Router, Tailwind CSS) with landing, login, and register placeholder pages. See [frontend/README.md](frontend/README.md) for installation, environment variables, and local development.

The API is configured for cross-origin requests from local development servers (`localhost:3000`, `127.0.0.1:3000`, `localhost:5173`). The Next.js frontend connects to `/api/v1/auth/*` endpoints for login, registration, logout, and token refresh.
