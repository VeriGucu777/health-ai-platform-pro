import { apiClient } from "@/lib/api/index";

export type ClinicAdminMembership = {
  membership_id: string;
  organization_id: string;
  membership_role: "doctor" | "clinic_admin";
  joined_at: string;
};

export type OrganizationDoctorMember = {
  membership_id: string;
  user_id: string;
  joined_at: string;
};

export type OrganizationDoctorMemberListResponse = {
  items: OrganizationDoctorMember[];
};

export async function fetchMyOrganizationMembership(
  authToken: string,
): Promise<ClinicAdminMembership> {
  return apiClient.get<ClinicAdminMembership>("/organizations/me/membership", { authToken });
}

export async function fetchOrganizationDoctors(
  authToken: string,
): Promise<OrganizationDoctorMemberListResponse> {
  return apiClient.get<OrganizationDoctorMemberListResponse>(
    "/organizations/me/members/doctors",
    { authToken },
  );
}
