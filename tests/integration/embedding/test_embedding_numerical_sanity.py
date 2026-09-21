"""Numerical sanity for production local embedding provider."""

from __future__ import annotations

import math

import pytest

from app.core.exceptions import ValidationError
@pytest.mark.asyncio
async def test_same_input_produces_identical_embeddings(production_local_embedding_provider) -> None:
    provider = production_local_embedding_provider
    text = "deterministic probe text for clinical retrieval"
    first = await provider.embed_documents([text])
    second = await provider.embed_documents([text])
    assert len(first) == 1
    assert first[0] == second[0]
    assert len(first[0]) == provider.dimensions


@pytest.mark.asyncio
async def test_embeddings_are_finite_and_unit_norm(production_local_embedding_provider) -> None:
    provider = production_local_embedding_provider
    vector = await provider.embed_query("norm check")
    assert all(math.isfinite(v) for v in vector)
    norm = math.sqrt(sum(v * v for v in vector))
    assert 0.99 <= norm <= 1.01


@pytest.mark.asyncio
async def test_empty_query_rejected(production_local_embedding_provider) -> None:
    provider = production_local_embedding_provider
    with pytest.raises(ValidationError, match="query must not be empty"):
        await provider.embed_query("   ")


@pytest.mark.asyncio
async def test_empty_document_batch_returns_empty(production_local_embedding_provider) -> None:
    provider = production_local_embedding_provider
    assert await provider.embed_documents([]) == []
