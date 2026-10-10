import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EncounterDetailWriteWorkspace } from "@/components/patients/EncounterDetailWriteWorkspace";
import { makeEncounterWorkspaceTestLabels } from "@/components/patients/encounter-test-labels";

const addEncounterComplaint = vi.fn();
const addEncounterFinding = vi.fn();
const upsertEncounterQuestionResponse = vi.fn();
const deactivateEncounterComplaint = vi.fn();

vi.mock("@/lib/api/clinical-encounters", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/clinical-encounters")>();
  return {
    ...actual,
    addEncounterComplaint: (...args: unknown[]) => addEncounterComplaint(...args),
    addEncounterFinding: (...args: unknown[]) => addEncounterFinding(...args),
    upsertEncounterQuestionResponse: (...args: unknown[]) => upsertEncounterQuestionResponse(...args),
    deactivateEncounterComplaint: (...args: unknown[]) => deactivateEncounterComplaint(...args),
  };
});

const baseDetail = {
  encounter: {
    id: "e1",
    patient_id: "p1",
    organization_id: "o1",
    clinician_user_id: "d1",
    specialty_key: "cardiology",
    status: "active" as const,
    locale: "en",
    started_at: "2026-01-01T10:00:00Z",
    ended_at: null,
    appointment_id: null,
    version: 1,
  },
  complaints: [],
  findings: [],
  question_responses: [],
  final_summary: null,
};

describe("EncounterDetailWriteWorkspace", () => {
  beforeEach(() => {
    addEncounterComplaint.mockReset();
    addEncounterFinding.mockReset();
    upsertEncounterQuestionResponse.mockReset();
    deactivateEncounterComplaint.mockReset();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows write forms for active encounter", () => {
    render(
      <EncounterDetailWriteWorkspace
        encounterId="e1"
        accessToken="token"
        detail={baseDetail}
        labels={makeEncounterWorkspaceTestLabels()}
        formatDateTime={(v) => v}
        onRefresh={async () => {}}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Add complaint" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add finding" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save response" })).toBeInTheDocument();
    expect(screen.queryByText(/Copilot|differential|diagnosis/i)).not.toBeInTheDocument();
  });

  it("hides write forms for finalized encounter", () => {
    render(
      <EncounterDetailWriteWorkspace
        encounterId="e1"
        accessToken="token"
        detail={{
          ...baseDetail,
          encounter: { ...baseDetail.encounter, status: "finalized" },
        }}
        labels={makeEncounterWorkspaceTestLabels()}
        formatDateTime={(v) => v}
        onRefresh={async () => {}}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Add complaint" })).not.toBeInTheDocument();
    expect(screen.getByText("Read-only finalized")).toBeInTheDocument();
  });

  it("submits complaint and refreshes detail", async () => {
    addEncounterComplaint.mockResolvedValue({ id: "c1" });
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    const onStatusMessage = vi.fn();

    render(
      <EncounterDetailWriteWorkspace
        encounterId="e1"
        accessToken="token"
        detail={baseDetail}
        labels={makeEncounterWorkspaceTestLabels()}
        formatDateTime={(v) => v}
        onRefresh={onRefresh}
        onUnauthorized={vi.fn()}
        onStatusMessage={onStatusMessage}
      />,
    );

    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Chest pain" } });
    fireEvent.click(screen.getByRole("button", { name: "Add complaint" }));

    await waitFor(() => {
      expect(addEncounterComplaint).toHaveBeenCalledWith("token", "e1", {
        is_primary: false,
        negated: false,
        clinician_display_text: "Chest pain",
      });
    });
    expect(onRefresh).toHaveBeenCalled();
    expect(onStatusMessage).toHaveBeenCalledWith("Saved complaint");
  });

  it("shows localized finding type label instead of raw enum", () => {
    render(
      <EncounterDetailWriteWorkspace
        encounterId="e1"
        accessToken="token"
        detail={{
          ...baseDetail,
          findings: [
            {
              id: "f1",
              encounter_id: "e1",
              finding_type: "physical_exam",
              finding_key: "murmur",
              value_code: null,
              value_numeric: null,
              unit: null,
              negated: false,
              onset_code: null,
              source: "clinician_observed",
              sequence_no: 1,
              recorded_at: "2026-01-01T10:00:00Z",
              recorded_by: null,
            },
          ],
        }}
        labels={makeEncounterWorkspaceTestLabels()}
        formatDateTime={(v) => v}
        onRefresh={async () => {}}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    expect(screen.getByText(/Physical exam: murmur/)).toBeInTheDocument();
    expect(screen.queryByText("physical_exam")).not.toBeInTheDocument();
  });

  it("handles 409 by refreshing and showing conflict message", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    addEncounterComplaint.mockRejectedValue(new ApiClientError("stale", 409, { detail: "secret" }));
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    const onStatusMessage = vi.fn();

    render(
      <EncounterDetailWriteWorkspace
        encounterId="e1"
        accessToken="token"
        detail={baseDetail}
        labels={makeEncounterWorkspaceTestLabels()}
        formatDateTime={(v) => v}
        onRefresh={onRefresh}
        onUnauthorized={vi.fn()}
        onStatusMessage={onStatusMessage}
      />,
    );

    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Pain" } });
    fireEvent.click(screen.getByRole("button", { name: "Add complaint" }));

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
      expect(onStatusMessage).toHaveBeenCalledWith("Conflict stale");
    });
    expect(onStatusMessage).not.toHaveBeenCalledWith(expect.stringContaining("secret"));
  });
});
