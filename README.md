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

### Clinical retrieval embeddings (RAG v1)

| Runtime | Support |
|---|---|
| **Linux / Docker production** | `EMBEDDING_PROVIDER=local` with ONNX + FastEmbed (`fastembed==0.6.1`) |
| **Windows dev host** | Use `EMBEDDING_PROVIDER=fake` for API/unit tests only — local ONNX embeddings are **not** supported on Windows |

**RAG v1 official closure** (Linux/Docker, production ONNX + pgvector):

```powershell
cd backend
docker compose -f docker-compose.embedding-test.yml build embedding-tests
docker compose -f docker-compose.embedding-test.yml run --rm embedding-tests
# or: bash scripts/run_rag_v1_closure_tests.sh inside the image
```

This runs **two pytest processes** on purpose:

| Stage | Command | Why separate |
|---|---|---|
| 1 | `pytest -m "not integration"` | API/unit without PostgreSQL Testcontainers or ONNX embedding suite (~502 tests) |
| 2 | `pytest tests/integration/embedding` | Loads FastEmbed/ONNX once per process (~16 tests, TR/EN/cross-language + live E2E) |

Stage 1 excludes all `tests/integration/**` (including embedding). Combining both in **one** pytest process is supported after the embedding provider cache fix, but the closure script keeps stages separate for clearer failure isolation and RSS measurement (`/usr/bin/time` + `/proc`).

**Docker memory:** set `mem_limit: 1536m` on `embedding-tests` (measured stage-2 peak ~850–950 MB with a single cached model). Default Docker Desktop limits below ~1 GiB can OOM-kill pytest during model load.

Production API loads the embedding model **once per process** via `get_embedding_provider()` (startup lifespan + request DI cache). It does **not** reload ONNX per HTTP request.

### Clinical narrative LLM (v1)

Flow: **PatientAccessPolicy READ → RAG retrieval → LLM narrative** (LLM never touches DB).

| Setting | Purpose |
|---|---|
| `CLINICAL_NARRATIVE_PROVIDER=fake` | Dev/tests only (deterministic generator) |
| `CLINICAL_NARRATIVE_PROVIDER=external` | Production/staging (explicit opt-in; OpenAI-compatible HTTP API) |
| `CLINICAL_NARRATIVE_EXTERNAL_*` | Base URL, model id, API key (env only — never commit) |

Local/self-hosted LLM is **not** wired in v1; production requires `external` or a future provider kind. Endpoint: `POST /api/v1/patients/{patient_id}/clinical-narrative`.

**Rate limits (pilot):** `AuthRateLimiter` and clinical narrative limits use an **in-process** sliding window (`app/middleware/auth_rate_limit.py`). They are **not** shared across Uvicorn workers or hosts. For production/staging with rate limits enabled, set **`UVICORN_WORKERS=1`** (enforced at startup via `validate_pilot_runtime_settings`). `scripts/start_production.sh` defaults to one worker.

**Live external smoke (optional):** with real vendor credentials (never commit), run:

```bash
export CLINICAL_NARRATIVE_LIVE_SMOKE=1
export CLINICAL_NARRATIVE_EXTERNAL_BASE_URL=...
export CLINICAL_NARRATIVE_EXTERNAL_API_KEY=...
export CLINICAL_NARRATIVE_EXTERNAL_MODEL=...
pytest tests/integration/narrative/test_external_narrative_live_smoke.py -v
```

If credentials are missing, do **not** treat the slice as closed — the suite skips/fails explicitly (no silent fake fallback).

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
