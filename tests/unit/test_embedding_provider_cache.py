"""Process-scoped embedding provider cache."""

from app.core.config import Settings
from app.infrastructure.embeddings.embedding_factory import (
    create_embedding_provider,
    get_embedding_provider,
    reset_embedding_provider_cache,
)


def test_get_embedding_provider_reuses_same_instance_for_local_config() -> None:
    reset_embedding_provider_cache()
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="fake",
        FAKE_EMBEDDING_DIMENSIONS=384,
    )
    first = get_embedding_provider(settings)
    second = get_embedding_provider(settings)
    assert first is second
    assert first is not create_embedding_provider(settings)


def test_cache_key_distinguishes_fake_dimensions() -> None:
    reset_embedding_provider_cache()
    common = {
        "ENVIRONMENT": "development",
        "JWT_SECRET_KEY": "test-secret-key-for-unit-tests-only",
        "EMBEDDING_PROVIDER": "fake",
    }
    a = get_embedding_provider(Settings(**common, FAKE_EMBEDDING_DIMENSIONS=384))
    b = get_embedding_provider(Settings(**common, FAKE_EMBEDDING_DIMENSIONS=128))
    assert a is not b
