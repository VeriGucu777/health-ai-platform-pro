import { describe, expect, it } from "vitest";
import { ApiClientError } from "@/lib/api/client";
import { resolveEncounterMutationErrorMessage } from "@/lib/clinical-encounters/mutation-errors";

const labels = {
  notFoundOrDenied: "not found",
  validation: "validation",
  conflictStale: "conflict",
  terminalEdit: "terminal",
  server: "server",
  accessDenied: "denied",
  generic: "generic",
};

describe("resolveEncounterMutationErrorMessage", () => {
  it("masks 404", () => {
    expect(resolveEncounterMutationErrorMessage(new ApiClientError("x", 404, { detail: "secret" }), labels)).toBe(
      "not found",
    );
  });

  it("maps 409 to conflict copy", () => {
    expect(resolveEncounterMutationErrorMessage(new ApiClientError("x", 409), labels)).toBe("conflict");
  });

  it("maps 422 to validation copy", () => {
    expect(resolveEncounterMutationErrorMessage(new ApiClientError("x", 422), labels)).toBe("validation");
  });

  it("does not expose raw backend detail", () => {
    const message = resolveEncounterMutationErrorMessage(
      new ApiClientError("x", 422, { detail: "raw backend validation" }),
      labels,
    );
    expect(message).toBe("validation");
    expect(message).not.toContain("raw backend");
  });
});
