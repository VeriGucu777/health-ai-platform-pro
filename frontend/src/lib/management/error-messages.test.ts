import { describe, expect, it } from "vitest";
import { ApiClientError } from "@/lib/api/client";
import { resolveManagementErrorMessage } from "@/lib/management/error-messages";
import { commonContent as en } from "@/content/en/common";

const messages = en.management.errors;

describe("resolveManagementErrorMessage", () => {
  it("maps 409 duplicate assignment", () => {
    const error = new ApiClientError(
      "An active assignment already exists for this doctor and patient",
      409,
    );
    expect(resolveManagementErrorMessage(error, messages).message).toBe(
      messages.duplicateAssignment,
    );
  });

  it("maps 404 patient not found for cross-org", () => {
    const error = new ApiClientError("Patient not found", 404);
    expect(resolveManagementErrorMessage(error, messages).message).toBe(messages.patientNotFound);
    expect(resolveManagementErrorMessage(error, messages).status).toBe(404);
  });

  it("maps 409 duplicate consent", () => {
    const error = new ApiClientError(
      "An active consent already exists for this patient and consent type",
      409,
    );
    expect(resolveManagementErrorMessage(error, messages).message).toBe(messages.duplicateConsent);
  });
});
