import { describe, expect, it } from "vitest";
import { canAccessManagementUi, isClinicAdminRole } from "@/lib/auth/roles";

describe("management role visibility", () => {
  it("allows clinic_admin only", () => {
    expect(isClinicAdminRole("clinic_admin")).toBe(true);
    expect(canAccessManagementUi("clinic_admin")).toBe(true);
  });

  it("denies doctor, patient, and system_admin", () => {
    for (const role of ["doctor", "patient", "system_admin"] as const) {
      expect(isClinicAdminRole(role)).toBe(false);
      expect(canAccessManagementUi(role)).toBe(false);
    }
  });
});
