import { apiClient } from "@/lib/api/index";

export type RiskContributingFactor = {
  factor: string;
  status: string;
  severity: string;
  weight: number;
  message: string;
  source: string;
};

export type RiskMissingInput = {
  input: string;
  reason: string;
  impact: string;
};

export type RiskResultSnapshot = {
  date_from?: string | null;
  date_to?: string | null;
  contributing_factors?: RiskContributingFactor[];
  missing_inputs?: RiskMissingInput[];
  recommendations?: unknown[];
};

export type RiskAssessmentHistoryItem = {
  id: string;
  patient_id: string;
  organization_id: string | null;
  assessment_type: string;
  assessment_status: string;
  risk_level: string | null;
  score: number | null;
  probability: number | null;
  model_kind: string;
  model_version: string;
  evaluated_by_user_id: string;
  evaluated_at: string;
  result_snapshot: RiskResultSnapshot | null;
  created_at: string;
};

export type RiskAssessmentHistoryListResponse = {
  items: RiskAssessmentHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type RiskHistoryQuery = {
  page?: number;
  page_size?: number;
  assessment_type?: string;
  date_from?: string;
  date_to?: string;
};

export async function fetchRiskAssessmentHistory(
  authToken: string,
  patientId: string,
  query: RiskHistoryQuery = {},
): Promise<RiskAssessmentHistoryListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(query.page ?? 1));
  search.set("page_size", String(query.page_size ?? 20));

  if (query.assessment_type) {
    search.set("assessment_type", query.assessment_type);
  }
  if (query.date_from) {
    search.set("date_from", query.date_from);
  }
  if (query.date_to) {
    search.set("date_to", query.date_to);
  }

  const qs = search.toString();
  const path = `/patients/${patientId}/risk-assessments/history?${qs}`;

  return apiClient.get<RiskAssessmentHistoryListResponse>(path, { authToken });
}
