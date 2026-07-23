"""API v1 router — mounts all v1 endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    appointments,
    auth,
    health,
    health_measurement_analytics,
    health_measurements,
    medical_records,
    patient_health_reports,
    patients,
)


def create_api_v1_router(prefix: str = "/api/v1") -> APIRouter:
    """Build the v1 API router with a configurable prefix."""
    api_v1_router = APIRouter(prefix=prefix)
    api_v1_router.include_router(health.router, tags=["Health"])
    api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    api_v1_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
    api_v1_router.include_router(
        patient_health_reports.router,
        prefix="/patients",
        tags=["Patient Health Reports"],
    )
    api_v1_router.include_router(
        appointments.router,
        prefix="/appointments",
        tags=["Appointments"],
    )
    api_v1_router.include_router(
        medical_records.router,
        prefix="/medical-records",
        tags=["Medical Records"],
    )
    api_v1_router.include_router(
        health_measurements.router,
        prefix="/health-measurements",
        tags=["Health Measurements"],
    )
    api_v1_router.include_router(
        health_measurement_analytics.router,
        prefix="/health-measurements/analytics",
        tags=["Health Measurement Analytics"],
    )
    return api_v1_router
