"""Narrative generator factory configuration tests."""

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.llm.deterministic_fake_narrative_generator import (
    DeterministicFakeNarrativeGenerator,
)
from app.infrastructure.llm.narrative_generator_factory import (
    create_clinical_narrative_generator,
    reset_clinical_narrative_generator_cache,
)


def test_production_rejects_fake_narrative_provider() -> None:
    reset_clinical_narrative_generator_cache()
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="production-secret-key-minimum-length",
        CLINICAL_NARRATIVE_PROVIDER="fake",
    )
    with pytest.raises(ConfigurationError, match="fake"):
        create_clinical_narrative_generator(settings)


def test_development_fake_provider_explicit() -> None:
    reset_clinical_narrative_generator_cache()
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        CLINICAL_NARRATIVE_PROVIDER="fake",
    )
    provider = create_clinical_narrative_generator(settings)
    assert isinstance(provider, DeterministicFakeNarrativeGenerator)


def test_missing_provider_config_fail_fast() -> None:
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        CLINICAL_NARRATIVE_PROVIDER="",
    )
    with pytest.raises(ConfigurationError, match="CLINICAL_NARRATIVE_PROVIDER"):
        create_clinical_narrative_generator(settings)
