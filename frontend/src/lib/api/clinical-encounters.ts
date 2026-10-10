import { apiClient } from "@/lib/api/index";

export type EncounterStatus = "draft" | "active" | "finalized" | "cancelled";

export type ClinicalEncounterListItem = {
  id: string;
  patient_id: string;
  organization_id: string;
  clinician_user_id: string;
  specialty_key: string;
  status: EncounterStatus;
  locale: string;
  started_at: string | null;
  ended_at: string | null;
  appointment_id: string | null;
  version: number;
};

export type ClinicalEncounterListResponse = {
  items: ClinicalEncounterListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type EncounterComplaint = {
  id: string;
  encounter_id: string;
  complaint_key: string | null;
  clinician_display_text: string | null;
  is_primary: boolean;
  negated: boolean;
  sequence_no: number;
  recorded_at: string;
  recorded_by: string | null;
};

export type EncounterFinding = {
  id: string;
  encounter_id: string;
  finding_type: string;
  finding_key: string;
  value_code: string | null;
  value_numeric: string | number | null;
  unit: string | null;
  negated: boolean;
  onset_code: string | null;
  source: string;
  sequence_no: number;
  recorded_at: string;
  recorded_by: string | null;
};

export type EncounterQuestionResponse = {
  id: string;
  encounter_id: string;
  question_key: string;
  answer_type: string;
  answer_code: string | null;
  answer_numeric: string | number | null;
  clinician_note: string | null;
  sequence_no: number;
  answered_at: string;
  answered_by: string | null;
};

export type EncounterSummarySection = {
  section_key: string;
  content_key: string | null;
  clinician_text: string | null;
};

export type EncounterFinalSummary = {
  id: string;
  encounter_id: string;
  summary_version: number;
  summary_sections: EncounterSummarySection[];
  clinician_note: string | null;
  finalized_by: string;
  finalized_at: string;
  created_at: string;
};

export type ClinicalEncounterDetail = {
  encounter: ClinicalEncounterListItem;
  complaints: EncounterComplaint[];
  findings: EncounterFinding[];
  question_responses: EncounterQuestionResponse[];
  final_summary: EncounterFinalSummary | null;
};

export type CreateClinicalEncounterBody = {
  specialty_key: string;
  locale: string;
};

export type FindingType =
  | "symptom"
  | "physical_exam"
  | "history_item"
  | "risk_factor"
  | "negative_finding"
  | "other";

export type ClinicalInputSource =
  | "patient_reported"
  | "clinician_observed"
  | "historical_record"
  | "device"
  | "other";

export type QuestionAnswerType = "boolean" | "single_choice" | "number" | "text";

export type EncounterComplaintCreateBody = {
  complaint_key?: string | null;
  clinician_display_text?: string | null;
  is_primary?: boolean;
  negated?: boolean;
};

export type EncounterFindingCreateBody = {
  finding_type: FindingType;
  finding_key: string;
  value_code?: string | null;
  value_numeric?: number | string | null;
  unit?: string | null;
  negated?: boolean;
  onset_code?: string | null;
  source?: ClinicalInputSource;
};

export type EncounterQuestionResponseUpsertBody = {
  answer_type: QuestionAnswerType;
  answer_code?: string | null;
  answer_numeric?: number | string | null;
  clinician_note?: string | null;
};

export type EncounterSummarySectionInput = {
  section_key: string;
  content_key?: string | null;
  clinician_text?: string | null;
};

export type FinalizeClinicalEncounterBody = {
  expected_version: number;
  summary_sections: EncounterSummarySectionInput[];
  clinician_note?: string | null;
};

export type CancelClinicalEncounterBody = {
  expected_version: number;
};

export type EncounterComplaintRecord = EncounterComplaint;
export type EncounterFindingRecord = EncounterFinding;
export type EncounterQuestionResponseRecord = EncounterQuestionResponse;

export async function fetchPatientEncounters(
  authToken: string,
  patientId: string,
  params?: { limit?: number; offset?: number; status?: string },
): Promise<ClinicalEncounterListResponse> {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    search.set("offset", String(params.offset));
  }
  if (params?.status) {
    search.set("status", params.status);
  }
  const query = search.toString();
  const path = `/patients/${patientId}/encounters${query ? `?${query}` : ""}`;
  return apiClient.get<ClinicalEncounterListResponse>(path, { authToken });
}

export async function createClinicalEncounter(
  authToken: string,
  patientId: string,
  body: CreateClinicalEncounterBody,
): Promise<ClinicalEncounterDetail> {
  return apiClient.post<ClinicalEncounterDetail>(`/patients/${patientId}/encounters`, {
    authToken,
    body,
  });
}

export async function fetchClinicalEncounterDetail(
  authToken: string,
  encounterId: string,
): Promise<ClinicalEncounterDetail> {
  return apiClient.get<ClinicalEncounterDetail>(`/encounters/${encounterId}`, {
    authToken,
  });
}

export async function addEncounterComplaint(
  authToken: string,
  encounterId: string,
  body: EncounterComplaintCreateBody,
): Promise<EncounterComplaint> {
  return apiClient.post<EncounterComplaint>(`/encounters/${encounterId}/complaints`, {
    authToken,
    body,
  });
}

export async function addEncounterFinding(
  authToken: string,
  encounterId: string,
  body: EncounterFindingCreateBody,
): Promise<EncounterFinding> {
  return apiClient.post<EncounterFinding>(`/encounters/${encounterId}/findings`, {
    authToken,
    body,
  });
}

export async function upsertEncounterQuestionResponse(
  authToken: string,
  encounterId: string,
  questionKey: string,
  body: EncounterQuestionResponseUpsertBody,
): Promise<EncounterQuestionResponse> {
  const encodedKey = encodeURIComponent(questionKey);
  return apiClient.put<EncounterQuestionResponse>(
    `/encounters/${encounterId}/question-responses/${encodedKey}`,
    { authToken, body },
  );
}

export async function deactivateEncounterComplaint(
  authToken: string,
  encounterId: string,
  complaintId: string,
): Promise<void> {
  await apiClient.delete<void>(`/encounters/${encounterId}/complaints/${complaintId}`, {
    authToken,
  });
}

export async function finalizeClinicalEncounter(
  authToken: string,
  encounterId: string,
  body: FinalizeClinicalEncounterBody,
): Promise<ClinicalEncounterDetail> {
  return apiClient.post<ClinicalEncounterDetail>(`/encounters/${encounterId}/finalize`, {
    authToken,
    body,
  });
}

export async function cancelClinicalEncounter(
  authToken: string,
  encounterId: string,
  body: CancelClinicalEncounterBody,
): Promise<ClinicalEncounterListItem> {
  return apiClient.post<ClinicalEncounterListItem>(`/encounters/${encounterId}/cancel`, {
    authToken,
    body,
  });
}
