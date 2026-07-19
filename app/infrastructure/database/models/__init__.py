"""Import all ORM models here so Alembic autogenerate can discover them."""

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.patient import PatientModel
from app.infrastructure.database.models.user import UserModel

__all__ = ["Base", "PatientModel", "UserModel"]
