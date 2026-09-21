"""Verify ONNX + FastEmbed + configured model loads in production-like runtime."""

from __future__ import annotations

from app.application.clinical_retrieval.constants import CLINICAL_RETRIEVAL_VECTOR_DIMENSION
def test_fastembed_and_onnx_import() -> None:
    import fastembed  # noqa: F401
    import onnxruntime

    assert onnxruntime.get_device() is not None


def test_production_local_provider_loads_and_dimension_matches(
    production_local_embedding_provider,
    production_local_embedding_settings,
) -> None:
    provider = production_local_embedding_provider
    assert provider.dimensions == CLINICAL_RETRIEVAL_VECTOR_DIMENSION
    assert provider.model_name == production_local_embedding_settings.local_embedding_model
