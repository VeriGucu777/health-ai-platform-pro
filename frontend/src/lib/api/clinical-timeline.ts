import { apiClient } from "@/lib/api/index";

export type TimelineSource = {
  kind: string;
  id: string;
};

export type TimelineEvent = {
  occurred_at: string;
  event_type: string;
  headline: string;
  detail: string;
  severity: string | null;
  source: TimelineSource;
};

export type ClinicalTimelineResponse = {
  patient_id: string;
  date_from: string | null;
  date_to: string;
  generated_at: string;
  events: TimelineEvent[];
  truncated: boolean;
  disclaimer: string;
};

export type ClinicalTimelineQuery = {
  date_from?: string;
  date_to?: string;
  max_events?: number;
  include_risk_snapshot?: boolean;
};

export async function fetchClinicalTimeline(
  authToken: string,
  patientId: string,
  query: ClinicalTimelineQuery = {},
): Promise<ClinicalTimelineResponse> {
  const search = new URLSearchParams();

  if (query.date_from) {
    search.set("date_from", query.date_from);
  }
  if (query.date_to) {
    search.set("date_to", query.date_to);
  }
  if (query.max_events !== undefined) {
    search.set("max_events", String(query.max_events));
  }
  if (query.include_risk_snapshot !== undefined) {
    search.set("include_risk_snapshot", String(query.include_risk_snapshot));
  }

  const qs = search.toString();
  const path = qs
    ? `/patients/${patientId}/clinical-timeline?${qs}`
    : `/patients/${patientId}/clinical-timeline`;

  return apiClient.get<ClinicalTimelineResponse>(path, { authToken });
}
