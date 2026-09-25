"""Default patient access policy — organization, assignment, and legacy owner rules."""

from uuid import UUID

from app.domain.entities.user import UserRole
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_access_policy import PatientAccessAction, PatientAccessPolicy
from app.domain.interfaces.patient_assignment_repository import PatientAssignmentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.organization.enums import AssignmentStatus, MembershipStatus, OrganizationMembershipRole
from app.domain.patient_access.reason_codes import PatientAccessReasonCode
from app.domain.patient_access.result import PatientAccessDecision


class DefaultPatientAccessPolicy(PatientAccessPolicy):
    """Evaluates clinical patient access without performing HTTP mapping."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        membership_repository: OrganizationMembershipRepository,
        assignment_repository: PatientAssignmentRepository,
    ) -> None:
        self._patients = patient_repository
        self._memberships = membership_repository
        self._assignments = assignment_repository

    async def resolve_access(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        action: PatientAccessAction,
    ) -> PatientAccessDecision:
        if action not in (
            PatientAccessAction.READ,
            PatientAccessAction.WRITE,
            PatientAccessAction.DELETE,
        ):
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

        patient = await self._patients.get_by_id(patient_id)
        if patient is None or not patient.is_active:
            return self._deny(
                PatientAccessReasonCode.DENIED_NOT_FOUND,
                suggested_http_status=404,
            )

        if actor_role == UserRole.SYSTEM_ADMIN:
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

        if actor_role == UserRole.PATIENT:
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

        if patient.organization_id is None:
            return self._resolve_legacy_unscoped_patient(
                actor_id=actor_id,
                actor_role=actor_role,
                owner_id=patient.owner_id,
            )

        return await self._resolve_org_scoped_patient(
            actor_id=actor_id,
            actor_role=actor_role,
            patient_id=patient_id,
            organization_id=patient.organization_id,
            owner_id=patient.owner_id,
        )

    async def _resolve_org_scoped_patient(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
        patient_id: UUID,
        organization_id: UUID,
        owner_id: UUID,
    ) -> PatientAccessDecision:
        membership = await self._memberships.get_by_organization_and_user(
            organization_id,
            actor_id,
        )
        if membership is None:
            return self._deny(
                PatientAccessReasonCode.DENIED_CROSS_ORG,
                organization_id=organization_id,
                suggested_http_status=404,
            )
        if membership.status != MembershipStatus.ACTIVE:
            return self._deny(
                PatientAccessReasonCode.DENIED_INACTIVE_MEMBERSHIP,
                organization_id=organization_id,
                suggested_http_status=403,
            )

        if actor_role == UserRole.CLINIC_ADMIN:
            return self._allow(
                PatientAccessReasonCode.ALLOWED_CLINIC_ADMIN,
                organization_id=organization_id,
            )

        if actor_role == UserRole.DOCTOR:
            assignment = await self._assignments.get_by_patient_and_assignee(
                patient_id,
                actor_id,
            )
            if assignment is None:
                return self._deny(
                    PatientAccessReasonCode.DENIED_UNASSIGNED,
                    organization_id=organization_id,
                    suggested_http_status=404,
                )
            if not self._is_active_assignment(assignment):
                reason = (
                    PatientAccessReasonCode.DENIED_INACTIVE_ASSIGNMENT
                    if assignment.status != AssignmentStatus.ACTIVE
                    or assignment.ended_at is not None
                    else PatientAccessReasonCode.DENIED_UNASSIGNED
                )
                return self._deny(
                    reason,
                    organization_id=organization_id,
                    suggested_http_status=404,
                )
            if assignment.organization_id != organization_id:
                return self._deny(
                    PatientAccessReasonCode.DENIED_CROSS_ORG,
                    organization_id=organization_id,
                    suggested_http_status=404,
                )
            return self._allow(
                PatientAccessReasonCode.ALLOWED_ASSIGNMENT,
                organization_id=organization_id,
            )

        return self._deny(
            PatientAccessReasonCode.DENIED_ROLE,
            organization_id=organization_id,
            suggested_http_status=403,
        )

    async def resolve_create_access(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
    ) -> PatientAccessDecision:
        if actor_role in (UserRole.SYSTEM_ADMIN, UserRole.PATIENT):
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

        if actor_role == UserRole.CLINIC_ADMIN:
            return await self._resolve_create_for_clinic_admin(actor_id)

        if actor_role == UserRole.DOCTOR:
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

        return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)

    async def _resolve_create_for_clinic_admin(self, actor_id: UUID) -> PatientAccessDecision:
        memberships = await self._memberships.list_active_memberships_for_user(
            actor_id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
        )
        if not memberships:
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)
        if len(memberships) > 1:
            return self._deny(PatientAccessReasonCode.DENIED_ROLE, suggested_http_status=403)
        org_id = memberships[0].organization_id
        return self._allow(
            PatientAccessReasonCode.ALLOWED_CLINIC_ADMIN,
            organization_id=org_id,
        )

    def _resolve_legacy_unscoped_patient(
        self,
        *,
        actor_id: UUID,
        actor_role: UserRole,
        owner_id: UUID,
    ) -> PatientAccessDecision:
        if actor_role == UserRole.DOCTOR and owner_id == actor_id:
            return self._allow(PatientAccessReasonCode.ALLOWED_LEGACY_OWNER, organization_id=None)
        return self._deny(
            PatientAccessReasonCode.DENIED_UNASSIGNED,
            organization_id=None,
            suggested_http_status=404,
        )

    @staticmethod
    def _is_active_assignment(assignment) -> bool:
        return assignment.status == AssignmentStatus.ACTIVE and assignment.ended_at is None

    @staticmethod
    def _allow(
        reason_code: PatientAccessReasonCode,
        *,
        organization_id: UUID | None,
    ) -> PatientAccessDecision:
        return PatientAccessDecision(
            allowed=True,
            reason_code=reason_code,
            organization_id=organization_id,
            suggested_http_status=200,
        )

    @staticmethod
    def _deny(
        reason_code: PatientAccessReasonCode,
        *,
        organization_id: UUID | None = None,
        suggested_http_status: int | None = None,
    ) -> PatientAccessDecision:
        return PatientAccessDecision(
            allowed=False,
            reason_code=reason_code,
            organization_id=organization_id,
            suggested_http_status=suggested_http_status,
        )
