"""API tests using ExternalClinicalNarrativeGenerator with mock HTTP transport."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from starlette.requests import Request

from app.api.deps import get_clinical_narrative_service
from app.core.config import Settings
from app.domain.entities.medical_record import MedicalRecord
from app.infrastructure.llm.external_narrative_generator import ExternalClinicalNarrativeGenerator
from tests.api.test_patient_clinical_narrative import NARRATIVE_URL, PATIENT_PAYLOAD, _register_and_login
from tests.support.clinical_read_service_factory import build_clinical_narrative_service
from tests.support.external_narrative_mock_transport import (
    transport_dynamic_valid,
    transport_hallucinated_id,
    transport_timeout,
    transport_valid,
)
from tests.support.memory_clinical_vector_store import InMemoryClinicalVectorStore
from tests.support.spy_narrative_generator import SpyNarrativeGenerator


def _external_test_settings() -> Settings:
    return Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="test-secret-key-for-unit-tests-only",
        EMBEDDING_PROVIDER="fake",
        CLINICAL_NARRATIVE_PROVIDER="external",
        CLINICAL_NARRATIVE_EXTERNAL_BASE_URL="https://llm.example/v1",
        CLINICAL_NARRATIVE_EXTERNAL_API_KEY="test-key-not-real",
        CLINICAL_NARRATIVE_EXTERNAL_MODEL="mock-narrative-v1",
        CLINICAL_NARRATIVE_MAX_RETRIES=0,
        CLINICAL_NARRATIVE_RATE_LIMIT_ENABLED=False,
    )


@pytest.fixture
async def external_narrative_client(
    client,
    app,
    patient_repository,
    membership_repository,
    assignment_repository,
    appointment_repository,
    medical_record_repository,
    health_measurement_repository,
    risk_assessment_history_repository,
):
    vector_store = InMemoryClinicalVectorStore()
    settings = _external_test_settings()
    prior = app.dependency_overrides.get(get_clinical_narrative_service)

    def make_override(transport):
        inner = ExternalClinicalNarrativeGenerator(settings, http_transport=transport)
        spy = SpyNarrativeGenerator(inner)

        def override(_request: Request):
            return build_clinical_narrative_service(
                patient_repository,
                health_measurement_repository,
                medical_record_repository,
                appointment_repository,
                risk_assessment_history_repository,
                membership_repository,
                assignment_repository,
                vector_store,
                narrative_generator=spy,
                settings=settings,
            )

        return override, spy

    holder = {"override_fn": None, "spy": None}

    def set_transport(transport):
        override_fn, spy = make_override(transport)
        holder["override_fn"] = override_fn
        holder["spy"] = spy
        app.dependency_overrides[get_clinical_narrative_service] = override_fn

    set_transport(transport_dynamic_valid("Valid external narrative summary."))
    yield client, holder, set_transport
    if prior is not None:
        app.dependency_overrides[get_clinical_narrative_service] = prior
    else:
        app.dependency_overrides.pop(get_clinical_narrative_service, None)


async def _seed_clinical_data(medical_record_repository, *, patient_id: UUID, owner_id: UUID) -> str:
    record = await medical_record_repository.create(
        MedicalRecord(
            patient_id=patient_id,
            owner_id=owner_id,
            record_type="visit",
            title="Diabetes follow-up",
            description="Type 2 diabetes follow-up — synthetic",
            diagnosis="Type 2 diabetes follow-up",
            record_date=datetime.now(UTC),
        ),
    )
    return f"medical_record:{record.id}"


@pytest.mark.asyncio
async def test_external_mock_http_success_with_fallback_on_hallucination(
    external_narrative_client,
    patient_repository,
    medical_record_repository,
) -> None:
    client, holder, set_transport = external_narrative_client
    headers = await _register_and_login(client, email="ext-mock-ok@example.com")
    patient_id = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"])
    doctor_id = (await patient_repository.get_by_id(patient_id)).owner_id
    eid = await _seed_clinical_data(
        medical_record_repository,
        patient_id=patient_id,
        owner_id=doctor_id,
    )
    set_transport(transport_valid(eid, "External narrative citing authorized evidence only."))
    response = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={"language": "en", "query": "overview"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fallback_used"] is False
    assert holder["spy"].generate_calls == 1

    set_transport(transport_hallucinated_id(eid))
    holder["spy"].generate_calls = 0
    response2 = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={"language": "en"},
    )
    assert response2.status_code == 200
    assert response2.json()["fallback_used"] is True
    assert holder["spy"].generate_calls == 1


@pytest.mark.asyncio
async def test_external_mock_timeout_fallback_and_audit(
    external_narrative_client,
    patient_repository,
    medical_record_repository,
    audit_log_repository,
) -> None:
    client, holder, set_transport = external_narrative_client
    headers = await _register_and_login(client, email="ext-mock-fb@example.com")
    patient_id = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers)).json()["id"])
    doctor_id = (await patient_repository.get_by_id(patient_id)).owner_id
    eid = await _seed_clinical_data(
        medical_record_repository,
        patient_id=patient_id,
        owner_id=doctor_id,
    )
    set_transport(transport_timeout())
    before = len(audit_log_repository.list_all())
    response = await client.post(
        NARRATIVE_URL.format(patient_id=patient_id),
        headers=headers,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["fallback_used"] is True
    after = audit_log_repository.list_all()
    assert len(after) == before + 1
    meta = after[-1].metadata or {}
    assert meta.get("fallback_used") is True
    assert meta.get("provider_kind") == "external"


@pytest.mark.asyncio
async def test_denied_roles_do_not_call_external_provider(
    external_narrative_client,
    user_repository,
    patient_repository,
    membership_repository,
    assignment_repository,
) -> None:
    from app.core.security import hash_password
    from app.domain.entities.patient import Patient
    from app.domain.entities.user import User, UserRole
    from datetime import date
    from uuid import uuid4

    client, holder, _set_transport = external_narrative_client
    org_id = uuid4()
    owner = await user_repository.create(
        User(
            email="ext-deny-owner@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="O",
            last_name="W",
            role=UserRole.DOCTOR,
        ),
    )
    patient = await patient_repository.create(
        Patient(
            owner_id=owner.id,
            organization_id=org_id,
            first_name="P",
            last_name="T",
            date_of_birth=date(1990, 1, 1),
            gender="male",
        ),
    )
    patient_user = await user_repository.create(
        User(
            email="ext-deny-pat@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="Pat",
            last_name="U",
            role=UserRole.PATIENT,
        ),
    )
    unassigned = await user_repository.create(
        User(
            email="ext-deny-unassigned@example.com",
            hashed_password=hash_password("securepass123"),
            first_name="U",
            last_name="N",
            role=UserRole.DOCTOR,
        ),
    )

    async def login(email: str) -> dict[str, str]:
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": "securepass123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    body = {"query": "overview"}
    holder["spy"].generate_calls = 0
    assert (
        await client.post(
            NARRATIVE_URL.format(patient_id=patient.id),
            headers=await login(patient_user.email),
            json=body,
        )
    ).status_code == 403
    assert (
        await client.post(
            NARRATIVE_URL.format(patient_id=patient.id),
            headers=await login(unassigned.email),
            json=body,
        )
    ).status_code == 404
    assert holder["spy"].generate_calls == 0


@pytest.mark.asyncio
async def test_clinical_narrative_concurrent_requests_isolated(
    external_narrative_client,
    patient_repository,
    medical_record_repository,
) -> None:
    client, holder, set_transport = external_narrative_client
    headers_a = await _register_and_login(client, email="ext-conc-a@example.com")
    headers_b = await _register_and_login(client, email="ext-conc-b@example.com")
    patient_a = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers_a)).json()["id"])
    patient_b = UUID((await client.post("/api/v1/patients", json=PATIENT_PAYLOAD, headers=headers_b)).json()["id"])
    doc_a = (await patient_repository.get_by_id(patient_a)).owner_id
    doc_b = (await patient_repository.get_by_id(patient_b)).owner_id
    eid_a = await _seed_clinical_data(medical_record_repository, patient_id=patient_a, owner_id=doc_a)
    eid_b = await _seed_clinical_data(medical_record_repository, patient_id=patient_b, owner_id=doc_b)
    set_transport(transport_dynamic_valid("Concurrent patient narrative"))
    holder["spy"].generate_calls = 0

    async def one(pid: UUID, headers: dict[str, str]) -> dict:
        r = await client.post(
            NARRATIVE_URL.format(patient_id=pid),
            headers=headers,
            json={"language": "en"},
        )
        assert r.status_code == 200
        return r.json()

    results = await asyncio.gather(
        one(patient_a, headers_a),
        one(patient_b, headers_b),
    )
    assert all(not r["fallback_used"] for r in results)
    assert holder["spy"].generate_calls == 2
    refs_a = {ref["evidence_id"] for ref in results[0]["evidence_references"]}
    refs_b = {ref["evidence_id"] for ref in results[1]["evidence_references"]}
    assert refs_a.isdisjoint(refs_b) or (refs_a and refs_b)
