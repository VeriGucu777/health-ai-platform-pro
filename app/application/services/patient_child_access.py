"""Patient access resolution for clinical child resources."""

from uuid import UUID

from app.application.services.patient_access_errors import raise_for_patient_access_decision
from app.application.services.patient_access_types import ResolvedPatientRead
from app.core.exceptions import NotFoundError
from app.domain.entities.user import UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository

_ACCESSIBLE_PATIENTS_CAP = 10_000


async def resolve_patient_access_for_action(
    *,
    patients: PatientRepository,
    access_policy: PatientAccessPolicy | None,
    actor_id: UUID,
    actor_role: UserRole,
    patient_id: UUID,
    action: PatientAccessAction,
) -> ResolvedPatientRead:
    """Enforce patient policy for the given action (read/write/delete)."""
    if access_policy is None:
        patient = await patients.get_by_id_and_owner(patient_id, actor_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        return ResolvedPatientRead(patient=patient, organization_id=None)

    decision = await access_policy.resolve_access(
        actor_id=actor_id,
        actor_role=actor_role,
        patient_id=patient_id,
        action=action,
    )
    raise_for_patient_access_decision(decision)

    patient = await patients.get_by_id(patient_id)
    if patient is None or not patient.is_active:
        raise NotFoundError("Patient not found")

    return ResolvedPatientRead(
        patient=patient,
        organization_id=decision.organization_id,
    )


async def list_accessible_patient_ids(
    *,
    patients: PatientRepository,
    memberships: OrganizationMembershipRepository | None,
    actor_id: UUID,
    actor_role: UserRole,
) -> list[UUID]:
    """Patient IDs the actor may access for child-resource listing."""
    if actor_role == UserRole.DOCTOR:
        visible = await patients.list_visible_to_doctor(
            actor_id,
            offset=0,
            limit=_ACCESSIBLE_PATIENTS_CAP,
        )
        return [patient.id for patient in visible]

    if actor_role == UserRole.CLINIC_ADMIN:
        if memberships is None:
            return []
        org_ids = await memberships.list_active_organization_ids_for_user(actor_id)
        if not org_ids:
            return []
        org_patients = await patients.list_by_organization_ids(
            org_ids,
            offset=0,
            limit=_ACCESSIBLE_PATIENTS_CAP,
        )
        return [patient.id for patient in org_patients]

    return []
