"""Verify FastEmbed catalog and production multilingual model choice."""

from __future__ import annotations

from app.application.clinical_retrieval.constants import (
    CLINICAL_RETRIEVAL_EMBEDDING_MODEL,
    CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE,
    CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    DEFAULT_LOCAL_EMBEDDING_MODEL,
)
from app.infrastructure.embeddings.fastembed_model_catalog import (
    PRODUCTION_MULTILINGUAL_EMBEDDING_MODEL,
    list_fastembed_text_models,
    validate_production_embedding_model_config,
)


def test_production_default_is_multilingual_384_in_fastembed_catalog() -> None:
    models = list_fastembed_text_models()
    by_name = {str(row["model"]): row for row in models}
    assert DEFAULT_LOCAL_EMBEDDING_MODEL == CLINICAL_RETRIEVAL_EMBEDDING_MODEL
    assert CLINICAL_RETRIEVAL_EMBEDDING_MODEL in by_name
    assert int(by_name[CLINICAL_RETRIEVAL_EMBEDDING_MODEL]["dim"]) == CLINICAL_RETRIEVAL_VECTOR_DIMENSION
    assert PRODUCTION_MULTILINGUAL_EMBEDDING_MODEL == CLINICAL_RETRIEVAL_EMBEDDING_MODEL

    description = str(by_name[CLINICAL_RETRIEVAL_EMBEDDING_MODEL]["description"]).lower()
    assert "multilingual" in description
    assert CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE.startswith("mean_l2")


def test_validate_production_model_matches_storage_dimension() -> None:
    selected = validate_production_embedding_model_config(
        model_name=DEFAULT_LOCAL_EMBEDDING_MODEL,
        storage_dimension=CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    )
    assert int(selected["dim"]) == CLINICAL_RETRIEVAL_VECTOR_DIMENSION
