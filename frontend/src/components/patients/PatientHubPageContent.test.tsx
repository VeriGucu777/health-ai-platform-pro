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
  clinicalSummaryTitle: "Clinical summary",
  clinicalSummarySubtitle: "Recent clinical picture",
  clinicalSummaryDescription: "Brief summary from records.",
  clinicalSummaryEmpty: "Not enough data for summary.",
  clinicalSummaryLoadError: "Summary load failed",
  clinicalSummaryDisclaimer: "Decision support only.",
  clinicalSummaryItemLabels: { laboratory_summary: "Laboratory" },
  clinicalSummaryTrendMessages: {},
  clinicalSummaryItemMessages: {},
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
  assessmentTypes: { diabetes: "Diabetes", heart_disease: "Kalp hastalığı" },
  riskLevels: { low: "Low", moderate: "Orta", high: "Yüksek" },
  missingInputLabels: {
    systolic_blood_pressure: "Sistolik tansiyon",
  },
  missingInputReasons: {
    systolic_blood_pressure:
      "Seçilen tarih aralığında sistolik tansiyon ölçümü bulunmuyor.",
  },
};

const localeFixture = {
  locale: "en" as "en" | "tr",
  effectiveLocale: "en" as "en" | "tr",
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
const fetchPatientClinicalSummary = vi.fn();
const fetchRiskAssessmentHistory = vi.fn();
const fetchHealthSummaryPdf = vi.fn();
const triggerBlobDownload = vi.fn();

vi.mock("@/lib/api/patients", () => ({
  fetchPatient: (...args: unknown[]) => fetchPatient(...args),
}));

vi.mock("@/lib/api/clinical-summary", () => ({
  fetchPatientClinicalSummary: (...args: unknown[]) => fetchPatientClinicalSummary(...args),
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
    fetchPatientClinicalSummary.mockReset();
    fetchPatientClinicalSummary.mockResolvedValue({ overview_items: [] });
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

  it("shows clinical summary card with overview items", async () => {
    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchPatientClinicalSummary.mockResolvedValue({
      overview_items: [
        {
          key: "laboratory_summary",
          severity: "info",
          label: "Laboratory",
          message: "HbA1c 7.2%",
          trend_status: null,
          source_count: 1,
          data_window_start: null,
          data_window_end: null,
        },
      ],
    });
    fetchRiskAssessmentHistory.mockResolvedValue({ items: [] });

    render(<PatientHubPageContent patientId="p1" />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Clinical summary" })).toBeInTheDocument();
      expect(screen.getByText(/HbA1c 7.2%/)).toBeInTheDocument();
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

  it("localizes missing inputs in risk history when locale is Turkish", async () => {
    localeFixture.effectiveLocale = "tr";
    localeFixture.locale = "tr";

    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchRiskAssessmentHistory.mockResolvedValue({
      items: [
        {
          id: "risk-1",
          patient_id: "p1",
          organization_id: null,
          assessment_type: "diabetes",
          assessment_status: "insufficient_data",
          risk_level: null,
          score: null,
          probability: null,
          model_kind: "rule_based",
          model_version: "rule_based_v1",
          evaluated_by_user_id: "u1",
          evaluated_at: "2026-09-29T11:24:32Z",
          created_at: "2026-09-29T11:24:32Z",
          result_snapshot: {
            missing_inputs: [
              {
                input: "systolic_blood_pressure",
                reason:
                  "No systolic blood pressure measurements are available in the selected date range.",
                impact: "",
              },
            ],
          },
        },
      ],
    });

    render(<PatientHubPageContent patientId="p1" />);

    await waitFor(() => {
      expect(screen.getByText(/Sistolik tansiyon:/)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/No systolic blood pressure measurements/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/systolic_blood_pressure/)).not.toBeInTheDocument();

    localeFixture.effectiveLocale = "en";
    localeFixture.locale = "en";
  });

  it("shows score and localized risk level on risk history card", async () => {
    localeFixture.effectiveLocale = "tr";
    localeFixture.locale = "tr";
    hubFixture.score = "Skor";
    hubFixture.riskLevel = "Düzey";

    fetchPatient.mockResolvedValue({
      id: "p1",
      first_name: "Demo",
      last_name: "Patient",
      date_of_birth: "1990-06-12",
      gender: "female",
      is_active: true,
    });
    fetchRiskAssessmentHistory.mockResolvedValue({
      items: [
        {
          id: "risk-cardiac",
          patient_id: "p1",
          organization_id: null,
          assessment_type: "heart_disease",
          assessment_status: "completed",
          risk_level: "moderate",
          score: 58,
          probability: null,
          model_kind: "rule_based",
          model_version: "heart_rule_based_v1",
          evaluated_by_user_id: "u1",
          evaluated_at: "2026-09-29T11:24:32Z",
          created_at: "2026-09-29T11:24:32Z",
          result_snapshot: { contributing_factors: [{ factor: "bp", message: "TR", message_tr: "TR" }] },
        },
      ],
    });

    render(<PatientHubPageContent patientId="p1" />);

    await waitFor(() => {
      expect(screen.getByText(/Skor: 58/)).toBeInTheDocument();
      expect(screen.getByText(/Düzey: Orta/)).toBeInTheDocument();
    });

    localeFixture.effectiveLocale = "en";
    localeFixture.locale = "en";
    hubFixture.score = "Score";
    hubFixture.riskLevel = "Level";
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
