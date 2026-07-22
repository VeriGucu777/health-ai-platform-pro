"""Import all ORM models here so Alembic autogenerate can discover them."""

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.appointment import AppointmentModel
from app.infrastructure.database.models.health_measurement import HealthMeasurementModel
from app.infrastructure.database.models.medical_record import MedicalRecordModel
from app.infrastructure.database.models.patient import PatientModel
from app.infrastructure.database.models.user import UserModel

__all__ = [
    "Base",
    "AppointmentModel",
    "HealthMeasurementModel",
    "MedicalRecordModel",
    "PatientModel",
    "UserModel",
]
