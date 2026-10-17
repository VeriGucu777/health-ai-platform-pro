"""Synthetic hypertension pilot QA fixtures (no PHI, no clinical interpretation)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.support.org_assigned_patient_harness import (
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
)

# Fixed sentinel values for API shape only — not used for staging, risk, or CDS claims.
_PILOT_MEASURED_AT = "2026-09-01T09:00:00Z"
_PILOT_SYSTOLIC = 118
_PILOT_DIASTOLIC = 76
_PILOT_HEART_RATE = 68


async def post_synthetic_vitals_for_pilot(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    patient_id: str,
) -> None:
    """Record systolic/diastolic BP and heart rate for technical flow validation."""
    payload = {
        "patient_id": patient_id,
        "measured_at": _PILOT_MEASURED_AT,
        "systolic_pressure": _PILOT_SYSTOLIC,
        "diastolic_pressure": _PILOT_DIASTOLIC,
        "heart_rate": _PILOT_HEART_RATE,
    }
    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    if response.status_code != 201:
        msg = f"expected 201 for synthetic vitals, got {response.status_code}: {response.text}"
        raise AssertionError(msg)


async def create_cardiology_encounter(
    client: AsyncClient,
    headers: dict[str, str],
    patient_id: str,
) -> dict:
    response = await client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        headers=headers,
        json={"specialty_key": "cardiology", "locale": "tr"},
    )
    if response.status_code != 201:
        msg = f"expected 201 for encounter, got {response.status_code}: {response.text}"
        raise AssertionError(msg)
    return response.json()


async def build_hypertension_pilot_qa_context(
    client: AsyncClient,
    user_repository,
    membership_repository,
    *,
    doctor_email: str = "htn-pilot-qa@example.com",
) -> dict[str, str | dict]:
    """Doctor with assigned patient, synthetic vitals, and active cardiology encounter."""
    headers = await register_and_login_doctor(client, email=doctor_email)
    patient_id = await create_assigned_patient_for_doctor_headers(
        client,
        user_repository,
        membership_repository,
        headers,
    )
    await post_synthetic_vitals_for_pilot(client, headers, patient_id=patient_id)
    encounter_detail = await create_cardiology_encounter(client, headers, patient_id)
    return {
        "headers": headers,
        "patient_id": patient_id,
        "encounter_id": encounter_detail["encounter"]["id"],
        "encounter_detail": encounter_detail,
    }
