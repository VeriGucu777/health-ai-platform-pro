"""Deterministic fake embeddings — unit/API tests and explicit EMBEDDING_PROVIDER=fake only."""

from __future__ import annotations

import hashlib
import math
import re

from app.application.clinical_retrieval.constants import (
    FAKE_EMBEDDING_DIMENSIONS,
    FAKE_EMBEDDING_MODEL,
)
from app.domain.interfaces.embedding_provider import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class DeterministicFakeEmbeddingProvider(EmbeddingProvider):
    """Bag-of-token hashing vectors — no external API."""

    def __init__(
        self,
        dimensions: int = FAKE_EMBEDDING_DIMENSIONS,
        *,
        embedding_version: str = "1",
    ) -> None:
        self._dimensions = dimensions
        self._embedding_version = embedding_version

    @property
    def model_name(self) -> str:
        return FAKE_EMBEDDING_MODEL

    @property
    def embedding_version(self) -> str:
        return self._embedding_version

    @property
    def pooling_profile(self) -> str:
        return "deterministic_fake_v1"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._vectorize(query)

    def _vectorize(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self._dimensions
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]
