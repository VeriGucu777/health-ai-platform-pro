"""Medical record CRUD endpoint integration tests."""

import pytest
from httpx import AsyncClient

from tests.support.org_assigned_patient_harness import (
    PATIENT_PAYLOAD,
    create_assigned_patient_for_doctor_headers as _create_patient,
    create_assigned_patients_for_doctor_email,
    register_and_login_doctor as _register_and_login,
)


MEDICAL_RECORD_PAYLOAD = {
    "record_date": "2026-08-15T10:30:00Z",
    "record_type": "visit",
    "title": "Annual checkup",
    "description": "Routine examination",
    "diagnosis": "Hypertension — decision support only",
    "treatment": "Lifestyle modifications recommended",
    "medications": "Lisinopril 10mg daily",
    "doctor_name": "Dr. Smith",
    "hospital_name": "City General Hospital",
    "notes": "Follow up in 3 months",
}






@pytest.mark.asyncio
async def test_create_medical_record(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-owner@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["record_type"] == "visit"
    assert data["title"] == "Annual checkup"
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_list_medical_records(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-lister@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    create_response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    assert create_response.status_code == 201

    response = await client.get("/api/v1/medical-records", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_list_medical_records_filter_by_patient_id(client: AsyncClient, user_repository, membership_repository,) -> None:
    email = "mr-filter-patient@example.com"
    headers = await _register_and_login(client, email=email)
    patient_a, patient_b = await create_assigned_patients_for_doctor_email(
        client,
        user_repository,
        membership_repository,
        doctor_email=email,
        patient_payloads=[PATIENT_PAYLOAD, {**PATIENT_PAYLOAD, "first_name": "Jane"}],
    )

    for patient_id in (patient_a, patient_b):
        payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
        response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        f"/api/v1/medical-records?patient_id={patient_a}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["patient_id"] == patient_a


@pytest.mark.asyncio
async def test_list_medical_records_filter_by_record_type(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-filter-type@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    for record_type in ("visit", "lab_result"):
        payload = {
            **MEDICAL_RECORD_PAYLOAD,
            "patient_id": patient_id,
            "record_type": record_type,
            "title": f"Record {record_type}",
        }
        response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/medical-records?record_type=lab_result",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["record_type"] == "lab_result"


@pytest.mark.asyncio
async def test_list_medical_records_filter_by_patient_id_and_record_type(
    client: AsyncClient,
    user_repository,
    membership_repository,
) -> None:
    headers = await _register_and_login(client, email="mr-filter-combined@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    records = [
        {"record_type": "visit", "title": "Visit record"},
        {"record_type": "lab_result", "title": "Lab record"},
        {"record_type": "lab_result", "title": "Another lab"},
    ]
    for record in records:
        payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id, **record}
        response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        f"/api/v1/medical-records?patient_id={patient_id}&record_type=lab_result",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["record_type"] == "lab_result" for item in data["items"])


@pytest.mark.asyncio
async def test_retrieve_medical_record(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-reader@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    medical_record_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/medical-records/{medical_record_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == medical_record_id


@pytest.mark.asyncio
async def test_update_medical_record(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-updater@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    medical_record_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/medical-records/{medical_record_id}",
        json={"title": "Updated checkup", "notes": "Follow up completed"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated checkup"
    assert data["notes"] == "Follow up completed"
    assert data["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_delete_medical_record(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-deleter@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    medical_record_id = created.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/medical-records/{medical_record_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/medical-records/{medical_record_id}",
        headers=headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient, user_repository, membership_repository,) -> None:
    response = await client.get("/api/v1/medical-records")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_access_returns_not_found(client: AsyncClient, user_repository, membership_repository,) -> None:
    owner_email = "mr-owner2@example.com"
    other_email = "mr-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)

    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        extra_org_doctor_emails=(other_email,),
    )
    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/medical-records", json=payload, headers=owner_headers)
    medical_record_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/medical-records/{medical_record_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["success"] is False

    patch_response = await client.patch(
        f"/api/v1/medical-records/{medical_record_id}",
        json={"title": "Unauthorized update"},
        headers=other_headers,
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/medical-records/{medical_record_id}",
        headers=other_headers,
    )
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_create_with_foreign_patient_returns_not_found(client: AsyncClient, user_repository, membership_repository,) -> None:
    owner_email = "mr-patient-owner@example.com"
    other_email = "mr-patient-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)

    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        extra_org_doctor_emails=(other_email,),
    )
    payload = {**MEDICAL_RECORD_PAYLOAD, "patient_id": patient_id}

    response = await client.post("/api/v1/medical-records", json=payload, headers=other_headers)
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_create_with_nonexistent_patient_returns_not_found(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-no-patient@example.com")

    payload = {
        **MEDICAL_RECORD_PAYLOAD,
        "patient_id": "00000000-0000-0000-0000-000000000001",
    }
    response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_list_with_foreign_patient_id_returns_not_found(client: AsyncClient, user_repository, membership_repository,) -> None:
    owner_email = "mr-list-owner@example.com"
    other_email = "mr-list-other@example.com"
    owner_headers = await _register_and_login(client, email=owner_email)
    other_headers = await _register_and_login(client, email=other_email)

    patient_id = await _create_patient(
        client,
        user_repository,
        membership_repository,
        owner_headers,
        extra_org_doctor_emails=(other_email,),
    )

    response = await client.get(
        f"/api/v1/medical-records?patient_id={patient_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_create_validation_error_missing_required_fields(client: AsyncClient, user_repository, membership_repository,) -> None:
    headers = await _register_and_login(client, email="mr-validation@example.com")
    patient_id = await _create_patient(client, user_repository, membership_repository, headers)

    payload = {
        "patient_id": patient_id,
        "record_date": "2026-08-15T10:30:00Z",
    }
    response = await client.post("/api/v1/medical-records", json=payload, headers=headers)
    assert response.status_code == 422
