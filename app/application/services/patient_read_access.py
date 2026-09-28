"""Resolve patient read access via PatientAccessPolicy."""

from uuid import UUID

from app.application.services.patient_access_types import ResolvedPatientRead
from app.application.services.patient_child_access import resolve_patient_access_for_action
from app.core.config import Settings
from app.domain.entities.user import UserRole
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository


async def resolve_patient_read_access(
    *,
    patients: PatientRepository,
    access_policy: PatientAccessPolicy | None,
    actor_id: UUID,
    actor_role: UserRole,
    patient_id: UUID,
    settings: Settings | None = None,
    consent_repository: PatientConsentRepository | None = None,
) -> ResolvedPatientRead:
    """Enforce READ policy and return the patient row for clinical read/export flows."""
    return await resolve_patient_access_for_action(
        patients=patients,
        access_policy=access_policy,
        actor_id=actor_id,
        actor_role=actor_role,
        patient_id=patient_id,
        action=PatientAccessAction.READ,
        settings=settings,
        consent_repository=consent_repository,
        apply_clinical_consent=True,
    )
