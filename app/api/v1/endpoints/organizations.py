"""Clinic admin organization membership endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import ClinicAdminUser, get_clinic_admin_organization_service
from app.api.schemas.clinic_admin_organization import (
    ClinicAdminMembershipResponse,
    OrganizationDoctorMemberListResponse,
    OrganizationDoctorMemberResponse,
)
from app.application.dtos.clinic_admin_organization import (
    ClinicAdminMembershipDTO,
    OrganizationDoctorMemberListDTO,
)
from app.application.services.clinic_admin_organization_service import (
    ClinicAdminOrganizationService,
)

router = APIRouter()


def _membership_response(data: ClinicAdminMembershipDTO) -> ClinicAdminMembershipResponse:
    return ClinicAdminMembershipResponse.model_validate(data.model_dump())


def _doctor_list_response(
    data: OrganizationDoctorMemberListDTO,
) -> OrganizationDoctorMemberListResponse:
    return OrganizationDoctorMemberListResponse(
        items=[OrganizationDoctorMemberResponse.model_validate(item.model_dump()) for item in data.items],
    )


@router.get(
    "/me/membership",
    response_model=ClinicAdminMembershipResponse,
    summary="Get current clinic admin organization membership",
)
async def get_my_clinic_admin_membership(
    current_user: ClinicAdminUser,
    service: Annotated[ClinicAdminOrganizationService, Depends(get_clinic_admin_organization_service)],
) -> ClinicAdminMembershipResponse:
    """Return the authenticated clinic admin's active organization membership."""
    membership = await service.get_my_clinic_admin_membership(current_user.id)
    return _membership_response(membership)


@router.get(
    "/me/members/doctors",
    response_model=OrganizationDoctorMemberListResponse,
    summary="List active doctors in the clinic admin organization",
)
async def list_organization_doctors(
    current_user: ClinicAdminUser,
    service: Annotated[ClinicAdminOrganizationService, Depends(get_clinic_admin_organization_service)],
) -> OrganizationDoctorMemberListResponse:
    """List active doctor memberships in the clinic admin's organization."""
    doctors = await service.list_organization_doctors(current_user.id)
    return _doctor_list_response(doctors)
