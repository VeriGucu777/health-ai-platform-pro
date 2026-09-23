import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PatientHubPageContent } from "@/components/patients/PatientHubPageContent";

const handleUnauthorized = vi.fn();

vi.mock("@/lib/auth/AuthProvider", () => ({
  useAuth: () => ({
    accessToken: "token",
    handleUnauthorized,
  }),
}));

const hubFixture = {
  title: "Patient overview",
  description: "Review patient",
  decisionSupportTitle: "Decision support",
  decisionSupportBody: "Not a diagnosis.",
  clinicalTimeline: "Clinical timeline",
  downloadPdf: "Download PDF report",
  downloadingPdf: "Preparing PDF…",
  pdfError: "PDF failed",
  pdfSuccess: "PDF started",
  riskHistoryTitle: "Risk history",
  riskHistoryEmpty: "No risk history",
  riskHistoryLoadError: "Risk load failed",
  riskType: "Type",
  riskLevel: "Level",
  assessedAt: "Assessed at",
  score: "Score",
  factors: "Factors",
  missingInputs: "Missing",
  riskDisclaimer: "Disclaimer",
  active: "Active",
  inactive: "Inactive",
  notFoundOrDenied: "Patient not found or you do not have access to this patient.",
  loadError: "Could not load patient",
  assessmentTypes: { diabetes: "Diabetes" },
  riskLevels: { low: "Low" },
};

const localeFixture = {
  locale: "en" as const,
  effectiveLocale: "en" as const,
  content: {
    common: { loading: "Loading…", error: "Error", retry: "Retry", back: "Back" },
    patients: { genders: { female: "Female", male: "Male", other: "Other" } },
    timeline: { patientSummary: { ageSuffix: "years" } },
    patientHub: hubFixture,
  },
  formatDate: (value: string) => value,
  formatDateTime: (value: string) => value,
};

vi.mock("@/lib/i18n/use-locale", () => ({
  useLocale: () => localeFixture,
}));

const fetchPatient = vi.fn();
const fetchRiskAssessmentHistory = vi.fn();
const fetchHealthSummaryPdf = vi.fn();
const triggerBlobDownload = vi.fn();

vi.mock("@/lib/api/patients", () => ({
  fetchPatient: (...args: unknown[]) => fetchPatient(...args),
}));

vi.mock("@/lib/api/risk-history", () => ({
  fetchRiskAssessmentHistory: (...args: unknown[]) => fetchRiskAssessmentHistory(...args),
}));

vi.mock("@/lib/api/health-report", () => ({
  fetchHealthSummaryPdf: (...args: unknown[]) => fetchHealthSummaryPdf(...args),
  triggerBlobDownload: (...args: unknown[]) => triggerBlobDownload(...args),
}));

describe("PatientHubPageContent", () => {
  beforeEach(() => {
    fetchPatient.mockReset();
    fetchRiskAssessmentHistory.mockReset();
    fetchHealthSummaryPdf.mockReset();
    triggerBlobDownload.mockReset();
    handleUnauthorized.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows loading then patient header", async () => {
    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchRiskAssessmentHistory.mockResolvedValue({ items: [] });

    render(<PatientHubPageContent patientId="p1" />);

    expect(screen.getByText("Loading…")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Demo Patient" })).toBeInTheDocument();
    });
  });

  it("shows empty risk history state", async () => {
    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchRiskAssessmentHistory.mockResolvedValue({ items: [] });

    render(<PatientHubPageContent patientId="p1" />);

    await waitFor(() => {
      expect(screen.getByText("No risk history")).toBeInTheDocument();
    });
  });

  it("shows not found message on 404", async () => {
    const { ApiClientError } = await import("@/lib/api/client");
    fetchPatient.mockRejectedValue(new ApiClientError("Not found", 404));

    render(<PatientHubPageContent patientId="missing" />);

    await waitFor(() => {
      expect(
        screen.getByText("Patient not found or you do not have access to this patient."),
      ).toBeInTheDocument();
    });
  });

  it("downloads pdf on button click", async () => {
    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchRiskAssessmentHistory.mockResolvedValue({ items: [] });
    fetchHealthSummaryPdf.mockResolvedValue({
      blob: new Blob(["pdf"]),
      filename: "report.pdf",
    });

    render(<PatientHubPageContent patientId="p1" />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Download PDF report" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Download PDF report" }));

    await waitFor(() => {
      expect(fetchHealthSummaryPdf).toHaveBeenCalledWith("token", "p1", {
        locale: "en",
      });
      expect(triggerBlobDownload).toHaveBeenCalled();
    });
  });
});
