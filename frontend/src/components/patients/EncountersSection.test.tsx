import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EncountersSection, type EncountersSectionLabels } from "@/components/patients/EncountersSection";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const labels: EncountersSectionLabels = {
  sectionTitle: "Encounters",
  startNew: "Start new encounter",
  startPending: "Starting…",
  viewDetail: "View details",
  listEmpty: "No encounters yet.",
  listLoadError: "List failed",
  createConflict: "Active encounter exists",
  createError: "Create failed",
  openActiveEncounter: "Open active",
  statusLabels: { active: "Active", finalized: "Finalized", draft: "Draft", cancelled: "Cancelled" },
  specialtyLabel: "Specialty",
  startedAt: "Started",
  endedAt: "Ended",
  notFoundOrDenied: "Not found",
  genericError: "Generic error",
  accessDenied: "Denied",
  loadingLabel: "Loading…",
  retryLabel: "Retry",
};

const fetchPatientEncounters = vi.fn();
const createClinicalEncounter = vi.fn();

vi.mock("@/lib/api/clinical-encounters", () => ({
  fetchPatientEncounters: (...args: unknown[]) => fetchPatientEncounters(...args),
  createClinicalEncounter: (...args: unknown[]) => createClinicalEncounter(...args),
}));

describe("EncountersSection", () => {
  beforeEach(() => {
    fetchPatientEncounters.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    createClinicalEncounter.mockReset();
    push.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows empty list state", async () => {
    render(
      <EncountersSection
        patientId="p1"
        accessToken="token"
        locale="en"
        labels={labels}
        onUnauthorized={vi.fn()}
        formatDateTime={(v) => v}
      />,
    );
    expect(await screen.findByText("No encounters yet.")).toBeInTheDocument();
  });

  it("lists encounters with translated status", async () => {
    fetchPatientEncounters.mockResolvedValue({
      items: [
        {
          id: "e1",
          patient_id: "p1",
          organization_id: "o1",
          clinician_user_id: "d1",
          specialty_key: "cardiology",
          status: "finalized",
          locale: "en",
          started_at: "2026-01-01T10:00:00Z",
          ended_at: null,
          appointment_id: null,
          version: 2,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    render(
      <EncountersSection
        patientId="p1"
        accessToken="token"
        locale="en"
        labels={labels}
        onUnauthorized={vi.fn()}
        formatDateTime={(v) => v}
      />,
    );
    expect(await screen.findByText("Finalized")).toBeInTheDocument();
    expect(screen.queryByText("finalized")).not.toBeInTheDocument();
  });

  it("navigates on create success", async () => {
    createClinicalEncounter.mockResolvedValue({
      encounter: { id: "new-enc" },
      complaints: [],
      findings: [],
      question_responses: [],
    });
    render(
      <EncountersSection
        patientId="p1"
        accessToken="token"
        locale="tr"
        labels={labels}
        onUnauthorized={vi.fn()}
        formatDateTime={(v) => v}
      />,
    );
    await screen.findByText("No encounters yet.");
    fireEvent.click(screen.getByRole("button", { name: "Start new encounter" }));
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/patients/p1/encounters/new-enc");
    });
    expect(createClinicalEncounter).toHaveBeenCalledWith("token", "p1", {
      specialty_key: "cardiology",
      locale: "tr",
    });
  });

  it("shows safe 409 conflict message", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    createClinicalEncounter.mockRejectedValue(new ApiClientError("conflict", 409, null));
    fetchPatientEncounters
      .mockResolvedValueOnce({ items: [], total: 0, limit: 50, offset: 0 })
      .mockResolvedValueOnce({
        items: [
          {
            id: "active-1",
            patient_id: "p1",
            organization_id: "o1",
            clinician_user_id: "d1",
            specialty_key: "cardiology",
            status: "active",
            locale: "en",
            started_at: null,
            ended_at: null,
            appointment_id: null,
            version: 1,
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      });
    render(
      <EncountersSection
        patientId="p1"
        accessToken="token"
        locale="en"
        labels={labels}
        onUnauthorized={vi.fn()}
        formatDateTime={(v) => v}
      />,
    );
    await screen.findByText("No encounters yet.");
    fireEvent.click(screen.getByRole("button", { name: "Start new encounter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Active encounter exists");
    expect(screen.queryByText("conflict")).not.toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Open active" })).toHaveAttribute(
      "href",
      "/patients/p1/encounters/active-1",
    );
  });

  it("prevents double submit while create pending", async () => {
    let resolveCreate: (value: unknown) => void = () => undefined;
    createClinicalEncounter.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        }),
    );
    render(
      <EncountersSection
        patientId="p1"
        accessToken="token"
        locale="en"
        labels={labels}
        onUnauthorized={vi.fn()}
        formatDateTime={(v) => v}
      />,
    );
    await screen.findByText("No encounters yet.");
    const button = screen.getByRole("button", { name: "Start new encounter" });
    fireEvent.click(button);
    expect(await screen.findByRole("button", { name: "Starting…" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Starting…" }));
    expect(createClinicalEncounter).toHaveBeenCalledTimes(1);
    resolveCreate({
      encounter: { id: "enc-x" },
      complaints: [],
      findings: [],
      question_responses: [],
    });
  });
});
