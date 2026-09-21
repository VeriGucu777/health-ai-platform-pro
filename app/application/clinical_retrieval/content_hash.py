"""Stable content hashing for incremental indexing."""

from __future__ import annotations

import hashlib


def compute_content_hash(canonical_text: str) -> str:
    """SHA-256 hex digest of canonical retrieval text."""
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
