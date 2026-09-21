"""API v1 router — mounts all v1 endpoint modules."""

from fastapi import APIRouter, Depends

from app.api.clinical_rbac_guard import enforce_clinical_role_with_audit
from app.api.v1.endpoints import (
    appointments,
    auth,
    diabetes_risk_assessment,
    health,
    heart_disease_risk_assessment,
    health_measurement_analytics,
    health_measurements,
    medical_records,
    metrics,
    organizations,
    patient_assignments,
    patient_consents,
    patient_clinical_narrative,
    patient_clinical_retrieval,
    patient_clinical_summary,
    patient_clinical_timeline,
    patient_health_reports,
    patients,
    risk_assessment_history,
    stroke_risk_assessment,
)


def create_api_v1_router(prefix: str = "/api/v1") -> APIRouter:
    """Build the v1 API router with a configurable prefix."""
    api_v1_router = APIRouter(prefix=prefix)
    api_v1_router.include_router(health.router, tags=["Health"])
    api_v1_router.include_router(metrics.router, tags=["Observability"])
    api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    api_v1_router.include_router(
        organizations.router,
        prefix="/organizations",
        tags=["Organizations"],
    )
    api_v1_router.include_router(
        patient_assignments.router,
        prefix="/patients",
        tags=["Patient Assignments"],
    )
    api_v1_router.include_router(
        patient_consents.router,
        prefix="/patients",
        tags=["Patient Consents"],
    )
    _clinical = [Depends(enforce_clinical_role_with_audit)]
    api_v1_router.include_router(
        patients.router,
        prefix="/patients",
        tags=["Patients"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        patient_health_reports.router,
        prefix="/patients",
        tags=["Patient Health Reports"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        patient_clinical_timeline.router,
        prefix="/patients",
        tags=["Patient Clinical Timeline"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        patient_clinical_summary.router,
        prefix="/patients",
        tags=["Patient Clinical Summary"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        patient_clinical_retrieval.router,
        prefix="/patients",
        tags=["Patient Clinical Retrieval"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        patient_clinical_narrative.router,
        prefix="/patients",
        tags=["Patient Clinical Narrative"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        diabetes_risk_assessment.router,
        prefix="/patients",
        tags=["Diabetes Risk Assessment"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        heart_disease_risk_assessment.router,
        prefix="/patients",
        tags=["Heart Disease Risk Assessment"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        stroke_risk_assessment.router,
        prefix="/patients",
        tags=["Stroke Risk Assessment"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        risk_assessment_history.router,
        prefix="/patients",
        tags=["Risk Assessment History"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        appointments.router,
        prefix="/appointments",
        tags=["Appointments"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        medical_records.router,
        prefix="/medical-records",
        tags=["Medical Records"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        health_measurements.router,
        prefix="/health-measurements",
        tags=["Health Measurements"],
        dependencies=_clinical,
    )
    api_v1_router.include_router(
        health_measurement_analytics.router,
        prefix="/health-measurements/analytics",
        tags=["Health Measurement Analytics"],
        dependencies=_clinical,
    )
    return api_v1_router
