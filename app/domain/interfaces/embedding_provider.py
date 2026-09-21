"""Embedding provider port for clinical retrieval."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Generate vector embeddings for documents and queries."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier persisted with indexed vectors."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector size."""

    @property
    @abstractmethod
    def embedding_version(self) -> str:
        """Version/config tag stored with indexed vectors for re-index decisions."""

    @property
    @abstractmethod
    def pooling_profile(self) -> str:
        """Pooling/normalization profile id included in index fingerprints."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple canonical texts in batch order."""

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Embed a single search query."""
