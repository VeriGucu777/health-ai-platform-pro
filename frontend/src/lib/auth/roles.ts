import type { UserRole } from "@/lib/api/auth";

export function isClinicAdminRole(role: UserRole | null | undefined): boolean {
  return role === "clinic_admin";
}

export function canAccessManagementUi(role: UserRole | null | undefined): boolean {
  return isClinicAdminRole(role);
}
