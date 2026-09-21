"""Patient domain entity."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entities.base import BaseEntity


@dataclass(kw_only=True)
class Patient(BaseEntity):
    """Healthcare patient record owned by an authenticated user."""

    owner_id: UUID
    organization_id: UUID | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str | None = None
    notes: str | None = None
    is_active: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
