"""Shared helpers for cardiovascular risk assessment API tests."""

from typing import Any

from httpx import AsyncClient

from tests.support.org_assigned_patient_harness import (
    PATIENT_PAYLOAD,
    create_assigned_patient_for_doctor_email,
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
)

ASSESSMENT_DATE_RANGE = "date_from=2026-08-01T00:00:00Z&date_to=2026-08-31T23:59:59Z"

register_and_login = register_and_login_doctor


async def create_patient(
    client: AsyncClient,
    user_repository,
    membership_repository,
    doctor_headers: dict[str, str],
    *,
    patient_payload: dict[str, Any] | None = None,
    extra_org_doctor_emails: tuple[str, ...] = (),
) -> str:
    return await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        doctor_headers,
        patient_payload=patient_payload or PATIENT_PAYLOAD,
        extra_org_doctor_emails=extra_org_doctor_emails,
    )


async def create_measurement(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    patient_id: str,
    measured_at: str,
    blood_glucose: int | None = None,
    glucose_context: str | None = None,
    systolic_pressure: int | None = None,
    diastolic_pressure: int | None = None,
    heart_rate: int | None = None,
) -> None:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "measured_at": measured_at,
    }
    if blood_glucose is not None:
        payload["blood_glucose"] = blood_glucose
    if glucose_context is not None:
        payload["glucose_context"] = glucose_context
    if systolic_pressure is not None:
        payload["systolic_pressure"] = systolic_pressure
    if diastolic_pressure is not None:
        payload["diastolic_pressure"] = diastolic_pressure
    if heart_rate is not None:
        payload["heart_rate"] = heart_rate

    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 201
