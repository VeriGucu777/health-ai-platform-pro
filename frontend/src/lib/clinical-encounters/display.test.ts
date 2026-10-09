import { describe, expect, it } from "vitest";
import { formatEncounterStatusLabel } from "@/lib/clinical-encounters/display";

describe("formatEncounterStatusLabel", () => {
  it("returns translated label when available", () => {
    expect(formatEncounterStatusLabel("active", { active: "Devam ediyor" })).toBe("Devam ediyor");
  });
});
