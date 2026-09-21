"""Ensure FastEmbed mean-pooling migration warning is not emitted for production model."""

from __future__ import annotations

import warnings

from app.infrastructure.embeddings.embedding_factory import get_embedding_provider, reset_embedding_provider_cache

_FASTEMBED_MEAN_POOLING_WARNING = (
    r".*now uses mean pooling instead of CLS embedding.*"
)


def test_production_model_load_has_no_mean_pooling_warning(production_local_embedding_settings) -> None:
    reset_embedding_provider_cache()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message=_FASTEMBED_MEAN_POOLING_WARNING,
            category=UserWarning,
        )
        provider = get_embedding_provider(production_local_embedding_settings)
        assert provider.dimensions == 384
