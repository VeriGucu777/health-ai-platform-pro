"""Shared doctor + assigned-patient setup for clinical API integration tests."""

from httpx import AsyncClient

from tests.support.org_assigned_patient_harness import (
    PATIENT_PAYLOAD,
    create_assigned_patient_for_doctor_headers,
    register_and_login_doctor,
)

NARRATIVE_PATIENT_PAYLOAD = {
    "first_name": "Narr",
    "last_name": "Patient",
    "date_of_birth": "1988-04-12",
    "gender": "female",
}

TIMELINE_PATIENT_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Timeline",
    "date_of_birth": "1985-03-10",
    "gender": "female",
}

register_and_login = register_and_login_doctor


async def assigned_patient_for_doctor(
    client: AsyncClient,
    user_repository,
    membership_repository,
    doctor_headers: dict[str, str],
    *,
    patient_payload: dict | None = None,
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
