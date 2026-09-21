"""Index freshness fingerprint including embedding model/version/pooling."""

from __future__ import annotations

import hashlib


def compute_index_fingerprint(
    *,
    content_hash: str,
    embedding_model: str,
    embedding_version: str,
    embedding_dimension: int,
    embedding_pooling_profile: str,
) -> str:
    """Stable fingerprint for skip-re-embed decisions."""
    payload = (
        f"{content_hash}|{embedding_model}|{embedding_version}|"
        f"{embedding_dimension}|{embedding_pooling_profile}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
