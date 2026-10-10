import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EncounterTerminalActions } from "@/components/patients/EncounterTerminalActions";
import { makeEncounterTerminalTestLabels } from "@/components/patients/encounter-test-labels";

const finalizeClinicalEncounter = vi.fn();
const cancelClinicalEncounter = vi.fn();

vi.mock("@/lib/api/clinical-encounters", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/clinical-encounters")>();
  return {
    ...actual,
    finalizeClinicalEncounter: (...args: unknown[]) => finalizeClinicalEncounter(...args),
    cancelClinicalEncounter: (...args: unknown[]) => cancelClinicalEncounter(...args),
  };
});

const activeDetail = {
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
    version: 4,
  },
  complaints: [],
  findings: [],
  question_responses: [],
  final_summary: null,
};

describe("EncounterTerminalActions", () => {
  beforeEach(() => {
    finalizeClinicalEncounter.mockReset();
    cancelClinicalEncounter.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows terminal actions only for active encounter", () => {
    const { rerender } = render(
      <EncounterTerminalActions
        encounterId="e1"
        accessToken="token"
        detail={activeDetail}
        labels={makeEncounterTerminalTestLabels()}
        onRefresh={async () => {}}
        onDetailUpdated={vi.fn()}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Complete encounter" })).toBeInTheDocument();

    rerender(
      <EncounterTerminalActions
        encounterId="e1"
        accessToken="token"
        detail={{
          ...activeDetail,
          encounter: { ...activeDetail.encounter, status: "finalized" },
        }}
        labels={makeEncounterTerminalTestLabels()}
        onRefresh={async () => {}}
        onDetailUpdated={vi.fn()}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "Complete encounter" })).not.toBeInTheDocument();
  });

  it("requires confirmation before finalize and sends expected_version", async () => {
    finalizeClinicalEncounter.mockResolvedValue({
      ...activeDetail,
      encounter: { ...activeDetail.encounter, status: "finalized", version: 5 },
      final_summary: {
        id: "fs1",
        encounter_id: "e1",
        summary_version: 1,
        summary_sections: [{ section_key: "assessment", content_key: null, clinician_text: "Stable" }],
        clinician_note: null,
        finalized_by: "d1",
        finalized_at: "2026-01-01T11:00:00Z",
        created_at: "2026-01-01T11:00:00Z",
      },
    });
    const onDetailUpdated = vi.fn();
    const onStatusMessage = vi.fn();

    render(
      <EncounterTerminalActions
        encounterId="e1"
        accessToken="token"
        detail={activeDetail}
        labels={makeEncounterTerminalTestLabels()}
        onRefresh={async () => {}}
        onDetailUpdated={onDetailUpdated}
        onUnauthorized={vi.fn()}
        onStatusMessage={onStatusMessage}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Complete encounter" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Encounter summary"), { target: { value: "Stable summary" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm completion" }));

    await waitFor(() => {
      expect(finalizeClinicalEncounter).toHaveBeenCalledWith("token", "e1", {
        expected_version: 4,
        summary_sections: [{ section_key: "assessment", clinician_text: "Stable summary" }],
      });
    });
    expect(onDetailUpdated).toHaveBeenCalled();
    expect(onStatusMessage).toHaveBeenCalledWith("Encounter completed.");
  });

  it("cancel sends only expected_version after confirmation", async () => {
    cancelClinicalEncounter.mockResolvedValue({ ...activeDetail.encounter, status: "cancelled" });
    const onRefresh = vi.fn().mockResolvedValue(undefined);

    render(
      <EncounterTerminalActions
        encounterId="e1"
        accessToken="token"
        detail={activeDetail}
        labels={makeEncounterTerminalTestLabels()}
        onRefresh={onRefresh}
        onDetailUpdated={vi.fn()}
        onUnauthorized={vi.fn()}
        onStatusMessage={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancel encounter" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm cancellation" }));

    await waitFor(() => {
      expect(cancelClinicalEncounter).toHaveBeenCalledWith("token", "e1", { expected_version: 4 });
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it("409 on finalize refreshes and shows conflict message", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    finalizeClinicalEncounter.mockRejectedValue(new ApiClientError("stale", 409, { detail: "secret" }));
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    const onStatusMessage = vi.fn();

    render(
      <EncounterTerminalActions
        encounterId="e1"
        accessToken="token"
        detail={activeDetail}
        labels={makeEncounterTerminalTestLabels()}
        onRefresh={onRefresh}
        onDetailUpdated={vi.fn()}
        onUnauthorized={vi.fn()}
        onStatusMessage={onStatusMessage}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Complete encounter" }));
    fireEvent.change(screen.getByLabelText("Encounter summary"), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm completion" }));

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
      expect(onStatusMessage).toHaveBeenCalledWith("Conflict stale");
    });
    expect(onStatusMessage).not.toHaveBeenCalledWith(expect.stringContaining("secret"));
  });
});
