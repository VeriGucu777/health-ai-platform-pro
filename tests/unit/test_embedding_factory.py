"""Embedding provider configuration and production fail-fast."""

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from app.infrastructure.embeddings.embedding_factory import create_embedding_provider


def test_production_rejects_missing_provider() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="production-secret-key-minimum-length",
        EMBEDDING_PROVIDER="",
    )
    with pytest.raises(ConfigurationError, match="EMBEDDING_PROVIDER=local"):
        create_embedding_provider(settings)


def test_production_rejects_fake_provider() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="production-secret-key-minimum-length",
        EMBEDDING_PROVIDER="fake",
    )
    with pytest.raises(ConfigurationError, match="Fake embeddings"):
        create_embedding_provider(settings)


def test_development_requires_explicit_provider() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="",
    )
    with pytest.raises(ConfigurationError, match="must be set explicitly"):
        create_embedding_provider(settings)


def test_production_rejects_empty_local_model(monkeypatch) -> None:
    monkeypatch.setattr("app.infrastructure.embeddings.embedding_factory.sys.platform", "linux")
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="production-secret-key-minimum-length",
        EMBEDDING_PROVIDER="local",
        LOCAL_EMBEDDING_MODEL="   ",
    )
    with pytest.raises(ConfigurationError, match="LOCAL_EMBEDDING_MODEL"):
        create_embedding_provider(settings)


def test_development_fake_provider_explicit() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="fake",
    )
    provider = create_embedding_provider(settings)
    assert isinstance(provider, DeterministicFakeEmbeddingProvider)


@pytest.mark.asyncio
async def test_pg_store_rejects_dimension_mismatch() -> None:
    from uuid import uuid4

    from app.core.exceptions import ValidationError
    from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
    from app.domain.interfaces.clinical_vector_store import ClinicalVectorIndexRecord
    from app.infrastructure.repositories.clinical_retrieval_vector_repository import (
        SQLAlchemyClinicalVectorStore,
    )

    class _Session:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("should not execute")

        async def flush(self) -> None:
            raise AssertionError("should not flush")

    store = SQLAlchemyClinicalVectorStore(_Session(), storage_vector_dimension=384)
    record = ClinicalVectorIndexRecord(
        evidence_id="x:1",
        patient_id=uuid4(),
        organization_id=None,
        source_type=ClinicalEvidenceSourceType.MEDICAL_RECORD,
        source_id=uuid4(),
        event_time=None,
        canonical_text="{}",
        embedding=[0.0] * 64,
        embedding_model="m",
        embedding_version="1",
        embedding_dimension=64,
        embedding_pooling_profile="deterministic_fake_v1",
        content_hash="abc",
    )
    with pytest.raises(ValidationError, match="storage vector dimension"):
        await store.upsert_batch([record])
