"""User domain entity."""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.entities.base import BaseEntity


class UserRole(StrEnum):
    """Supported platform roles."""

    PATIENT = "patient"
    DOCTOR = "doctor"
    CLINIC_ADMIN = "clinic_admin"
    SYSTEM_ADMIN = "system_admin"


@dataclass(kw_only=True)
class User(BaseEntity):
    """Authenticated platform user."""

    email: str
    hashed_password: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
