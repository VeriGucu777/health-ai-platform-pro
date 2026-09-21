"""Index fingerprint includes pooling profile and dimension."""

from app.application.clinical_retrieval.index_fingerprint import compute_index_fingerprint


def test_pooling_profile_change_changes_fingerprint() -> None:
    base_kwargs = {
        "content_hash": "abc",
        "embedding_model": "health-ai-platform/clinical-retrieval-multilingual-v1",
        "embedding_version": "3",
        "embedding_dimension": 384,
    }
    fp_mean = compute_index_fingerprint(**base_kwargs, embedding_pooling_profile="mean_l2_normalized_v1")
    fp_cls = compute_index_fingerprint(**base_kwargs, embedding_pooling_profile="cls_v1")
    assert fp_mean != fp_cls
