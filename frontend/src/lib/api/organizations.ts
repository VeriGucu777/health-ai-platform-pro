import { apiClient } from "@/lib/api/index";

export type ClinicAdminMembership = {
  membership_id: string;
  organization_id: string;
  organization_name: string;
  membership_role: "doctor" | "clinic_admin";
  membership_status: "active" | "inactive";
  joined_at: string;
};

export type OrganizationDoctorMember = {
  membership_id: string;
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
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
