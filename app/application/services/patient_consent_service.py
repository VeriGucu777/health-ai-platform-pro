"""Clinic admin patient consent management."""

from datetime import UTC, datetime
from uuid import UUID

from app.application.dtos.patient_consent import PatientConsentDTO, PatientConsentListDTO
from app.application.services.base import BaseService
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.domain.consent.entities import PatientConsent
from app.domain.consent.enums import ConsentSource, ConsentStatus, ConsentType
from app.domain.interfaces.organization_membership_repository import OrganizationMembershipRepository
from app.domain.interfaces.patient_consent_repository import PatientConsentRepository
from app.domain.interfaces.patient_repository import PatientRepository
from app.domain.organization.enums import MembershipStatus, OrganizationMembershipRole


class PatientConsentService(BaseService):
    """Grant and revoke patient consents within a clinic admin organization."""

    def __init__(
        self,
        membership_repository: OrganizationMembershipRepository,
        consent_repository: PatientConsentRepository,
        patient_repository: PatientRepository,
    ) -> None:
        self._memberships = membership_repository
        self._consents = consent_repository
        self._patients = patient_repository

    async def list_patient_consents(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
    ) -> PatientConsentListDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)
        rows = await self._consents.list_by_patient_and_organization(patient_id, organization_id)
        return PatientConsentListDTO(
            organization_id=organization_id,
            items=[_consent_dto(row) for row in rows],
        )

    async def grant_patient_consent(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
        *,
        consent_type: ConsentType,
    ) -> PatientConsentDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)

        active = await self._consents.get_active_granted(
            patient_id,
            organization_id,
            consent_type,
        )
        if active is not None:
            raise ConflictError("An active consent already exists for this patient and consent type")

        next_version = await self._consents.get_max_version(
            patient_id,
            organization_id,
            consent_type,
        ) + 1
        now = datetime.now(UTC)
        consent = PatientConsent(
            patient_id=patient_id,
            organization_id=organization_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            granted_at=now,
            recorded_by_user_id=admin_user_id,
            version=next_version,
            source=ConsentSource.MANUAL,
            created_at=now,
        )
        created = await self._consents.create(consent)
        return _consent_dto(created)

    async def revoke_patient_consent(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
        consent_id: UUID,
    ) -> PatientConsentDTO:
        organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        await self._require_patient_in_organization(patient_id, organization_id)

        consent = await self._consents.get_by_id(consent_id)
        if (
            consent is None
            or consent.patient_id != patient_id
            or consent.organization_id != organization_id
        ):
            raise NotFoundError("Consent not found")
        if consent.status != ConsentStatus.GRANTED:
            raise ValidationError("Only an active granted consent can be revoked")

        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(UTC)
        updated = await self._consents.update(consent)
        return _consent_dto(updated)

    async def _require_single_active_clinic_admin_org(self, admin_user_id: UUID) -> UUID:
        memberships = await self._memberships.list_active_memberships_for_user(
            admin_user_id,
            membership_role=OrganizationMembershipRole.CLINIC_ADMIN,
        )
        if not memberships:
            raise ForbiddenError("Insufficient permissions")
        if len(memberships) > 1:
            raise ForbiddenError("Multiple active clinic admin organizations are not supported")
        return memberships[0].organization_id

    async def _require_patient_in_organization(
        self,
        patient_id: UUID,
        organization_id: UUID,
    ) -> None:
        patient = await self._patients.get_by_id(patient_id)
        if (
            patient is None
            or not patient.is_active
            or patient.organization_id != organization_id
        ):
            raise NotFoundError("Patient not found")

    async def resolve_audit_organization_id(
        self,
        admin_user_id: UUID,
        patient_id: UUID,
    ) -> UUID | None:
        """Return organization_id for audit when patient is in the admin's org (no extra lookup leak)."""
        try:
            organization_id = await self._require_single_active_clinic_admin_org(admin_user_id)
        except ForbiddenError:
            return None
        patient = await self._patients.get_by_id(patient_id)
        if (
            patient is None
            or not patient.is_active
            or patient.organization_id != organization_id
        ):
            return None
        return organization_id


def _consent_dto(consent: PatientConsent) -> PatientConsentDTO:
    return PatientConsentDTO.model_validate(consent.__dict__)
