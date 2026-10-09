import { describe, expect, it } from "vitest";
import { ApiClientError } from "@/lib/api/client";
import { resolveEncounterClientErrorMessage } from "@/lib/clinical-encounters/error-messages";

const labels = {
  notFoundOrDenied: "Safe not found",
  activeConflict: "Safe conflict",
  generic: "Safe generic",
  accessDenied: "Safe denied",
};

describe("resolveEncounterClientErrorMessage", () => {
  it("never returns raw backend message", () => {
    const message = resolveEncounterClientErrorMessage(
      new ApiClientError("Internal secret detail", 500, { message: "Internal secret detail" }),
      labels,
    );
    expect(message).toBe("Safe generic");
    expect(message).not.toContain("secret");
  });

  it("maps 404 to safe masking copy", () => {
    expect(
      resolveEncounterClientErrorMessage(new ApiClientError("x", 404, { message: "Patient not found" }), labels),
    ).toBe("Safe not found");
  });
});
