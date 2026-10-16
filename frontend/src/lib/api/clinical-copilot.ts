import { apiClient } from "@/lib/api/index";

export type ClinicalCopilotEvaluationStatus = "success" | "no_applicable_rules" | "failed";

export type ClinicalCopilotProvenance = {
  input_snapshot_id: string;
  context_schema_version: string;
  vocabulary_id: string | null;
  vocabulary_version: string | null;
  vocabulary_manifest_hash: string | null;
  rule_manifest_hash: string;
  engine_version: string;
  specialty_module_version: string;
  policy_profile_id: string;
  policy_profile_version: string;
  context_profile: string;
  specialty_key: string;
  evaluated_at: string;
  rule_provenance: unknown[];
};

export type ClinicalCopilotEvaluationResponse = {
  evaluation_id: string;
  encounter_id: string;
  patient_id: string;
  evaluation_status: ClinicalCopilotEvaluationStatus;
  read_only: boolean;
  missing_information: unknown[];
  review_domain_status: unknown[];
  documentation_reminders: unknown[];
  provenance: ClinicalCopilotProvenance;
};

export async function evaluateClinicalCopilot(
  authToken: string,
  patientId: string,
  encounterId: string,
  body: { context_profile?: string } = {},
): Promise<ClinicalCopilotEvaluationResponse> {
  return apiClient.post<ClinicalCopilotEvaluationResponse>(
    `/patients/${patientId}/encounters/${encounterId}/evaluate`,
    { authToken, body: { context_profile: body.context_profile ?? "hypertension_v1" } },
  );
}
