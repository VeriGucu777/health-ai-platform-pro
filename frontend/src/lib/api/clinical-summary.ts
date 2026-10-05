import { apiClient } from "@/lib/api/index";

export type ClinicalSummaryOverviewItem = {
  key: string;
  severity: string;
  label: string;
  message: string;
  trend_status: string | null;
  source_count: number;
  data_window_start: string | null;
  data_window_end: string | null;
};

export type PatientClinicalSummary = {
  patient_id: string;
  generated_at: string;
  summary_version: string;
  overview_items: ClinicalSummaryOverviewItem[];
  disclaimer: string;
  data_quality: {
    no_data: boolean;
  };
};

export async function fetchPatientClinicalSummary(
  authToken: string,
  patientId: string,
): Promise<PatientClinicalSummary> {
  return apiClient.get<PatientClinicalSummary>(`/patients/${patientId}/clinical-summary`, {
    authToken,
  });
}
