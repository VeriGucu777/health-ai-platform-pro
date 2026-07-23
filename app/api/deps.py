"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user import UserDTO
from app.application.services.appointment_service import AppointmentService
from app.application.services.auth_service import AuthService
from app.application.services.health_measurement_analytics_service import (
    HealthMeasurementAnalyticsService,
)
from app.application.services.health_measurement_service import HealthMeasurementService
from app.application.services.medical_record_service import MedicalRecordService
from app.application.services.patient_service import PatientService
from app.application.services.patient_health_report_service import PatientHealthReportService
from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import decode_token
from app.domain.entities.user import UserRole
from app.infrastructure.database.session import get_db_session
from app.infrastructure.repositories.appointment_repository import SQLAlchemyAppointmentRepository
from app.infrastructure.repositories.health_measurement_repository import (
    SQLAlchemyHealthMeasurementRepository,
)
from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    """Return application settings stored on the FastAPI app instance."""
    return request.app.state.settings


async def get_db_session_from_app(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session using the app-scoped settings."""
    async for session in get_db_session(request.app.state.settings):
        yield session


def get_patient_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> PatientService:
    """Provide a PatientService bound to the current request session."""
    return PatientService(SQLAlchemyPatientRepository(session))


def get_appointment_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> AppointmentService:
    """Provide an AppointmentService bound to the current request session."""
    return AppointmentService(
        SQLAlchemyAppointmentRepository(session),
        SQLAlchemyPatientRepository(session),
    )


def get_medical_record_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> MedicalRecordService:
    """Provide a MedicalRecordService bound to the current request session."""
    return MedicalRecordService(
        SQLAlchemyMedicalRecordRepository(session),
        SQLAlchemyPatientRepository(session),
    )


def get_health_measurement_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> HealthMeasurementService:
    """Provide a HealthMeasurementService bound to the current request session."""
    return HealthMeasurementService(
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyPatientRepository(session),
    )


def get_health_measurement_analytics_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
) -> HealthMeasurementAnalyticsService:
    """Provide a HealthMeasurementAnalyticsService bound to the current request session."""
    return HealthMeasurementAnalyticsService(
        SQLAlchemyHealthMeasurementRepository(session),
        SQLAlchemyPatientRepository(session),
    )


def get_patient_health_report_service(
    patient_service: Annotated[PatientService, Depends(get_patient_service)],
    medical_record_service: Annotated[MedicalRecordService, Depends(get_medical_record_service)],
    analytics_service: Annotated[
        HealthMeasurementAnalyticsService,
        Depends(get_health_measurement_analytics_service),
    ],
) -> PatientHealthReportService:
    """Provide a PatientHealthReportService composed from existing read-only services."""
    return PatientHealthReportService(
        patient_service,
        medical_record_service,
        analytics_service,
    )


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session_from_app)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthService:
    """Provide an AuthService bound to the current request session."""
    return AuthService(SQLAlchemyUserRepository(session), settings)


# Re-export common dependencies with type aliases for route signatures
DbSession = Annotated[AsyncSession, Depends(get_db_session_from_app)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: AppSettings,
) -> UUID:
    """Extract and validate the authenticated user ID from a JWT access token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials, settings)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        return UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserDTO:
    """Load the authenticated user from the database."""
    try:
        return await auth_service.get_current_user(user_id)
    except AppException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentUser = Annotated[UserDTO, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., UserDTO]:
    """Dependency factory that restricts access to users with specific roles."""

    async def role_checker(current_user: CurrentUser) -> UserDTO:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
