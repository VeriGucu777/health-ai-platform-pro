import { describe, expect, it } from "vitest";
import {
  isComplaintInputValid,
  parseOptionalFiniteNumber,
} from "@/lib/clinical-encounters/validation";

describe("clinical encounter validation helpers", () => {
  it("requires complaint key or display text", () => {
    expect(isComplaintInputValid("", "")).toBe(false);
    expect(isComplaintInputValid("chest_pain", "")).toBe(true);
    expect(isComplaintInputValid("", "Pain")).toBe(true);
  });

  it("rejects non-finite numeric input", () => {
    expect(parseOptionalFiniteNumber("")).toBe(null);
    expect(parseOptionalFiniteNumber("12.5")).toBe(12.5);
    expect(parseOptionalFiniteNumber("NaN")).toBe(null);
    expect(parseOptionalFiniteNumber("Infinity")).toBe(null);
  });
});
