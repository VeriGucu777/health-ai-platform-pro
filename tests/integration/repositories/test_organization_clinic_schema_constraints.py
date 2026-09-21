"""PostgreSQL constraint tests for organization clinic skeleton schema."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.organization.entities import Organization, OrganizationMembership, PatientAssignment
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.infrastructure.repositories.organization_membership_repository import (
    SQLAlchemyOrganizationMembershipRepository,
)
from app.infrastructure.repositories.organization_repository import SQLAlchemyOrganizationRepository
from app.infrastructure.repositories.patient_assignment_repository import (
    SQLAlchemyPatientAssignmentRepository,
)
from app.infrastructure.repositories.patient_repository import SQLAlchemyPatientRepository
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from tests.integration.support.factories import make_patient, make_user


async def _create_org(session, name: str = "Test Clinic") -> Organization:
    repo = SQLAlchemyOrganizationRepository(session)
    return await repo.create(Organization(name=name, slug=f"clinic-{uuid.uuid4().hex[:8]}"))


async def test_organization_create_and_slug_unique(db_session):
    repo = SQLAlchemyOrganizationRepository(db_session)
    org = await repo.create(Organization(name="Alpha Clinic", slug="alpha-clinic"))
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await repo.create(Organization(name="Alpha Duplicate", slug="alpha-clinic"))
        await db_session.commit()
    await db_session.rollback()

    loaded = await repo.get_by_id(org.id)
    assert loaded is not None
    assert loaded.name == "Alpha Clinic"


async def test_organization_membership_unique_org_user(db_session):
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    user_repo = SQLAlchemyUserRepository(db_session)
    membership_repo = SQLAlchemyOrganizationMembershipRepository(db_session)

    org = await org_repo.create(Organization(name="Membership Clinic", slug=None))
    user = await user_repo.create(make_user(email="member@example.test"))
    await db_session.commit()

    await membership_repo.create(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            membership_role=OrganizationMembershipRole.DOCTOR,
            status=MembershipStatus.ACTIVE,
        ),
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await membership_repo.create(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
                status=MembershipStatus.INACTIVE,
            ),
        )
        await db_session.commit()
    await db_session.rollback()


async def test_patient_organization_id_nullable(db_session, user_repository, patient_repository):
    owner = await user_repository.create(make_user(email="nullable-org@example.test"))
    await db_session.commit()

    patient = await patient_repository.create(make_patient(owner_id=owner.id))
    await db_session.commit()

    loaded = await patient_repository.get_by_id(patient.id)
    assert loaded is not None
    assert loaded.organization_id is None


async def test_active_assignment_duplicate_patient_assignee_rejected(db_session):
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    user_repo = SQLAlchemyUserRepository(db_session)
    patient_repo = SQLAlchemyPatientRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)

    org = await org_repo.create(Organization(name="Assignment Clinic", slug=None))
    doctor = await user_repo.create(make_user(email="assignee@example.test"))
    owner = await user_repo.create(make_user(email="owner@example.test"))
    patient = await patient_repo.create(
        make_patient(owner_id=owner.id, organization_id=org.id),
    )
    await db_session.commit()

    base = dict(
        organization_id=org.id,
        patient_id=patient.id,
        assignee_user_id=doctor.id,
        status=AssignmentStatus.ACTIVE,
    )
    await assignment_repo.create(PatientAssignment(**base, is_primary=True))
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await assignment_repo.create(PatientAssignment(**base, is_primary=False))
        await db_session.commit()
    await db_session.rollback()


async def test_active_primary_assignment_unique_per_org_patient(db_session):
    org_repo = SQLAlchemyOrganizationRepository(db_session)
    user_repo = SQLAlchemyUserRepository(db_session)
    patient_repo = SQLAlchemyPatientRepository(db_session)
    assignment_repo = SQLAlchemyPatientAssignmentRepository(db_session)

    org = await org_repo.create(Organization(name="Primary Clinic", slug=None))
    doctor_one = await user_repo.create(make_user(email="primary-one@example.test"))
    doctor_two = await user_repo.create(make_user(email="primary-two@example.test"))
    owner = await user_repo.create(make_user(email="primary-owner@example.test"))
    patient = await patient_repo.create(
        make_patient(owner_id=owner.id, organization_id=org.id),
    )
    await db_session.commit()

    await assignment_repo.create(
        PatientAssignment(
            organization_id=org.id,
            patient_id=patient.id,
            assignee_user_id=doctor_one.id,
            is_primary=True,
            status=AssignmentStatus.ACTIVE,
        ),
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await assignment_repo.create(
            PatientAssignment(
                organization_id=org.id,
                patient_id=patient.id,
                assignee_user_id=doctor_two.id,
                is_primary=True,
                status=AssignmentStatus.ACTIVE,
            ),
        )
        await db_session.commit()
    await db_session.rollback()
