import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EncounterDetailPageContent } from "@/components/patients/EncounterDetailPageContent";
import { makeEncounterDetailTestLabels } from "@/components/patients/encounter-test-labels";

const labels = makeEncounterDetailTestLabels();

const fetchClinicalEncounterDetail = vi.fn();

vi.mock("@/lib/api/clinical-encounters", () => ({
  fetchClinicalEncounterDetail: (...args: unknown[]) => fetchClinicalEncounterDetail(...args),
}));

describe("EncounterDetailPageContent", () => {
  beforeEach(() => {
    fetchClinicalEncounterDetail.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders finalized summary as plain text", async () => {
    fetchClinicalEncounterDetail.mockResolvedValue({
      encounter: {
        id: "e1",
        patient_id: "p1",
        organization_id: "o1",
        clinician_user_id: "d1",
        specialty_key: "cardiology",
        status: "finalized",
        locale: "en",
        started_at: "2026-01-01T10:00:00Z",
        ended_at: "2026-01-01T11:00:00Z",
        appointment_id: null,
        version: 3,
      },
      complaints: [],
      findings: [],
      question_responses: [],
      final_summary: {
        id: "fs1",
        encounter_id: "e1",
        summary_version: 1,
        summary_sections: [
          { section_key: "Assessment", content_key: "stable", clinician_text: "Stable summary text" },
        ],
        clinician_note: "Follow up",
        finalized_by: "d1",
        finalized_at: "2026-01-01T11:00:00Z",
        created_at: "2026-01-01T11:00:00Z",
      },
    });

    const { container } = render(
      <EncounterDetailPageContent
        patientId="p1"
        encounterId="e1"
        accessToken="token"
        labels={labels}
        formatDateTime={(v) => v}
        onUnauthorized={vi.fn()}
      />,
    );

    expect(await screen.findByText("Stable summary text")).toBeInTheDocument();
    expect(screen.getByText("Finalized")).toBeInTheDocument();
    expect(container.innerHTML).not.toContain("dangerouslySetInnerHTML");
    expect(screen.queryByRole("button", { name: "Add complaint" })).not.toBeInTheDocument();
  });

  it("shows safe 404 masking message", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    fetchClinicalEncounterDetail.mockRejectedValue(new ApiClientError("missing", 404, { message: "secret" }));

    render(
      <EncounterDetailPageContent
        patientId="p1"
        encounterId="missing"
        accessToken="token"
        labels={labels}
        formatDateTime={(v) => v}
        onUnauthorized={vi.fn()}
      />,
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Not found or denied");
    expect(alert.textContent).not.toContain("secret");
  });
});
