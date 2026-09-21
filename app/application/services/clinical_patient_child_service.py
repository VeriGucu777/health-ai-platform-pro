"""Base helpers for clinical child resources scoped by patient access policy."""

from typing import TypeVar
from uuid import UUID

from app.application.services.base import BaseService
from app.application.services.patient_child_access import (
    list_accessible_patient_ids,
    resolve_patient_access_for_action,
)
from app.application.services.patient_access_types import ResolvedPatientRead
from app.core.exceptions import NotFoundError
from app.domain.entities.user import UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.interfaces.repository import Repository

TChild = TypeVar("TChild")


class ClinicalPatientChildService(BaseService):
    """Shared patient-policy checks for appointment/measurement/record services."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        access_policy: PatientAccessPolicy | None = None,
        membership_repository: OrganizationMembershipRepository | None = None,
    ) -> None:
        self._patients = patient_repository
        self._access_policy = access_policy
        self._memberships = membership_repository

    async def _require_patient_access(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        action: PatientAccessAction,
    ) -> ResolvedPatientRead:
        return await resolve_patient_access_for_action(
            patients=self._patients,
            access_policy=self._access_policy,
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            action=action,
        )

    async def read_organization_id_for_patient(
        self,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
    ) -> UUID | None:
        """Return organization_id after READ policy (for audit on successful reads)."""
        ctx = await self._require_patient_access(
            actor_id,
            actor_role,
            patient_id,
            PatientAccessAction.READ,
        )
        return ctx.organization_id

    async def _accessible_patient_ids(
        self,
        actor_id: UUID,
        actor_role: UserRole,
    ) -> list[UUID]:
        return await list_accessible_patient_ids(
            patients=self._patients,
            memberships=self._memberships,
            actor_id=actor_id,
            actor_role=actor_role,
        )

    async def _get_child_with_patient_access(
        self,
        repository: Repository[TChild],
        child_id: UUID,
        *,
        actor_id: UUID,
        actor_role: UserRole,
        action: PatientAccessAction,
        not_found_message: str,
        patient_id_getter,
    ) -> tuple[TChild, ResolvedPatientRead]:
        child = await repository.get_by_id(child_id)
        if child is None:
            raise NotFoundError(not_found_message)
        patient_id = patient_id_getter(child)
        ctx = await self._require_patient_access(actor_id, actor_role, patient_id, action)
        return child, ctx
