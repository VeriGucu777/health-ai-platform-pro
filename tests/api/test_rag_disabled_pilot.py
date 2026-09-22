"""Pilot deployment: RAG disabled on low-memory hosts (Render Free tier)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.core.exceptions import FeatureDisabledError
from app.infrastructure.database.session import reset_database_engine
from app.infrastructure.embeddings.embedding_factory import get_embedding_provider
from app.main import create_app


def _production_pilot_settings(*, rag_enabled: bool) -> Settings:
    return Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        RAG_ENABLED=rag_enabled,
        EMBEDDING_PROVIDER="local",
        LOCAL_EMBEDDING_MODEL="health-ai-platform/clinical-retrieval-multilingual-v1",
        EMBEDDING_VERSION="3",
        JWT_SECRET_KEY="a-unique-production-secret-with-sufficient-length",
        CORS_ORIGINS=["https://app.example.com"],
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/health_ai_test",
        AUTH_RATE_LIMIT_ENABLED=False,
        HEALTH_CHECK_DB_ENABLED=False,
        METRICS_ENABLED=False,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=False,
    )


def test_rag_enabled_defaults_to_true() -> None:
    settings = Settings(JWT_SECRET_KEY="test-secret-key-for-unit-tests-only")
    assert settings.rag_enabled is True


def test_get_embedding_provider_raises_when_rag_disabled() -> None:
    settings = _production_pilot_settings(rag_enabled=False)
    with pytest.raises(FeatureDisabledError, match="RAG") as exc_info:
        get_embedding_provider(settings)
    assert exc_info.value.status_code == 503
    assert exc_info.value.details.get("code") == "rag_disabled"


@pytest.mark.asyncio
async def test_production_rag_disabled_startup_skips_embedding_provider() -> None:
    settings = _production_pilot_settings(rag_enabled=False)
    get_settings.cache_clear()
    reset_database_engine()
    app = create_app(settings)

    with patch(
        "app.infrastructure.embeddings.embedding_factory.get_embedding_provider",
    ) as mock_get_provider:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
        assert response.status_code == 200
        mock_get_provider.assert_not_called()

    get_settings.cache_clear()
    reset_database_engine()


@pytest.mark.asyncio
async def test_clinical_retrieval_returns_503_when_rag_disabled(client, app) -> None:
    from app.api.deps import get_clinical_retrieval_service

    app.dependency_overrides.pop(get_clinical_retrieval_service, None)
    app.state.settings = app.state.settings.model_copy(update={"rag_enabled": False})

    email = f"rag-off-{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Pilot",
            "last_name": "User",
            "role": "doctor",
        },
    )
    token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "securepass123"},
        )
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patient_id = uuid4()
    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-retrieval",
        headers=headers,
        json={"query": "glucose", "top_k": 3},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert "disabled" in body["message"].lower()
