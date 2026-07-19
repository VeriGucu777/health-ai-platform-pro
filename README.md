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
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Project Structure

See the architecture explanation in the repository root documentation.
