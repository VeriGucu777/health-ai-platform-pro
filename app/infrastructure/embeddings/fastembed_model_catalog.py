"""FastEmbed-supported models — runtime catalog helpers for clinical retrieval."""

from __future__ import annotations

from typing import Any

from app.application.clinical_retrieval.constants import (
    CLINICAL_RETRIEVAL_EMBEDDING_MODEL,
    CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE,
    CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    DEFAULT_LOCAL_EMBEDDING_MODEL,
)
from app.core.exceptions import ConfigurationError
from app.infrastructure.embeddings.clinical_retrieval_fastembed_model import (
    ensure_clinical_retrieval_embedding_model_registered,
)

PRODUCTION_MULTILINGUAL_EMBEDDING_MODEL = DEFAULT_LOCAL_EMBEDDING_MODEL

STATIC_FASTEMBED_MODEL_DIMENSIONS: dict[str, int] = {
    CLINICAL_RETRIEVAL_EMBEDDING_MODEL: CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
}


def list_fastembed_text_models() -> list[dict[str, Any]]:
    """Return FastEmbed TextEmbedding supported models (requires onnxruntime)."""
    ensure_clinical_retrieval_embedding_model_registered()
    from fastembed import TextEmbedding

    return TextEmbedding.list_supported_models()


def multilingual_dense_models(models: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = models if models is not None else list_fastembed_text_models()
    result: list[dict[str, Any]] = []
    for row in rows:
        description = str(row.get("description", ""))
        if "multilingual" in description.lower():
            result.append(row)
    return result


def models_with_dimension(dimension: int, models: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = models if models is not None else list_fastembed_text_models()
    return [row for row in rows if int(row.get("dim", -1)) == dimension]


def validate_production_embedding_model_config(
    *,
    model_name: str,
    storage_dimension: int,
) -> dict[str, Any]:
    if not model_name.strip():
        raise ConfigurationError("LOCAL_EMBEDDING_MODEL must be set for local embeddings")
    normalized = model_name.strip()
    if normalized != CLINICAL_RETRIEVAL_EMBEDDING_MODEL:
        raise ConfigurationError(
            f"LOCAL_EMBEDDING_MODEL must be {CLINICAL_RETRIEVAL_EMBEDDING_MODEL!r} "
            f"({CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE}).",
        )
    try:
        ensure_clinical_retrieval_embedding_model_registered()
        models = {str(m["model"]): m for m in list_fastembed_text_models()}
        selected = models.get(normalized)
    except ImportError:
        static_dim = STATIC_FASTEMBED_MODEL_DIMENSIONS.get(normalized)
        if static_dim is None:
            raise ConfigurationError(
                f"LOCAL_EMBEDDING_MODEL {normalized!r} is not in the static FastEmbed catalog "
                "and ONNX runtime is unavailable to verify supported models.",
            ) from None
        selected = {"model": normalized, "dim": static_dim, "description": "static catalog"}
    if selected is None:
        raise ConfigurationError(
            f"LOCAL_EMBEDDING_MODEL {normalized!r} is not registered in FastEmbed.",
        )
    model_dim = int(selected["dim"])
    if model_dim != storage_dimension:
        raise ConfigurationError(
            f"Model {normalized!r} dimension ({model_dim}) does not match "
            f"CLINICAL_RETRIEVAL_VECTOR_DIMENSION ({storage_dimension}).",
        )
    return selected
