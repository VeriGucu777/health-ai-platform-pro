"""Health measurement CRUD endpoint integration tests."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

PATIENT_PAYLOAD = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "phone": "+15551234567",
    "notes": "Initial consultation scheduled",
}

MEASUREMENT_PAYLOAD = {
    "measured_at": "2026-08-15T08:30:00Z",
    "blood_glucose": 120,
    "glucose_context": "fasting",
    "systolic_pressure": 120,
    "diastolic_pressure": 80,
    "heart_rate": 72,
    "weight_kg": 75.5,
    "insulin_units": 4.0,
    "meal_context": "breakfast",
    "exercise_minutes": 30,
    "notes": "Morning reading",
}


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "securepass123",
    first_name: str = "Test",
    last_name: str = "User",
) -> dict[str, str]:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": "patient",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_patient(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_health_measurement(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-owner@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id}
    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == patient_id
    assert Decimal(data["blood_glucose"]) == Decimal("120")
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_create_requires_at_least_one_trackable_value(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-no-value@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {
        "patient_id": patient_id,
        "measured_at": "2026-08-15T08:30:00Z",
        "glucose_context": "fasting",
        "meal_context": "breakfast",
        "notes": "Only context and notes",
    }
    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_context_or_notes_without_trackable_value(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(client, email="hm-context-only@example.com")
    patient_id = await _create_patient(client, headers)

    for payload in (
        {
            "patient_id": patient_id,
            "measured_at": "2026-08-15T08:30:00Z",
            "glucose_context": "fasting",
        },
        {
            "patient_id": patient_id,
            "measured_at": "2026-08-15T08:30:00Z",
            "meal_context": "breakfast",
        },
        {
            "patient_id": patient_id,
            "measured_at": "2026-08-15T08:30:00Z",
            "notes": "Notes only",
        },
    ):
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_numeric_validation_rejects_invalid_values(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-invalid-num@example.com")
    patient_id = await _create_patient(client, headers)

    invalid_payloads = [
        {"blood_glucose": 0},
        {"systolic_pressure": 120, "diastolic_pressure": 80, "heart_rate": 0},
        {"weight_kg": -1},
        {"insulin_units": -1},
        {"exercise_minutes": -5},
    ]
    for fields in invalid_payloads:
        payload = {
            "patient_id": patient_id,
            "measured_at": "2026-08-15T08:30:00Z",
            **fields,
        }
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_requires_blood_pressure_pair(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-bp-pair@example.com")
    patient_id = await _create_patient(client, headers)

    for payload in (
        {"systolic_pressure": 120},
        {"diastolic_pressure": 80},
    ):
        response = await client.post(
            "/api/v1/health-measurements",
            json={
                "patient_id": patient_id,
                "measured_at": "2026-08-15T08:30:00Z",
                **payload,
            },
            headers=headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_health_measurements(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-lister@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id}
    create_response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert create_response.status_code == 201

    response = await client.get("/api/v1/health-measurements", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_health_measurements_filter_by_patient_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-filter-patient@example.com")
    patient_a = await _create_patient(client, headers)
    patient_b_response = await client.post(
        "/api/v1/patients",
        json={**PATIENT_PAYLOAD, "first_name": "Jane"},
        headers=headers,
    )
    assert patient_b_response.status_code == 201
    patient_b = patient_b_response.json()["id"]

    for patient_id in (patient_a, patient_b):
        payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id, "blood_glucose": 110}
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        f"/api/v1/health-measurements?patient_id={patient_a}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["patient_id"] == patient_a


@pytest.mark.asyncio
async def test_list_health_measurements_filter_by_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-filter-date@example.com")
    patient_id = await _create_patient(client, headers)

    measurements = [
        ("2026-08-15T08:00:00Z", 120),
        ("2026-08-16T08:00:00Z", 130),
        ("2026-08-17T08:00:00Z", 140),
    ]
    for measured_at, glucose in measurements:
        payload = {
            "patient_id": patient_id,
            "measured_at": measured_at,
            "blood_glucose": glucose,
        }
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/health-measurements"
        "?date_from=2026-08-16T00:00:00Z&date_to=2026-08-16T23:59:59Z",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert Decimal(data["items"][0]["blood_glucose"]) == Decimal("130")


@pytest.mark.asyncio
async def test_list_health_measurements_filter_by_glucose_context(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-filter-glucose@example.com")
    patient_id = await _create_patient(client, headers)

    for glucose_context in ("fasting", "post_meal"):
        payload = {
            "patient_id": patient_id,
            "measured_at": "2026-08-15T08:30:00Z",
            "blood_glucose": 120,
            "glucose_context": glucose_context,
        }
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/health-measurements?glucose_context=post_meal",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["glucose_context"] == "post_meal"


@pytest.mark.asyncio
async def test_list_health_measurements_invalid_date_range(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-invalid-date@example.com")

    response = await client.get(
        "/api/v1/health-measurements"
        "?date_from=2026-08-20T00:00:00Z&date_to=2026-08-10T00:00:00Z",
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["message"] == "date_from must be before or equal to date_to"


@pytest.mark.asyncio
async def test_list_health_measurements_pagination(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-pagination@example.com")
    patient_id = await _create_patient(client, headers)

    for index in range(5):
        payload = {
            "patient_id": patient_id,
            "measured_at": f"2026-08-{10 + index:02d}T08:00:00Z",
            "blood_glucose": 100 + index,
        }
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    page_one = await client.get("/api/v1/health-measurements?page=1&page_size=2", headers=headers)
    page_two = await client.get("/api/v1/health-measurements?page=2&page_size=2", headers=headers)
    assert page_one.status_code == 200 and page_two.status_code == 200
    data_one = page_one.json()
    data_two = page_two.json()
    assert data_one["total"] == 5
    assert data_one["pages"] == 3
    assert len(data_one["items"]) == 2
    assert len(data_two["items"]) == 2


@pytest.mark.asyncio
async def test_list_health_measurements_default_newest_first(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-order-desc@example.com")
    patient_id = await _create_patient(client, headers)

    for measured_at, glucose in (
        ("2026-08-10T08:00:00Z", 100),
        ("2026-08-12T08:00:00Z", 120),
        ("2026-08-11T08:00:00Z", 110),
    ):
        payload = {"patient_id": patient_id, "measured_at": measured_at, "blood_glucose": glucose}
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get("/api/v1/health-measurements", headers=headers)
    assert response.status_code == 200
    glucose_values = [Decimal(item["blood_glucose"]) for item in response.json()["items"]]
    assert glucose_values == [Decimal("120"), Decimal("110"), Decimal("100")]


@pytest.mark.asyncio
async def test_list_health_measurements_sort_ascending(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-order-asc@example.com")
    patient_id = await _create_patient(client, headers)

    for measured_at, glucose in (
        ("2026-08-12T08:00:00Z", 120),
        ("2026-08-10T08:00:00Z", 100),
        ("2026-08-11T08:00:00Z", 110),
    ):
        payload = {"patient_id": patient_id, "measured_at": measured_at, "blood_glucose": glucose}
        response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/health-measurements?sort_order=asc",
        headers=headers,
    )
    assert response.status_code == 200
    glucose_values = [Decimal(item["blood_glucose"]) for item in response.json()["items"]]
    assert glucose_values == [Decimal("100"), Decimal("110"), Decimal("120")]


@pytest.mark.asyncio
async def test_retrieve_health_measurement(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-reader@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    measurement_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == measurement_id


@pytest.mark.asyncio
async def test_update_health_measurement(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-updater@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    measurement_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/health-measurements/{measurement_id}",
        json={"heart_rate": 68, "notes": "Updated reading"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["heart_rate"] == 68
    assert data["notes"] == "Updated reading"


@pytest.mark.asyncio
async def test_update_cannot_clear_all_trackable_values(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-clear-values@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {
        "patient_id": patient_id,
        "measured_at": "2026-08-15T08:30:00Z",
        "blood_glucose": 120,
    }
    created = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    measurement_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/health-measurements/{measurement_id}",
        json={"blood_glucose": None},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_patch_ignores_patient_id(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-patch-patient@example.com")
    patient_a = await _create_patient(client, headers)
    patient_b_response = await client.post(
        "/api/v1/patients",
        json={**PATIENT_PAYLOAD, "first_name": "Jane"},
        headers=headers,
    )
    assert patient_b_response.status_code == 201
    patient_b = patient_b_response.json()["id"]

    created = await client.post(
        "/api/v1/health-measurements",
        json={
            "patient_id": patient_a,
            "measured_at": "2026-08-15T08:30:00Z",
            "blood_glucose": 120,
        },
        headers=headers,
    )
    measurement_id = created.json()["id"]
    original_patient_id = created.json()["patient_id"]

    response = await client.patch(
        f"/api/v1/health-measurements/{measurement_id}",
        json={"patient_id": patient_b, "heart_rate": 70},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["heart_rate"] == 70
    assert data["patient_id"] == original_patient_id


@pytest.mark.asyncio
async def test_delete_health_measurement(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-deleter@example.com")
    patient_id = await _create_patient(client, headers)

    payload = {**MEASUREMENT_PAYLOAD, "patient_id": patient_id}
    created = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    measurement_id = created.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health-measurements")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_user_access_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="hm-owner2@example.com")
    other_headers = await _register_and_login(client, email="hm-other@example.com")

    patient_id = await _create_patient(client, owner_headers)
    payload = {
        "patient_id": patient_id,
        "measured_at": "2026-08-15T08:30:00Z",
        "blood_glucose": 120,
    }
    created = await client.post("/api/v1/health-measurements", json=payload, headers=owner_headers)
    measurement_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["success"] is False

    patch_response = await client.patch(
        f"/api/v1/health-measurements/{measurement_id}",
        json={"heart_rate": 60},
        headers=other_headers,
    )
    assert patch_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/health-measurements/{measurement_id}",
        headers=other_headers,
    )
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_create_with_foreign_patient_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="hm-patient-owner@example.com")
    other_headers = await _register_and_login(client, email="hm-patient-other@example.com")

    patient_id = await _create_patient(client, owner_headers)
    payload = {
        "patient_id": patient_id,
        "measured_at": "2026-08-15T08:30:00Z",
        "blood_glucose": 120,
    }

    response = await client.post("/api/v1/health-measurements", json=payload, headers=other_headers)
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_create_with_nonexistent_patient_returns_not_found(client: AsyncClient) -> None:
    headers = await _register_and_login(client, email="hm-no-patient@example.com")

    payload = {
        "patient_id": "00000000-0000-0000-0000-000000000001",
        "measured_at": "2026-08-15T08:30:00Z",
        "blood_glucose": 120,
    }
    response = await client.post("/api/v1/health-measurements", json=payload, headers=headers)
    assert response.status_code == 404
    assert response.json()["message"] == "Patient not found"


@pytest.mark.asyncio
async def test_list_with_foreign_patient_id_returns_not_found(client: AsyncClient) -> None:
    owner_headers = await _register_and_login(client, email="hm-list-owner@example.com")
    other_headers = await _register_and_login(client, email="hm-list-other@example.com")

    patient_id = await _create_patient(client, owner_headers)

    response = await client.get(
        f"/api/v1/health-measurements?patient_id={patient_id}",
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["message"] == "Patient not found"
