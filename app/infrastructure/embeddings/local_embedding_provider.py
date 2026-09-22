"""Self-hosted local embeddings via fastembed (no third-party API)."""

from __future__ import annotations

import asyncio
import math
import threading
from functools import partial

from app.application.clinical_retrieval.constants import (
    CLINICAL_RETRIEVAL_EMBEDDING_MODEL,
    CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE,
)
from app.core.exceptions import ConfigurationError, ValidationError
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.infrastructure.embeddings.clinical_retrieval_fastembed_model import (
    ensure_clinical_retrieval_embedding_model_registered,
)


class LocalEmbeddingProvider(EmbeddingProvider):
    """ONNX-based local text embeddings — clinical text stays on-premise."""

    def __init__(
        self,
        *,
        model_name: str,
        embedding_version: str,
    ) -> None:
        if not model_name.strip():
            raise ConfigurationError("LOCAL_EMBEDDING_MODEL must be set for local embeddings")
        self._model_name = model_name.strip()
        self._embedding_version = embedding_version.strip() or "1"
        self._model: object | None = None
        self._dimensions: int | None = None
        self._infer_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def embedding_version(self) -> str:
        return self._embedding_version

    @property
    def pooling_profile(self) -> str:
        return CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            self._ensure_model()
        return self._dimensions

    def _ensure_model(self) -> object:
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise ConfigurationError(
                "fastembed is required for EMBEDDING_PROVIDER=local. "
                "Install the production dependencies including fastembed.",
            ) from exc
        ensure_clinical_retrieval_embedding_model_registered()
        if self._model_name != CLINICAL_RETRIEVAL_EMBEDDING_MODEL:
            raise ConfigurationError(
                f"Unsupported LOCAL_EMBEDDING_MODEL {self._model_name!r}. "
                f"Production uses {CLINICAL_RETRIEVAL_EMBEDDING_MODEL!r} with explicit mean pooling.",
            )
        self._model = TextEmbedding(model_name=self._model_name)
        vectors = list(self._model.embed(["dimension probe"]))
        if not vectors:
            raise ConfigurationError(f"Local embedding model {self._model_name!r} returned no vectors")
        probe = list(vectors[0])
        self._validate_vector_values(probe)
        self._dimensions = len(probe)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vectors = await asyncio.to_thread(
            partial(self._embed_batch_locked, model, texts),
        )
        return [self._validate_and_copy(vector) for vector in vectors]

    async def embed_query(self, query: str) -> list[float]:
        cleaned = query.strip()
        if not cleaned:
            raise ValidationError("query must not be empty")
        rows = await self.embed_documents([cleaned])
        return rows[0]

    def _validate_and_copy(self, vector: list[float]) -> list[float]:
        self._validate_vector_values(vector)
        if len(vector) != self.dimensions:
            raise ValidationError(
                f"Embedding length {len(vector)} does not match provider dimension {self.dimensions}",
            )
        return list(vector)

    def _embed_batch_locked(self, model: object, texts: list[str]) -> list[list[float]]:
        with self._infer_lock:
            return [list(v) for v in model.embed(texts)]

    @staticmethod
    def _validate_vector_values(vector: list[float]) -> None:
        for value in vector:
            if not math.isfinite(value):
                raise ValidationError("Embedding vector contains non-finite values")
