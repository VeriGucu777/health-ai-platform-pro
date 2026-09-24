import { describe, expect, it } from "vitest";
import { buildGenderOptions, isPatientGenderValue } from "@/lib/management/patient-gender";

describe("patient gender helpers", () => {
  it("maps localized labels to canonical API values", () => {
    const options = buildGenderOptions({
      female: "Kadın",
      male: "Erkek",
      other: "Diğer",
    });

    expect(options).toEqual([
      { value: "female", label: "Kadın" },
      { value: "male", label: "Erkek" },
      { value: "other", label: "Diğer" },
    ]);
    expect(isPatientGenderValue("female")).toBe(true);
    expect(isPatientGenderValue("Kadın")).toBe(false);
  });
});
