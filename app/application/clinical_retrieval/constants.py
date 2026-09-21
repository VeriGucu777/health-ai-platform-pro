"""Clinical RAG retrieval constants."""

RETRIEVAL_VERSION = "rag_retrieval_v1"
DEFAULT_TOP_K = 5
MAX_TOP_K = 20
FAKE_EMBEDDING_MODEL = "deterministic_fake_v1"
"""In-memory / explicit test-only fake dimension — not used for pgvector schema."""
FAKE_EMBEDDING_DIMENSIONS = 64
"""Fixed pgvector column size for production local model (e.g. BGE-small-en-v1.5)."""
CLINICAL_RETRIEVAL_VECTOR_DIMENSION = 384
CLINICAL_RETRIEVAL_EMBEDDING_MODEL = "health-ai-platform/clinical-retrieval-multilingual-v1"
CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE = "mean_l2_normalized_v1"
DEFAULT_LOCAL_EMBEDDING_MODEL = CLINICAL_RETRIEVAL_EMBEDDING_MODEL
DEFAULT_EMBEDDING_VERSION = "3"
