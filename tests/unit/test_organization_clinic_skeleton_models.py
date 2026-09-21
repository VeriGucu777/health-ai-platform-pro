"""Unit tests for organization clinic skeleton imports and patient org column."""

import inspect

from app.domain.interfaces.patient_access_policy import PatientAccessPolicy
from app.domain.patient_access.result import PatientAccessDecision
from app.domain.organization.entities import Organization, OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.database.models import (
    OrganizationMembershipModel,
    OrganizationModel,
    PatientAssignmentModel,
    PatientModel,
)
from app.domain.entities.patient import Patient


def test_orm_models_import_for_alembic_discovery() -> None:
    assert OrganizationModel.__tablename__ == "organizations"
    assert OrganizationMembershipModel.__tablename__ == "organization_memberships"
    assert PatientAssignmentModel.__tablename__ == "patient_assignments"
    assert "organization_id" in PatientModel.__table__.columns
    assert PatientModel.__table__.columns["organization_id"].nullable is True


def test_patient_entity_organization_id_optional() -> None:
    from uuid import uuid4

    patient = Patient(
        owner_id=uuid4(),
        first_name="A",
        last_name="B",
        date_of_birth=__import__("datetime").date(1990, 1, 1),
        gender="male",
    )
    assert patient.organization_id is None


def test_patient_access_policy_is_abstract_contract() -> None:
    assert inspect.isabstract(PatientAccessPolicy)
    assert "resolve_access" in PatientAccessPolicy.__abstractmethods__
    assert "resolve_create_access" in PatientAccessPolicy.__abstractmethods__
    from app.domain.patient_access.reason_codes import PatientAccessReasonCode

    decision = PatientAccessDecision(
        allowed=True,
        reason_code=PatientAccessReasonCode.ALLOWED_CLINIC_ADMIN,
    )
    assert decision.allowed is True
