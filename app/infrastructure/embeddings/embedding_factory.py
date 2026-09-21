"""Resolve EmbeddingProvider from settings — production fail-fast, no silent fake."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from app.application.clinical_retrieval.constants import FAKE_EMBEDDING_MODEL
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.infrastructure.embeddings.deterministic_fake_embedding_provider import (
    DeterministicFakeEmbeddingProvider,
)
from app.infrastructure.embeddings.fastembed_model_catalog import validate_production_embedding_model_config
from app.infrastructure.embeddings.local_embedding_provider import LocalEmbeddingProvider

if TYPE_CHECKING:
    from collections.abc import Hashable

_provider_cache: dict[tuple[Hashable, ...], EmbeddingProvider] = {}


def _provider_cache_key(settings: Settings) -> tuple[Hashable, ...]:
    kind = (settings.embedding_provider or "").strip().lower()
    return (
        kind,
        settings.local_embedding_model.strip() if kind == "local" else "",
        settings.embedding_version.strip(),
        settings.fake_embedding_dimensions if kind == "fake" else 0,
        settings.clinical_retrieval_vector_dimension,
    )


def reset_embedding_provider_cache() -> None:
    """Clear cached providers — test isolation only."""
    _provider_cache.clear()


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Return a process-scoped embedding provider (single ONNX model load per config)."""
    key = _provider_cache_key(settings)
    cached = _provider_cache.get(key)
    if cached is not None:
        return cached
    provider = create_embedding_provider(settings)
    _provider_cache[key] = provider
    return provider


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build embedding provider; never fall back to fake in production/staging."""
    kind = (settings.embedding_provider or "").strip().lower()
    storage_dim = settings.clinical_retrieval_vector_dimension

    if settings.is_production or settings.environment == "staging":
        if kind != "local":
            raise ConfigurationError(
                "Production and staging require EMBEDDING_PROVIDER=local. "
                "Fake embeddings are not permitted.",
            )
        if sys.platform == "win32":
            raise ConfigurationError(
                "Local embeddings are not supported on Windows hosts. Deploy on Linux/Docker.",
            )
        if not settings.local_embedding_model.strip():
            raise ConfigurationError("LOCAL_EMBEDDING_MODEL is required in production/staging.")
        validate_production_embedding_model_config(
            model_name=settings.local_embedding_model,
            storage_dimension=storage_dim,
        )
        provider = LocalEmbeddingProvider(
            model_name=settings.local_embedding_model,
            embedding_version=settings.embedding_version,
        )
    elif kind == "local":
        if sys.platform == "win32":
            try:
                import onnxruntime  # noqa: F401
            except ImportError as exc:
                raise ConfigurationError(
                    "Local embeddings require the Linux/Docker production runtime (ONNX + FastEmbed). "
                    "On Windows, use EMBEDDING_PROVIDER=fake for API/unit tests only.",
                ) from exc
        if not settings.local_embedding_model.strip():
            raise ConfigurationError("LOCAL_EMBEDDING_MODEL is required when EMBEDDING_PROVIDER=local.")
        validate_production_embedding_model_config(
            model_name=settings.local_embedding_model,
            storage_dimension=storage_dim,
        )
        provider = LocalEmbeddingProvider(
            model_name=settings.local_embedding_model,
            embedding_version=settings.embedding_version,
        )
    elif kind == "fake":
        provider = DeterministicFakeEmbeddingProvider(
            dimensions=settings.fake_embedding_dimensions,
            embedding_version=settings.embedding_version,
        )
    else:
        raise ConfigurationError(
            "EMBEDDING_PROVIDER must be set explicitly: "
            "'local' for real embeddings or 'fake' for development/tests only.",
        )

    if provider.model_name == FAKE_EMBEDDING_MODEL and (
        settings.is_production or settings.environment == "staging"
    ):
        raise ConfigurationError("Deterministic fake embedding cannot be used in production.")

    if kind == "local" and provider.dimensions != storage_dim:
        raise ConfigurationError(
            f"Local model dimension ({provider.dimensions}) must match "
            f"CLINICAL_RETRIEVAL_VECTOR_DIMENSION ({storage_dim}). "
            "Adjust the model or database vector column via migration.",
        )

    return provider
