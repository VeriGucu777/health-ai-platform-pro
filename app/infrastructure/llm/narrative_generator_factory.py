"""Resolve ClinicalNarrativeGenerator from settings."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.domain.interfaces.clinical_narrative_generator import ClinicalNarrativeGenerator
from app.infrastructure.llm.deterministic_fake_narrative_generator import (
    DeterministicFakeNarrativeGenerator,
)
from app.infrastructure.llm.external_narrative_generator import ExternalClinicalNarrativeGenerator

_generator_cache: dict[tuple[str, ...], ClinicalNarrativeGenerator] = {}


def reset_clinical_narrative_generator_cache() -> None:
    _generator_cache.clear()


def _cache_key(settings: Settings) -> tuple[str, ...]:
    kind = (settings.clinical_narrative_provider or "").strip().lower()
    return (
        kind,
        settings.clinical_narrative_external_model.strip(),
        settings.clinical_narrative_external_base_url.strip(),
    )


def get_clinical_narrative_generator(settings: Settings) -> ClinicalNarrativeGenerator:
    key = _cache_key(settings)
    cached = _generator_cache.get(key)
    if cached is not None:
        return cached
    provider = create_clinical_narrative_generator(settings)
    _generator_cache[key] = provider
    return provider


def create_clinical_narrative_generator(settings: Settings) -> ClinicalNarrativeGenerator:
    kind = (settings.clinical_narrative_provider or "").strip().lower()
    if settings.is_production or settings.environment == "staging":
        if kind == "fake":
            raise ConfigurationError(
                "Deterministic fake clinical narrative generator cannot be used in production/staging.",
            )
        if kind != "external":
            raise ConfigurationError(
                "Production/staging require CLINICAL_NARRATIVE_PROVIDER=external "
                "(local/self-hosted LLM is not configured in v1).",
            )
    if not kind:
        raise ConfigurationError(
            "CLINICAL_NARRATIVE_PROVIDER must be set explicitly: 'fake' (dev/tests) or 'external'.",
        )
    if kind == "fake":
        return DeterministicFakeNarrativeGenerator()
    if kind == "external":
        return ExternalClinicalNarrativeGenerator(settings)
    raise ConfigurationError(
        f"Unsupported CLINICAL_NARRATIVE_PROVIDER {kind!r}. Use 'fake' or 'external'.",
    )
