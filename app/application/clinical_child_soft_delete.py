"""Shared soft-delete helpers for patient-scoped clinical child records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

from app.domain.entities.base import BaseEntity

ClinicalChildT = TypeVar("ClinicalChildT", bound=BaseEntity)


def soft_deactivate_clinical_child(
    entity: ClinicalChildT,
    *,
    deactivated_at: datetime | None = None,
) -> ClinicalChildT:
    """Mark a clinical child row inactive (idempotent)."""
    when = deactivated_at or datetime.now(UTC)
    if getattr(entity, "is_active", True):
        entity.is_active = False  # type: ignore[attr-defined]
        entity.deleted_at = when  # type: ignore[attr-defined]
        entity.touch()
    return entity
