"""Clinical retrieval vector ORM model (pgvector)."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.application.clinical_retrieval.constants import CLINICAL_RETRIEVAL_VECTOR_DIMENSION
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalRetrievalVectorModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Patient-scoped embedding index row for clinical evidence."""

    __tablename__ = "clinical_retrieval_vectors"
    __table_args__ = (UniqueConstraint("evidence_id", name="uq_clinical_retrieval_vectors_evidence_id"),)

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(32), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_pooling_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(CLINICAL_RETRIEVAL_VECTOR_DIMENSION),
        nullable=False,
    )
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
