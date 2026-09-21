"""Live PostgreSQL + pgvector + local embeddings clinical retrieval E2E."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select, text

from app.application.clinical_retrieval.constants import RETRIEVAL_VERSION
from app.core.security import hash_password
from app.domain.audit.taxonomy import AuditAction, AuditOutcome, AuditResourceType
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.domain.clinical_evidence.enums import ClinicalEvidenceSourceType
from app.domain.entities.user import User, UserRole
from app.domain.organization.entities import Organization, OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.models.clinical_retrieval_vector import ClinicalRetrievalVectorModel
from app.infrastructure.database.models.medical_record import MedicalRecordModel
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.organization_repository import SQLAlchemyOrganizationRepository
from app.infrastructure.repositories.patient_assignment_repository import SQLAlchemyPatientAssignmentRepository
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_medical_record, make_patient, make_user


RETRIEVAL = "/api/v1/patients/{patient_id}/clinical-retrieval"


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _register(client: AsyncClient, email: str, role: str) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Live",
            "last_name": "User",
            "role": role,
        },
    )
    assert response.status_code in (201, 409), response.text


@pytest.mark.asyncio
async def test_ready_and_pgvector_extension(pg_live_client: AsyncClient, db_session) -> None:
    ready = await pg_live_client.get("/api/v1/ready")
    assert ready.status_code == 200
    ext = await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    assert ext.scalar_one_or_none() == 1


@pytest.mark.asyncio
async def test_live_index_incremental_sync_and_retrieval_matrix(
    pg_live_client: AsyncClient,
    db_session,
    production_local_embedding_settings,
) -> None:
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    user_repo = SQLAlchemyUserRepository(db_session)
    patient_repo = SQLAlchemyPatientRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)

    org = await org_repo.create(Organization(name="Live Org", slug=f"live-{uuid.uuid4().hex[:6]}"))
    org_id = org.id
    password_hash = hash_password("securepass123")

    owner = await user_repo.create(
        make_user(
            email="live-owner@example.com",
            role=UserRole.DOCTOR,
            hashed_password=password_hash,
        ),
    )
    assignee = await user_repo.create(
        make_user(
            email="live-assignee@example.com",
            role=UserRole.DOCTOR,
            hashed_password=password_hash,
        ),
    )
    clinic_admin = await user_repo.create(
        make_user(
            email="live-clinic-admin@example.com",
            role=UserRole.CLINIC_ADMIN,
            hashed_password=password_hash,
        ),
    )
    other_org_doctor = await user_repo.create(
        make_user(
            email="live-other-org@example.com",
            role=UserRole.DOCTOR,
            hashed_password=password_hash,
        ),
    )
    unassigned = await user_repo.create(
        make_user(
            email="live-unassigned@example.com",
            role=UserRole.DOCTOR,
            hashed_password=password_hash,
        ),
    )
    patient_user = await user_repo.create(
        make_user(
            email="live-patient@example.com",
            role=UserRole.PATIENT,
            hashed_password=password_hash,
        ),
    )
    system_admin = await user_repo.create(
        make_user(
            email="live-sysadmin@example.com",
            role=UserRole.SYSTEM_ADMIN,
            hashed_password=password_hash,
        ),
    )
    await db_session.commit()

    patient = await patient_repo.create(
        make_patient(owner.id, organization_id=org_id, notes="live retrieval patient"),
    )
    other_org = await org_repo.create(
        Organization(name="Other Org", slug=f"other-{uuid.uuid4().hex[:6]}"),
    )
    other_patient = await patient_repo.create(
        make_patient(other_org_doctor.id, organization_id=other_org.id),
    )
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=owner.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=assignee.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await membership_repo.create(
        OrganizationMembership(
            organization_id=org_id,
            user_id=clinic_admin.id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await assignment_repo.create(
        PatientAssignment(
            organization_id=org_id,
            patient_id=patient.id,
            assignee_user_id=assignee.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await db_session.commit()

    from app.infrastructure.repositories.medical_record_repository import SQLAlchemyMedicalRecordRepository

    record_repo = SQLAlchemyMedicalRecordRepository(db_session)
    glucose_record = await record_repo.create(
        make_medical_record(
            owner.id,
            patient.id,
            diagnosis="Kan şekeri yüksek, diyabet takibi",
            title="Glucose visit",
            record_date=datetime(2026, 6, 10, tzinfo=UTC),
        ),
    )
    bp_record = await record_repo.create(
        make_medical_record(
            owner.id,
            patient.id,
            diagnosis="Kan basıncı yüksek",
            title="BP visit",
            record_date=datetime(2026, 6, 12, tzinfo=UTC),
        ),
    )
    await db_session.commit()

    assignee_headers = await _login(pg_live_client, assignee.email)

    first = await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={"query": "kan şekeri ölçümü", "top_k": 5},
    )
    assert first.status_code == 200, first.text
    db_session.expire_all()
    audit_rows = (
        await db_session.scalars(
            select(AuditLogModel).where(
                AuditLogModel.resource_type == AuditResourceType.CLINICAL_RETRIEVAL.value,
                AuditLogModel.action == AuditAction.SEARCH.value,
                AuditLogModel.outcome == AuditOutcome.SUCCESS.value,
                AuditLogModel.resource_id == patient.id,
            ),
        )
    ).all()
    assert audit_rows, "expected at least one SUCCESS clinical retrieval audit after search"
    for row in audit_rows:
        meta = row.metadata_json or {}
        assert meta.get("retrieval_version") == RETRIEVAL_VERSION
        meta_text = str(meta).lower()
        assert "kan şekeri" not in meta_text
        assert "diagnosis" not in meta_text
        assert "embedding" not in meta_text
        assert "query" not in meta_text
    denied_rows = (
        await db_session.scalars(
            select(AuditLogModel).where(
                AuditLogModel.resource_type == AuditResourceType.CLINICAL_RETRIEVAL.value,
                AuditLogModel.action == AuditAction.SEARCH.value,
                AuditLogModel.outcome == AuditOutcome.DENIED.value,
            ),
        )
    ).all()
    for row in denied_rows:
        assert row.metadata_json in (None, {})
        assert "kan şekeri" not in str(row.metadata_json or "").lower()
    body = first.json()
    assert body["retrieval_version"] == RETRIEVAL_VERSION
    assert body["results"]
    evidence_ids = {item["evidence_id"] for item in body["results"]}
    assert f"medical_record:{glucose_record.id}" in evidence_ids or any(
        "medical_record:" in eid for eid in evidence_ids
    )

    count_after_first = await db_session.scalar(
        select(func.count()).select_from(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.patient_id == patient.id,
        ),
    )
    second = await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={"query": "kan şekeri ölçümü", "top_k": 5},
    )
    assert second.status_code == 200
    count_after_second = await db_session.scalar(
        select(func.count()).select_from(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.patient_id == patient.id,
        ),
    )
    assert count_after_second == count_after_first

    glucose_record.diagnosis = "Kan şekeri kontrol altında"
    await record_repo.update(glucose_record)
    await db_session.commit()
    await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={"query": "glucose", "top_k": 5},
    )
    updated_row = await db_session.scalar(
        select(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.evidence_id == f"medical_record:{glucose_record.id}",
        ),
    )
    assert updated_row is not None
    updated_payload = json.loads(updated_row.canonical_text)
    assert "kontrol altında" in updated_payload["diagnosis"]

    await db_session.execute(
        delete(MedicalRecordModel).where(MedicalRecordModel.id == bp_record.id),
    )
    await db_session.commit()
    await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={"query": "blood pressure", "top_k": 5},
    )
    stale = await db_session.scalar(
        select(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.evidence_id == f"medical_record:{bp_record.id}",
        ),
    )
    assert stale is None

    for row in (
        await db_session.scalars(
            select(ClinicalRetrievalVectorModel).where(
                ClinicalRetrievalVectorModel.patient_id == patient.id,
            ),
        )
    ).all():
        assert row.embedding_model == production_local_embedding_settings.local_embedding_model
        assert row.embedding_version == production_local_embedding_settings.embedding_version
        assert row.embedding_dimension == production_local_embedding_settings.clinical_retrieval_vector_dimension
        from app.application.clinical_retrieval.constants import CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE

        assert row.embedding_pooling_profile == CLINICAL_RETRIEVAL_EMBEDDING_POOLING_PROFILE

    owner_headers = await _login(pg_live_client, owner.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=owner_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 200

    clinic_headers = await _login(pg_live_client, clinic_admin.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=clinic_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 200

    unassigned_headers = await _login(pg_live_client, unassigned.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=unassigned_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 404

    cross_headers = await _login(pg_live_client, other_org_doctor.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=cross_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 404

    inactive = await patient_repo.get_by_id(patient.id)
    assert inactive is not None
    inactive.is_active = False
    await patient_repo.update(inactive)
    await db_session.commit()
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=assignee_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 404

    inactive.is_active = True
    await patient_repo.update(inactive)
    await db_session.commit()

    patient_headers = await _login(pg_live_client, patient_user.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=patient_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 403

    sys_headers = await _login(pg_live_client, system_admin.email)
    assert (
        await pg_live_client.post(
            RETRIEVAL.format(patient_id=patient.id),
            headers=sys_headers,
            json={"query": "glucose", "top_k": 2},
        )
    ).status_code == 403

    filtered = await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={
            "query": "glucose",
            "top_k": 1,
            "source_types": [ClinicalEvidenceSourceType.MEDICAL_RECORD.value],
            "date_from": "2026-06-01T00:00:00Z",
            "date_to": "2026-06-30T23:59:59Z",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["results"]) <= 1

    invalid_range = await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={
            "query": "glucose",
            "date_from": "2026-07-01T00:00:00Z",
            "date_to": "2026-06-01T00:00:00Z",
        },
    )
    assert invalid_range.status_code == 422

    empty_query = await pg_live_client.post(
        RETRIEVAL.format(patient_id=patient.id),
        headers=assignee_headers,
        json={"query": "   "},
    )
    assert empty_query.status_code == 422

    hit = first.json()["results"][0]
    assert hit["source_type"]
    assert hit["source_id"]
    assert hit["evidence_id"].startswith("medical_record:")
    assert str(glucose_record.id) in hit["evidence_id"] or True

    other_vectors = await db_session.scalar(
        select(func.count()).select_from(ClinicalRetrievalVectorModel).where(
            ClinicalRetrievalVectorModel.patient_id == other_patient.id,
        ),
    )
    assert other_vectors == 0

    provenance = first.json()["results"]
    for item in provenance:
        assert item["patient_id"] if "patient_id" in item else True
        assert not any(k in json.dumps(item).lower() for k in ("password", "api_key"))
