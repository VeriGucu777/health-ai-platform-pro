import { describe, expect, it } from "vitest";
import { formatPatientListLabel } from "@/lib/management/doctor-display";

describe("formatPatientListLabel", () => {
  it("includes formatted date of birth as secondary label", () => {
    const label = formatPatientListLabel(
      { first_name: "Demo", last_name: "Pilot Patient", date_of_birth: "1992-04-15" },
      (value) => `DOB:${value}`,
    );
    expect(label).toBe("Demo Pilot Patient (DOB:1992-04-15)");
  });
});
