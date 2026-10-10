"""Deterministic manifest hashing for controlled vocabulary."""

from __future__ import annotations

import hashlib
import json

from app.domain.clinical_vocabulary.models import ControlledVocabularyManifest

EMPTY_VOCABULARY_MANIFEST_PAYLOAD = "controlled_vocab:v1:empty"


def vocabulary_manifest_hash(manifest: ControlledVocabularyManifest) -> str:
    """SHA-256 over canonical term keys (order-independent)."""
    if not manifest.terms:
        return hashlib.sha256(EMPTY_VOCABULARY_MANIFEST_PAYLOAD.encode("utf-8")).hexdigest()
    canonical = [
        {
            "key": term.key,
            "category": term.category.value,
            "status": term.status.value,
            "version_added": term.version_added,
        }
        for term in sorted(manifest.terms, key=lambda t: t.key)
    ]
    payload = (
        f"controlled_vocab:v1:{manifest.vocabulary_id}:{manifest.vocabulary_version}:"
        + json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
