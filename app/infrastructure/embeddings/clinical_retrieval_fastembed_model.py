"""Explicit FastEmbed registration for clinical retrieval (mean pool + L2 norm)."""

from __future__ import annotations

from app.application.clinical_retrieval.constants import (
    CLINICAL_RETRIEVAL_EMBEDDING_MODEL,
    CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE,
    CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
)

_REGISTRATION_DONE = False


def ensure_clinical_retrieval_embedding_model_registered() -> None:
    """Register production embedding model with deterministic mean pooling (no CLS fallback).

    FastEmbed >=0.6 emits a UserWarning when loading the stock HuggingFace model id because
    library behaviour changed from CLS token to mean pooling. Sentence-Transformers models
    require mean pooling; we register an explicit custom model id bound to the same ONNX
    weights so pooling is deterministic and the warning is not emitted.
    """
    global _REGISTRATION_DONE
    if _REGISTRATION_DONE:
        return

    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType

    registered = {str(row["model"]) for row in TextEmbedding.list_supported_models()}
    if CLINICAL_RETRIEVAL_EMBEDDING_MODEL not in registered:
        TextEmbedding.add_custom_model(
            model=CLINICAL_RETRIEVAL_EMBEDDING_MODEL,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf="qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q"),
            dim=CLINICAL_RETRIEVAL_VECTOR_DIMENSION,
            model_file="model_optimized.onnx",
            description=(
                "Clinical retrieval TR/EN multilingual embeddings — explicit mean pooling, "
                f"L2 normalized ({CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE})."
            ),
            license="apache-2.0",
            size_in_gb=0.22,
        )
    _REGISTRATION_DONE = True
